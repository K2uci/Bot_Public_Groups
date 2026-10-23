#Prueba de la sincronizacion con Supabase contra un servidor simulado (no toca la nube ni la carpeta clientes/ real)
#Uso: python tests/test_sync.py
import json,os,sys,tempfile,threading,uuid
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path
from urllib.parse import parse_qs,unquote,urlparse

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))

#------------------------------------------------------------------ datos simulados
CLIENTE_ID = str(uuid.uuid4())
PUB_ID = str(uuid.uuid4())
PUB2_ID = str(uuid.uuid4())
DB = {
    'clientes':[{'id':CLIENTE_ID,'slug':'demo','nombre':'Cliente Demo','activo':True,'hora_inicio':'11:30','espera_min':12,'espera_max':15,
                 'dias_semana':[0,3],'max_grupos_dia':5,'tg_chat_id':None,'cookies_cifradas':None,'cookies_actualizadas':'2026-10-22T10:00:00+00:00'}],
    'grupos':[{'url':'https://www.facebook.com/groups/1','nombre':'Grupo Uno'},{'url':'https://www.facebook.com/groups/2','nombre':'Grupo\nDos'}],
    'publicaciones':[{'id':PUB_ID,'texto':'Hola 🙂','imagen_path':f'{CLIENTE_ID}/a.png'},{'id':PUB2_ID,'texto':'Segunda','imagen_path':f'{CLIENTE_ID}/b.jpg'}],
    'ordenes':[{'id':7,'cliente_id':CLIENTE_ID,'tipo':'enviar_resumen','parametros':{}}],
}
RECIBIDO = []   #(metodo, ruta, query, cuerpo)

class Falso(BaseHTTPRequestHandler):
    def log_message(self,*a):
        pass
    def _responder(self,codigo,cuerpo=b'',tipo='application/json'):
        self.send_response(codigo);self.send_header('Content-Type',tipo);self.send_header('Content-Length',str(len(cuerpo)));self.end_headers();self.wfile.write(cuerpo)
    def _manejar(self,metodo):
        u = urlparse(self.path);q = {k:v[0] for k,v in parse_qs(u.query).items()}
        largo = int(self.headers.get('Content-Length') or 0)
        cuerpo = json.loads(self.rfile.read(largo)) if largo and 'json' in (self.headers.get('Content-Type') or '') else None
        RECIBIDO.append((metodo,u.path,q,cuerpo,dict(self.headers)))
        assert self.headers.get('apikey') == 'clave-de-prueba' and self.headers.get('Authorization') == 'Bearer clave-de-prueba'
        tabla = u.path.rsplit('/',1)[-1]
        if metodo == 'GET' and u.path.startswith('/storage/v1/object/imagenes/'):
            return self._responder(200,b'IMAGEN-' + unquote(u.path).encode(),'image/png')
        if metodo == 'GET':
            if tabla == 'ordenes':
                filas = DB['ordenes'] if q.get('estado') == 'eq.pendiente' else []
            elif tabla == 'clientes' and q.get('select') == 'activo':
                filas = [{'activo':DB['clientes'][0]['activo']}]
            else:
                filas = DB.get(tabla,[])
            return self._responder(200,json.dumps(filas).encode())
        if metodo == 'PATCH' and tabla == 'ordenes':
            DB['ordenes'] = [o for o in DB['ordenes'] if f"eq.{o['id']}" != q.get('id')]
        return self._responder(201 if metodo == 'POST' else 204)
    def do_GET(self): self._manejar('GET')
    def do_POST(self): self._manejar('POST')
    def do_PATCH(self): self._manejar('PATCH')

servidor = HTTPServer(('127.0.0.1',0),Falso)
threading.Thread(target=servidor.serve_forever,daemon=True).start()
os.environ['SUPABASE_URL'] = f'http://127.0.0.1:{servidor.server_port}'
os.environ['SUPABASE_SERVICE_KEY'] = 'clave-de-prueba'

import sync_supabase as nube
import Facebook_bot as bot
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import base64

tmp = Path(tempfile.mkdtemp())
nube.DIR_CLIENTES = tmp;bot.DIR_CLIENTES = tmp
clave = rsa.generate_private_key(public_exponent=65537,key_size=2048)
(tmp / 'priv.pem').write_bytes(clave.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()))
nube.CLAVE_PRIVADA = tmp / 'priv.pem'
publica_b64 = base64.b64encode(clave.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)).decode()
COOKIES = json.dumps([{'name':'c_user','value':'1'},{'name':'xs','value':'ñ🙂'}])
DB['clientes'][0]['cookies_cifradas'] = nube.cifrar_sobre(COOKIES,publica_b64)

fallos = []
def comprobar(cond,texto):
    print(('OK   ' if cond else 'FALLA'),texto)
    if not cond: fallos.append(texto)

