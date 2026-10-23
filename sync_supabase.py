#Sincronizacion del bot con Supabase (la web de Vercel escribe, el bot del VPS lee y ejecuta)
#- BAJA: clientes, grupos activos, publicaciones (texto + imagen) y cookies a clientes/<slug>/ (la estructura de archivos de siempre)
#- SUBE: latido, estado del dia, historial de publicaciones, grupos nuevos y resultado de las ordenes
#Sin SUPABASE_URL y SUPABASE_SERVICE_KEY en el .env este modulo no hace nada y el bot trabaja solo con archivos
#Ninguna funcion publica lanza excepciones: un fallo de red no puede tumbar las publicaciones
from config.config import BASE_DIR,DIR_CLIENTES
from datetime import datetime,timezone
from pathlib import Path
import base64,json,logging,os,re,urllib.error,urllib.parse,urllib.request

log = logging.getLogger('bot')
VERSION = 'multicliente+nube'
URL = os.environ.get('SUPABASE_URL','').rstrip('/')
KEY = os.environ.get('SUPABASE_SERVICE_KEY','')
CLAVE_PRIVADA = Path(os.environ.get('COOKIE_PRIVATE_KEY_FILE') or BASE_DIR / 'config' / 'cookie_private.pem')
ACTIVO = bool(URL and KEY)
#slug <-> id de cada cliente, se rellena al bajar los clientes
_IDS = {}
_UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')

#------------------------------------------------------------------ HTTP
def _peticion(metodo,ruta,cuerpo=None,params=None,cabeceras=None,crudo=None,binario=False,timeout=30):
    url = f'{URL}{ruta}'
    if params:
        url += '?' + urllib.parse.urlencode(params,safe=',.()*:!-_')
    datos = crudo if crudo is not None else (json.dumps(cuerpo).encode() if cuerpo is not None else None)
    h = {'apikey':KEY,'Authorization':f'Bearer {KEY}'}
    if cuerpo is not None:
        h['Content-Type'] = 'application/json'
    h.update(cabeceras or {})
    req = urllib.request.Request(url,data=datos,method=metodo,headers=h)
    try:
        with urllib.request.urlopen(req,timeout=timeout) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP {e.code} {metodo} {ruta}: {e.read()[:300].decode(errors="replace")}') from None
    if binario:
        return raw
    return json.loads(raw) if raw else None

def consultar(tabla,**params):
    return _peticion('GET',f'/rest/v1/{tabla}',params=params) or []

def insertar(tabla,filas,resolucion=None,on_conflict=None,retorno=False):
    prefer = ['return=representation' if retorno else 'return=minimal']
    if resolucion:
        prefer.append(f'resolution={resolucion}')
    params = {'on_conflict':on_conflict} if on_conflict else None
    return _peticion('POST',f'/rest/v1/{tabla}',cuerpo=filas,params=params,cabeceras={'Prefer':','.join(prefer)})

def actualizar(tabla,filtros,datos):
    return _peticion('PATCH',f'/rest/v1/{tabla}',cuerpo=datos,params=filtros,cabeceras={'Prefer':'return=minimal'})

def _ahora():
    return datetime.now(timezone.utc).isoformat()

#Decorador: registra el fallo y sigue, la nube nunca debe detener al bot
def seguro(por_defecto=None):
    def deco(fn):
        def envuelto(*a,**k):
            if not ACTIVO:
                return por_defecto
            try:
                return fn(*a,**k)
            except Exception as e:
                log.warning(f'[nube] {fn.__name__}: {e}')
                return por_defecto
        envuelto.__name__ = fn.__name__
        return envuelto
    return deco

