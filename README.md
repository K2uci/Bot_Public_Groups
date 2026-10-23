# Bot Facebook

Publica a diario un texto con imagen en los grupos de Facebook de cada cliente, con un panel web para administrarlo.

```
Navegador ──► Web (Next.js en Vercel) ──► Supabase (Postgres + Storage + Auth) ◄── Bot (Python en el VPS)
                  web/                         supabase/migrations/                 Facebook_bot.py
```

- **Web (`web/`)**: panel de administrador. Clientes y horarios, grupos, publicaciones (texto + imagen), cookies, historial y botones de acción. Solo usa la clave **pública** de Supabase; los permisos los impone RLS.
- **Supabase**: guarda la configuración y los resultados. Esquema en `supabase/migrations/`.
- **Bot (VPS)**: cada minuto baja la configuración a `clientes/<slug>/`, ejecuta las tandas con Selenium/Firefox y sube latido, estado, historial y resultado de las órdenes. Solo hace conexiones salientes (no expone puertos).
- **Telegram**: avisos de bloqueo/login y un resumen diario a las 21:00 (hora de Cuba).

## Cookies de Facebook (dato crítico)
Las cookies se **cifran en el navegador** (`web/lib/crypto.ts`, RSA-OAEP + AES-GCM) con la clave pública antes de enviarse. Solo la clave privada (`config/cookie_private.pem`, generada con `generar_claves.py` **en el VPS** y nunca versionada) puede abrirlas. Ni Vercel ni Supabase ven nunca las cookies en claro. Nunca se guardan contraseñas.

## Puesta en marcha
1. **Supabase** (plan gratis): `npx supabase projects create bot-facebook --org-id <org> --region us-east-1 --db-password <clave>`, `supabase link`, `supabase db push` y `supabase config push` (cierra el registro público; no cambies `[auth.email] enable_signup`, apaga el login). Crear tu administrador con `SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python crear_admin.py <usuario>`: el panel entra con **nombre de usuario** (internamente `usuario@usuarios.invalid`) y la contraseña aleatoria queda en `ADMIN_CREDENCIALES.txt` (cámbiala en el menú Cuenta).
2. **VPS**: `pip install cryptography selenium`, `python generar_claves.py`, y en `.env`: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (clave secreta, solo en el VPS). Luego `python migrar_a_supabase.py <slug>` para subir un cliente existente y reiniciar el servicio.
3. **Web**: variables `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` y `NEXT_PUBLIC_COOKIE_PUBLIC_KEY` (contenido de `config/cookie_public.b64`). `cd web && npm install && npm run build`; despliegue en Vercel.

## Pruebas
- `python tests/test_sync.py`: sincronización del bot contra un servidor Supabase simulado.
- `cd web && npx tsc --noEmit && npx eslint . && npx next build`.

## Comandos del bot
`python Facebook_bot.py` (servicio) · `--lista` · `--sync` · `--nuevo <slug> "<Nombre>" <min> <max>` · `--grupos <slug>` · `--ahora <slug> [N]` · `--resumen <slug>`.
`python login_manual.py <slug>`: el cliente inicia sesión en Edge y se guardan sus cookies.

Facebook prohíbe la automatización: el uso es bajo tu responsabilidad y la de cada cliente.
