#Genera el par de claves RSA con el que se protegen las cookies de los clientes
#- La clave PRIVADA se queda en el VPS (config/cookie_private.pem) y nunca sale de ahi ni va a git
#- La clave PUBLICA (base64) se pone en la web como NEXT_PUBLIC_COOKIE_PUBLIC_KEY: solo sirve para cifrar
#Uso: python generar_claves.py
import base64,os,sys
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

BASE = Path(__file__).resolve().parent
PRIVADA = BASE / 'config' / 'cookie_private.pem'
PUBLICA = BASE / 'config' / 'cookie_public.b64'

if PRIVADA.exists():
    print(f'Ya existe {PRIVADA}. No se sobrescribe (borrarla invalidaria las cookies ya guardadas).')
    sys.exit(1)
clave = rsa.generate_private_key(public_exponent=65537,key_size=3072)
PRIVADA.write_bytes(clave.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
try:
    os.chmod(PRIVADA,0o600)
except OSError:
    pass
spki = clave.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
PUBLICA.write_text(base64.b64encode(spki).decode())
print(f'Clave privada: {PRIVADA}  (guardala solo en el VPS)')
print(f'Clave publica (NEXT_PUBLIC_COOKIE_PUBLIC_KEY): {PUBLICA}')