#------------------------------------------------------------------ 1. bajar
comprobar(nube.ACTIVO,'modulo activo con URL y clave')
comprobar(nube.bajar_todo() == 1,'bajar_todo devuelve 1 cliente')
d = tmp / 'demo'
cfg = json.loads((d / 'cliente.json').read_text(encoding='utf-8'))
comprobar(cfg['hora_inicio'] == '11:30' and cfg['espera_min'] == 12 and cfg['dias_semana'] == [0,3] and cfg['max_grupos_dia'] == 5,'cliente.json con la configuracion de la web')
c = bot.Cliente('demo')
comprobar(c.espera_min == 12.0 and c.dias == [0,3] and c.max_grupos == 5 and c.hora_inicio == '11:30','Cliente() lee lo bajado')
comprobar(bot.cargar_grupos(c) == ['https://www.facebook.com/groups/1','https://www.facebook.com/groups/2'],'grupos.txt con solo los grupos activos')
comprobar((d / 'grupos.txt').read_text(encoding='utf-8').count('\n') == 3,'nombre multilinea limpiado (1 linea por grupo)')
comprobar((d / 'Publicaciones' / f'p_{PUB_ID}.txt').read_text(encoding='utf-8') == 'Hola 🙂','texto de la publicacion bajado (con emoji)')
comprobar((d / 'Imagenes' / f'p_{PUB_ID}.png').read_bytes().startswith(b'IMAGEN-'),'imagen bajada desde el almacenamiento')
comprobar(len(bot.cargar_publicaciones(c)) == 2,'cargar_publicaciones empareja texto+imagen (2 pares)')
comprobar(json.loads((d / 'cookies.json').read_text(encoding='utf-8')) == json.loads(COOKIES),'cookies descifradas con la clave privada')

# idempotencia: una segunda bajada no reescribe ni vuelve a descargar nada
antes = len([r for r in RECIBIDO if r[1].startswith('/storage')])
nube.bajar_todo()
comprobar(len([r for r in RECIBIDO if r[1].startswith('/storage')]) == antes,'segunda bajada no vuelve a descargar imagenes')

# una publicacion retirada de la web desaparece del bot
DB['publicaciones'] = DB['publicaciones'][:1]
nube.bajar_todo()
comprobar(not (d / 'Publicaciones' / f'p_{PUB2_ID}.txt').exists() and not (d / 'Imagenes' / f'p_{PUB2_ID}.jpg').exists(),'publicacion eliminada en la web se retira del bot')

# archivos de la carpeta que no vienen de la nube se retiran (la web manda)
(d / 'Publicaciones' / 'vieja.txt').write_text('x');nube.bajar_todo()
comprobar(not (d / 'Publicaciones' / 'vieja.txt').exists(),'archivos locales ajenos a la nube se retiran')

#------------------------------------------------------------------ 2. subir
estado = bot.cargar_estado(c)
estado.update({'inicio':'11:30','publicados':['https://www.facebook.com/groups/1'],'en_curso':True,'bloqueo':'','nuevos_grupos':2})
bot.guardar_estado(c,estado)
ultimo = [r for r in RECIBIDO if r[1].endswith('/tandas_dia')][-1]
fila = ultimo[3][0]
comprobar(ultimo[2].get('on_conflict') == 'cliente_id,fecha' and 'merge-duplicates' in ultimo[4].get('Prefer',''),'estado del dia: upsert con on_conflict y merge-duplicates')
comprobar(fila['cliente_id'] == CLIENTE_ID and fila['publicados'] == 1 and fila['pendientes'] == 1 and fila['total_grupos'] == 2 and fila['en_curso'] and fila['bloqueo'] is None and fila['nuevos_grupos'] == 2,'estado del dia con los contadores correctos')

nube.registrar(c,estado['fecha'],'https://www.facebook.com/groups/1','Grupo Uno',f'p_{PUB_ID}',False,'BLOQUEO: x')
fila = [r for r in RECIBIDO if r[1].endswith('/publicaciones_log')][-1][3][0]
comprobar(fila['publicacion_id'] == PUB_ID and fila['ok'] is False and fila['motivo'] == 'BLOQUEO: x','historial: publicacion_id valido y motivo')
nube.registrar(c,estado['fecha'],'u','n','promo1',True,'')
fila = [r for r in RECIBIDO if r[1].endswith('/publicaciones_log')][-1][3][0]
comprobar(fila['publicacion_id'] is None and fila['motivo'] is None,'historial: publicacion local sin uuid -> null')

nube.latido('prueba')
ult = [r for r in RECIBIDO if r[1].endswith('/bot_estado')][-1]
comprobar(ult[3][0]['id'] == 1 and ult[3][0]['mensaje'] == 'prueba','latido en la fila unica id=1')

nube.subir_grupos(c)
ult = [r for r in RECIBIDO if r[1].endswith('/grupos') and r[0] == 'POST'][-1]
comprobar(ult[2].get('on_conflict') == 'cliente_id,url' and 'ignore-duplicates' in ult[4].get('Prefer','') and len(ult[3]) == 2,'subir grupos: ignore-duplicates (no pisa los desactivados)')

#------------------------------------------------------------------ 3. ordenes y pausa
bot.procesar_ordenes()
patch = [r for r in RECIBIDO if r[0] == 'PATCH' and r[1].endswith('/ordenes')]
comprobar([p[3]['estado'] for p in patch] == ['en_proceso','hecha'] and patch[-1][3]['resultado'] == 'resumen enviado' and patch[-1][3]['terminada'],'orden enviar_resumen: en_proceso -> hecha con resultado')
DB['clientes'][0]['activo'] = False
comprobar(nube.cliente_activo('demo') is False,'cliente_activo detecta la pausa desde la web')

#------------------------------------------------------------------ 4. resiliencia: la nube caida no tumba al bot
nube.URL = 'http://127.0.0.1:1'
comprobar(nube.latido() is None and nube.bajar_todo() == 0 and nube.cliente_activo('demo') is True,'con la nube caida las funciones no lanzan y cliente_activo no frena la tanda')

servidor.shutdown()
print('\nRESULTADO:','TODO OK' if not fallos else f'{len(fallos)} FALLOS')
sys.exit(1 if fallos else 0)