#------------------------------------------------------------------ cifrado de cookies (sobre hibrido RSA-OAEP + AES-GCM)
def descifrar_sobre(sobre,ruta_privada=None):
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    privada = serialization.load_pem_private_key((ruta_privada or CLAVE_PRIVADA).read_bytes(),password=None)
    aes = privada.decrypt(base64.b64decode(sobre['k']),padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    return AESGCM(aes).decrypt(base64.b64decode(sobre['iv']),base64.b64decode(sobre['ct']),None).decode()

def cifrar_sobre(texto,publica_b64):
    from cryptography.hazmat.primitives import hashes,serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    publica = serialization.load_der_public_key(base64.b64decode(publica_b64.strip()))
    aes = AESGCM.generate_key(bit_length=256)
    iv = os.urandom(12)
    ct = AESGCM(aes).encrypt(iv,texto.encode(),None)
    k = publica.encrypt(aes,padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
    return {'v':1,'k':base64.b64encode(k).decode(),'iv':base64.b64encode(iv).decode(),'ct':base64.b64encode(ct).decode()}

#------------------------------------------------------------------ BAJAR (nube -> archivos)
def _escribir_si_cambia(ruta,texto):
    if ruta.is_file() and ruta.read_text(encoding='utf-8') == texto:
        return False
    ruta.write_text(texto,encoding='utf-8')
    return True

def _limpio(texto):
    return ' '.join(str(texto or '').split())

def _bajar_config(fila,carpeta):
    cfg = {'nombre':fila['nombre'],'activo':fila['activo'],'hora_inicio':fila['hora_inicio'],
           'espera_min':fila['espera_min'],'espera_max':fila['espera_max'],'dias_semana':fila['dias_semana'],
           'max_grupos_dia':fila['max_grupos_dia'],'tg_chat_id':fila['tg_chat_id'] or ''}
    _escribir_si_cambia(carpeta / 'cliente.json',json.dumps(cfg,indent=2,ensure_ascii=False))

def _texto_grupos(filas):
    lineas = ['# Una url de grupo por linea. Las lineas con # se ignoran. (Generado desde Supabase)']
    lineas += [f"{f['url']}  # {_limpio(f['nombre']) or f['url']}" for f in filas]
    return '\n'.join(lineas) + '\n'

def _bajar_grupos(fila,carpeta):
    filas = consultar('grupos',select='url,nombre',cliente_id=f"eq.{fila['id']}",activo='eq.true',order='nombre.asc')
    _escribir_si_cambia(carpeta / 'grupos.txt',_texto_grupos(filas))

def _bajar_publicaciones(fila,carpeta):
    filas = consultar('publicaciones',select='id,texto,imagen_path',cliente_id=f"eq.{fila['id']}",activo='eq.true',order='creada.asc')
    dir_txt,dir_img = carpeta / 'Publicaciones',carpeta / 'Imagenes'
    dir_txt.mkdir(exist_ok=True)
    dir_img.mkdir(exist_ok=True)
    deseados_txt,deseados_img = set(),set()
    for p in filas:
        stem = f"p_{p['id']}"
        img = dir_img / f"{stem}{Path(p['imagen_path']).suffix.lower()}"
        if not img.is_file():
            ruta = '/storage/v1/object/imagenes/' + urllib.parse.quote(p['imagen_path'])
            try:
                img.write_bytes(_peticion('GET',ruta,binario=True,timeout=60))
            except Exception as e:
                log.warning(f"[nube] no se pudo bajar la imagen de {stem}: {e}")
                continue
        _escribir_si_cambia(dir_txt / f'{stem}.txt',p['texto'])
        deseados_txt.add(f'{stem}.txt')
        deseados_img.add(img.name)
    #La carpeta de un cliente de la nube se gestiona desde la web: lo que ya no esta alli se retira
    for f in dir_txt.glob('*'):
        if f.is_file() and f.name not in deseados_txt:
            f.unlink()
    for f in dir_img.glob('*'):
        if f.is_file() and f.name not in deseados_img:
            f.unlink()

def _bajar_cookies(fila,carpeta):
    if not fila.get('cookies_cifradas'):
        return
    marca = carpeta / 'cookies.version'
    version = str(fila.get('cookies_actualizadas'))
    if marca.is_file() and marca.read_text() == version and (carpeta / 'cookies.json').is_file():
        return
    texto = descifrar_sobre(fila['cookies_cifradas'])
    json.loads(texto)
    destino = carpeta / 'cookies.json'
    destino.write_text(texto,encoding='utf-8')
    try:
        os.chmod(destino,0o600)
    except OSError:
        pass
    marca.write_text(version)
    log.info(f"[nube] cookies nuevas descifradas para {fila['slug']}")

@seguro(0)
def bajar_todo():
    filas = consultar('clientes',select='*')
    for fila in filas:
        _IDS[fila['slug']] = fila['id']
        carpeta = DIR_CLIENTES / fila['slug']
        carpeta.mkdir(parents=True,exist_ok=True)
        for paso in (_bajar_config,_bajar_grupos,_bajar_publicaciones,_bajar_cookies):
            try:
                paso(fila,carpeta)
            except Exception as e:
                log.warning(f"[nube] {fila['slug']} {paso.__name__}: {e}")
    return len(filas)

@seguro()
def bajar_grupos(c):
    id_c = _IDS.get(c.slug)
    if id_c:
        _bajar_grupos({'id':id_c},c.dir)

#------------------------------------------------------------------ SUBIR (bot -> nube)
@seguro()
def latido(mensaje=''):
    insertar('bot_estado',[{'id':1,'ultima_conexion':_ahora(),'version':VERSION,'mensaje':mensaje}],resolucion='merge-duplicates')

@seguro(True)
def cliente_activo(slug):
    filas = consultar('clientes',select='activo',slug=f'eq.{slug}')
    return filas[0]['activo'] if filas else True

@seguro()
def subir_estado(c,estado,total_grupos,pendientes):
    id_c = _IDS.get(c.slug)
    if not id_c:
        return
    insertar('tandas_dia',[{'cliente_id':id_c,'fecha':estado['fecha'],'inicio':estado['inicio'] or None,'fin':estado['fin'] or None,
        'publicados':len(estado['publicados']),'fallidos':len(estado['fallidos']),'pendientes':pendientes,'total_grupos':total_grupos,
        'nuevos_grupos':estado['nuevos_grupos'],'bloqueo':estado['bloqueo'] or None,'abortada':estado['abortada'] or None,
        'en_curso':estado['en_curso'],'resumen_enviado':estado['resumen_enviado'],'actualizado':_ahora()}],
        resolucion='merge-duplicates',on_conflict='cliente_id,fecha')

@seguro()
def registrar(c,fecha,url,nombre,stem,ok,motivo):
    id_c = _IDS.get(c.slug)
    if not id_c:
        return
    pub_id = stem[2:] if stem.startswith('p_') and _UUID.match(stem[2:]) else None
    insertar('publicaciones_log',[{'cliente_id':id_c,'fecha':fecha,'grupo_url':url,'grupo_nombre':nombre or None,
        'publicacion_id':pub_id,'ok':ok,'motivo':(motivo or None)}])

#Sube los grupos del grupos.txt local que aun no esten en la nube (los existentes, activos o no, no se tocan)
@seguro()
def subir_grupos(c):
    id_c = _IDS.get(c.slug)
    if not id_c or not c.archivo_grupos.is_file():
        return
    filas = []
    for linea in c.archivo_grupos.read_text(encoding='utf-8').splitlines():
        url = linea.split('  #')[0].strip()
        if url and not url.startswith('#'):
            nombre = linea.split('  #',1)[1].strip() if '  #' in linea else None
            filas.append({'cliente_id':id_c,'url':url,'nombre':nombre})
    if filas:
        insertar('grupos',filas,resolucion='ignore-duplicates',on_conflict='cliente_id,url')
        #Los grupos que ya estaban sin nombre real (solo el numero) reciben el nombre leido
        existentes = {g['url']:g['nombre'] for g in consultar('grupos',select='url,nombre',cliente_id=f'eq.{id_c}')}
        for f in filas:
            actual = existentes.get(f['url'])
            if f['nombre'] and not f['nombre'].isdigit() and f['url'] in existentes and (not actual or actual.isdigit()):
                actualizar('grupos',{'cliente_id':f'eq.{id_c}','url':f"eq.{f['url']}"},{'nombre':f['nombre']})

#URLs de todos los grupos del cliente en la nube (activos o excluidos); vacio si no hay nube
@seguro(set())
def urls_conocidas(c):
    id_c = _IDS.get(c.slug)
    return {g['url'] for g in consultar('grupos',select='url',cliente_id=f'eq.{id_c}')} if id_c else set()

#Excluye un grupo de los proximos dias (p. ej. uno de compraventa); se puede volver a incluir desde la web
@seguro()
def excluir_grupo(c,url):
    id_c = _IDS.get(c.slug)
    if id_c:
        actualizar('grupos',{'cliente_id':f'eq.{id_c}','url':f'eq.{url}'},{'activo':False})

#------------------------------------------------------------------ ordenes de la web
@seguro([])
def ordenes_pendientes():
    return consultar('ordenes',select='*',estado='eq.pendiente',order='creada.asc',limit='10')

def slug_de(id_cliente):
    return next((s for s,i in _IDS.items() if i == id_cliente),None)

@seguro()
def marcar_orden(id_orden,estado,resultado=''):
    datos = {'estado':estado,'resultado':resultado[:500] or None}
    if estado in ('hecha','error'):
        datos['terminada'] = _ahora()
    actualizar('ordenes',{'id':f'eq.{id_orden}'},datos)
