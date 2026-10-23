#Migra clientes locales (clientes/<slug>/) a Supabase: configuracion, grupos, publicaciones con imagen y cookies cifradas
#Uso (en el VPS, con SUPABASE_URL y SUPABASE_SERVICE_KEY en el .env): python migrar_a_supabase.py astro
#Se puede repetir: no duplica clientes, grupos ni publicaciones
import json,mimetypes,os,sys,urllib.parse,uuid
from datetime import datetime,timezone
from pathlib import Path
from config.config import BASE_DIR,DIR_CLIENTES,EXT_IMAGEN
import sync_supabase as nube

def migrar(slug):
    carpeta = DIR_CLIENTES / slug
    cfg = json.loads((carpeta / 'cliente.json').read_text(encoding='utf-8'))
    fila = {'slug':slug,'nombre':cfg['nombre'],'activo':bool(cfg.get('activo')),'hora_inicio':cfg.get('hora_inicio','10:00'),
            'espera_min':cfg['espera_min'],'espera_max':cfg['espera_max'],'dias_semana':cfg.get('dias_semana'),
            'max_grupos_dia':cfg.get('max_grupos_dia'),'tg_chat_id':cfg.get('tg_chat_id') or None}
    id_c = nube.insertar('clientes',[fila],resolucion='merge-duplicates',on_conflict='slug',retorno=True)[0]['id']
    print(f'[{slug}] cliente en Supabase: {id_c}')

    #Grupos (los que ya existan, activos o no, no se tocan)
    grupos = []
    archivo = carpeta / 'grupos.txt'
    for linea in archivo.read_text(encoding='utf-8').splitlines() if archivo.is_file() else []:
        url = linea.split('  #')[0].strip()
        if url and not url.startswith('#'):
            grupos.append({'cliente_id':id_c,'url':url,'nombre':linea.split('  #',1)[1].strip() if '  #' in linea else None})
    if grupos:
        nube.insertar('grupos',grupos,resolucion='ignore-duplicates',on_conflict='cliente_id,url')
    print(f'[{slug}] grupos: {len(grupos)}')

    #Publicaciones (texto + imagen): solo si el cliente aun no tiene ninguna en la nube
    if nube.consultar('publicaciones',select='id',cliente_id=f'eq.{id_c}',limit='1'):
        print(f'[{slug}] publicaciones: ya existen en la nube, no se duplican')
    else:
        n = 0
        for txt in sorted((carpeta / 'Publicaciones').glob('*.txt')):
            img = next((i for i in sorted((carpeta / 'Imagenes').glob(f'{txt.stem}.*')) if i.suffix.lower() in EXT_IMAGEN),None)
            if not img:
                print(f'[{slug}] {txt.name} sin imagen, se omite')
                continue
            ruta = f'{id_c}/{uuid.uuid4()}{img.suffix.lower()}'
            nube._peticion('POST','/storage/v1/object/imagenes/' + urllib.parse.quote(ruta),crudo=img.read_bytes(),
                           cabeceras={'Content-Type':mimetypes.guess_type(img.name)[0] or 'image/png'},timeout=120)
            nube.insertar('publicaciones',[{'cliente_id':id_c,'texto':txt.read_text(encoding='utf-8').strip(),'imagen_path':ruta}])
            n += 1
        print(f'[{slug}] publicaciones subidas: {n}')

    #Cookies cifradas con la clave publica (el servidor de la web nunca las ve en claro)
    cookies = carpeta / 'cookies.json'
    publica = BASE_DIR / 'config' / 'cookie_public.b64'
    if cookies.is_file() and publica.is_file():
        ahora = datetime.now(timezone.utc).isoformat()
        nube.actualizar('clientes',{'id':f'eq.{id_c}'},{'cookies_cifradas':nube.cifrar_sobre(cookies.read_text(encoding='utf-8'),publica.read_text()),'cookies_actualizadas':ahora})
        print(f'[{slug}] cookies cifradas y subidas')
    else:
        print(f'[{slug}] cookies: no se subieron (falta cookies.json o config/cookie_public.b64)')

if __name__ == '__main__':
    if not nube.ACTIVO:
        sys.exit('Faltan SUPABASE_URL y SUPABASE_SERVICE_KEY en el .env')
    if len(sys.argv) < 2:
        sys.exit('Uso: python migrar_a_supabase.py <slug> [<slug> ...]')
    for s in sys.argv[1:]:
        migrar(s)
