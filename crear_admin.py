#Crea un usuario administrador del panel web (login por NOMBRE DE USUARIO) con una contrasena aleatoria
#Uso: SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python crear_admin.py <usuario>
#La contrasena se guarda en ADMIN_CREDENCIALES.txt (ignorado por git); cambiala despues en la web (menu Cuenta)
import json,os,re,secrets,string,sys,urllib.error,urllib.request

URL = os.environ.get('SUPABASE_URL','').rstrip('/')
KEY = os.environ.get('SUPABASE_SERVICE_KEY','')
DOMINIO = 'usuarios.invalid'   #mismo valor que web/lib/usuario.ts

def llamar(metodo,ruta,cuerpo=None):
    req = urllib.request.Request(URL + ruta,data=json.dumps(cuerpo).encode() if cuerpo is not None else None,method=metodo,
        headers={'apikey':KEY,'Authorization':f'Bearer {KEY}','Content-Type':'application/json','Prefer':'return=minimal'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        sys.exit(f'Error {e.code} en {ruta}: {e.read()[:300].decode(errors="replace")}')

if __name__ == '__main__':
    if not (URL and KEY):
        sys.exit('Faltan SUPABASE_URL y SUPABASE_SERVICE_KEY en el entorno')
    if len(sys.argv) < 2 or not re.fullmatch(r'[a-z0-9._-]{3,32}',sys.argv[1]):
        sys.exit('Uso: python crear_admin.py <usuario>   (3-32 caracteres: a-z, 0-9, punto, guion)')
    usuario = sys.argv[1]
    alfabeto = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alfabeto) for _ in range(24))
    nuevo = llamar('POST','/auth/v1/admin/users',{'email':f'{usuario}@{DOMINIO}','password':password,'email_confirm':True,'user_metadata':{'usuario':usuario}})
    llamar('POST','/rest/v1/admins',{'user_id':nuevo['id']})
    archivo = sys.argv[2] if len(sys.argv) > 2 else 'ADMIN_CREDENCIALES.txt'
    with open(archivo,'w',encoding='utf-8') as f:
        f.write(f'Usuario: {usuario}\nContrasena: {password}\n\nCambiala en la web: menu Cuenta. Borra este archivo despues.\n')
    print(f'Administrador "{usuario}" creado. Credenciales en {archivo}')
