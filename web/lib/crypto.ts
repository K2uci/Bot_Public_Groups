// Cifrado de cookies EN EL NAVEGADOR (WebCrypto) antes de enviarlas al servidor.
// Esquema hibrido: AES-256-GCM cifra las cookies y RSA-OAEP (SHA-256) cifra esa clave AES con la
// clave PUBLICA. Solo la clave privada, que vive unicamente en el VPS, puede abrir el sobre.
// Formato guardado: { v: 1, k: <clave AES cifrada>, iv: <nonce>, ct: <cookies cifradas + tag> } en base64.

export type SobreCifrado = { v: 1; k: string; iv: string; ct: string };

function aBase64(bytes: ArrayBuffer | Uint8Array): string {
  const arr = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
  let bin = "";
  for (const b of arr) bin += String.fromCharCode(b);
  return btoa(bin);
}

function deBase64(b64: string): Uint8Array<ArrayBuffer> {
  const bin = atob(b64.trim());
  const out = new Uint8Array(new ArrayBuffer(bin.length));
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

// publicKeyB64: clave publica RSA en formato SPKI/DER codificada en base64
export async function cifrarCookies(
  textoPlano: string,
  publicKeyB64: string,
): Promise<SobreCifrado> {
  const publicKey = await crypto.subtle.importKey(
    "spki",
    deBase64(publicKeyB64),
    { name: "RSA-OAEP", hash: "SHA-256" },
    false,
    ["encrypt"],
  );
  const aes = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt"]);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ct = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    aes,
    new TextEncoder().encode(textoPlano),
  );
  const aesRaw = await crypto.subtle.exportKey("raw", aes);
  const k = await crypto.subtle.encrypt({ name: "RSA-OAEP" }, publicKey, aesRaw);
  return { v: 1, k: aBase64(k), iv: aBase64(iv), ct: aBase64(ct) };
}
