from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from datetime import datetime
from config.config import *
import json,logging,os,random,re,sys,time,html
import urllib.request,urllib.parse
import sync_supabase as nube

log = logging.getLogger('bot')
#Navegador y espera compartidos por las funciones de una tanda
driver = None
wait = None

class LoginError(Exception):
    pass

#Cada cliente tiene su carpeta clientes/<slug>/ con cliente.json, cookies.json, grupos.txt, Publicaciones/ e Imagenes/
class Cliente:
    def __init__(self,slug):
        self.slug = slug
        self.dir = DIR_CLIENTES / slug
        cfg = json.loads((self.dir / 'cliente.json').read_text(encoding='utf-8'))
        self.nombre = cfg.get('nombre',slug)
        self.activo = cfg.get('activo',False)
        self.hora_inicio = cfg.get('hora_inicio',HORA_INICIO)
        #Dias de la semana en que publica (0=lunes ... 6=domingo); sin definir = todos los dias
        self.dias = cfg.get('dias_semana')
        self.espera_min = float(cfg.get('espera_min',ESPERA_MIN))
        self.espera_max = float(cfg.get('espera_max',ESPERA_MAX))
        #Maximo de grupos por tanda (si no se define, todos)
        self.max_grupos = cfg.get('max_grupos_dia')
        #Chat de Telegram del cliente (opcional): recibe solo su resumen diario
        self.tg_chat = str(cfg.get('tg_chat_id') or '')
        self.publicaciones = self.dir / 'Publicaciones'
        self.imagenes = self.dir / 'Imagenes'
        self.archivo_grupos = self.dir / 'grupos.txt'
        self.archivo_cookies = self.dir / 'cookies.json'
        self.archivo_estado = self.dir / 'estado.json'

    def inicio_hoy(self):
        hora,minuto = map(int,self.hora_inicio.split(':'))
        return datetime.now().replace(hour=hora,minute=minuto,second=0,microsecond=0)

#Funcion para listar los clientes (todos o solo los activos)
def cargar_clientes(solo_activos=True):
    clientes = []
    if DIR_CLIENTES.is_dir():
        for carpeta in sorted(DIR_CLIENTES.iterdir()):
            if (carpeta / 'cliente.json').is_file():
                try:
                    c = Cliente(carpeta.name)
                except Exception as e:
                    log.error(f'cliente.json invalido en {carpeta.name}: {e}')
                    continue
                if c.activo or not solo_activos:
                    clientes.append(c)
    return sorted(clientes,key=lambda c:c.hora_inicio)

#Funcion para crear la estructura de un cliente nuevo (queda inactivo hasta que se configure)
def crear_cliente(slug,nombre,espera_min,espera_max):
    c_dir = DIR_CLIENTES / slug
    if (c_dir / 'cliente.json').exists():
        print(f'El cliente {slug} ya existe')
        return
    (c_dir / 'Publicaciones').mkdir(parents=True)
    (c_dir / 'Imagenes').mkdir()
    cfg = {'nombre':nombre,'activo':False,'hora_inicio':'10:00','espera_min':espera_min,'espera_max':espera_max,'dias_semana':None,'max_grupos_dia':None,'tg_chat_id':''}
    (c_dir / 'cliente.json').write_text(json.dumps(cfg,indent=2,ensure_ascii=False),encoding='utf-8')
    (c_dir / 'grupos.txt').write_text('# Una url de grupo por linea. Las lineas con # se ignoran.\n',encoding='utf-8')
    print(f'Cliente creado en {c_dir}')
    print('Siguientes pasos: 1) python login_manual.py '+slug+'  2) poner textos/imagenes emparejados en Publicaciones/ e Imagenes/  3) "activo": true en cliente.json')

#Funcion para configurar el log (consola + archivo)
def configurar_log():
    DIR_LOGS.mkdir(exist_ok=True)
    formato = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s','%Y-%m-%d %H:%M:%S')
    log.setLevel(logging.INFO)
    for handler in (logging.StreamHandler(),logging.FileHandler(DIR_LOGS / 'bot.log',encoding='utf-8')):
        handler.setFormatter(formato)
        log.addHandler(handler)

#Funcion para obtener el chat del administrador (del .env o detectado cuando escribe /start al bot)
def chat_telegram():
    if TG_CHAT_ID:
        return TG_CHAT_ID
    if ARCHIVO_CHAT.is_file():
        return ARCHIVO_CHAT.read_text().strip()
    try:
        with urllib.request.urlopen(f'https://api.telegram.org/bot{TG_TOKEN}/getUpdates',timeout=15) as r:
            for upd in reversed(json.load(r).get('result',[])):
                chat = (upd.get('message') or {}).get('chat',{}).get('id')
                if chat:
                    ARCHIVO_CHAT.write_text(str(chat))
                    return str(chat)
    except Exception as e:
        log.warning(f'Telegram getUpdates: {e}')
    return ''

def _enviar_telegram(chat,texto):
    #Telegram admite 4096 caracteres por mensaje: se parte por lineas en trozos
    trozos = ['']
    for linea in texto.split('\n'):
        if len(trozos[-1]) + len(linea) + 1 > 3800:
            trozos.append('')
        trozos[-1] += linea + '\n'
    for trozo in trozos:
        try:
            datos = urllib.parse.urlencode({'chat_id':chat,'text':trozo.strip(),'parse_mode':'HTML','disable_web_page_preview':'true'}).encode()
            urllib.request.urlopen(f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage',datos,timeout=15).read()
        except Exception as e:
            log.warning(f'Telegram sendMessage: {e}')

#Funcion para enviar un aviso por Telegram al administrador y, si se indica, al chat del cliente (nunca detiene el bot)
def avisar(texto,chat_cliente=''):
    if not TG_TOKEN:
        return
    admin = chat_telegram()
    if not admin:
        log.warning('Telegram: aun no hay chat, escribe /start a @AlertCTF_bot')
    else:
        _enviar_telegram(admin,texto)
    if chat_cliente and chat_cliente != admin:
        _enviar_telegram(chat_cliente,texto)

def esc(x):
    return html.escape(str(x))

#Funcion para inicializar el driver Firefox
def run_firefox():
    options = Options()
    if HEADLESS:
        options.add_argument('--headless')#No muestra el navegador
    options.add_argument('--width=1366')
    options.add_argument('--height=900')
    options.set_preference('dom.webnotifications.enabled',False)#Desabilita las notificaciones
    options.set_preference('intl.accept_languages','es-ES,es')#Selecciona el idioma del navegador
    #Si no se indica geckodriver, Selenium Manager lo descarga solo
    service = Service(executable_path=GECKODRIVER_PATH) if GECKODRIVER_PATH else Service()
    return webdriver.Firefox(service=service,options=options)

#Funcion para leer los grupos del cliente (una url por linea, # para comentarios)
def cargar_grupos(c):
    if not c.archivo_grupos.is_file():
        log.error(f'[{c.slug}] No existe {c.archivo_grupos}')
        return []
    grupos = []
    for linea in c.archivo_grupos.read_text(encoding='utf-8').splitlines():
        linea = linea.split('  #')[0].strip()
        if linea and not linea.startswith('#') and linea not in grupos:
            grupos.append(linea)
    return grupos

#Funcion para emparejar cada texto con su imagen (publicacion1.txt <-> publicacion1.jpg/png/...)
def cargar_publicaciones(c):
    pares = []
    for txt in sorted(c.publicaciones.glob('*.txt')):
        imagen = next((i for i in sorted(c.imagenes.glob(f'{txt.stem}.*')) if i.suffix.lower() in EXT_IMAGEN),None)
        if imagen:
            pares.append((txt,imagen))
        else:
            log.warning(f'[{c.slug}] {txt.name} no tiene imagen en Imagenes/, se omite')
    return pares

#Funciones para guardar y leer lo ya publicado hoy (permite reanudar si el bot se reinicia)
def cargar_estado(c):
    hoy = datetime.now().strftime('%Y-%m-%d')
    estado = {'fecha':hoy,'publicados':[],'fallidos':[],'motivos':{},'indice':0,'cursor':0,'en_curso':False,'inicio':'','fin':'','abortada':'','bloqueo':'','nuevos_grupos':0,'resumen_enviado':False}
    if c.archivo_estado.is_file():
        guardado = json.loads(c.archivo_estado.read_text(encoding='utf-8'))
        estado['indice'] = guardado.get('indice',0)
        estado['cursor'] = guardado.get('cursor',0)
        if guardado.get('fecha') == hoy:
            estado.update(guardado)
    return estado

def guardar_estado(c,estado):
    c.archivo_estado.write_text(json.dumps(estado,indent=2),encoding='utf-8')
    if nube.ACTIVO:
        grupos = cargar_grupos(c)
        nube.subir_estado(c,estado,len(grupos),len(pendientes(estado,grupos)))

def pendientes(estado,grupos):
    return [g for g in grupos if g not in estado['publicados'] and g not in estado['fallidos']]

#Funcion para escribir el texto en el cuadro de publicacion (soporta emojis y saltos de linea)
def escribir_texto(caja,texto):
    caja.click()
    lineas = texto.strip().splitlines()
    for n,linea in enumerate(lineas):
        if linea:
            driver.execute_script("document.execCommand('insertText',false,arguments[0])",linea)
        if n < len(lineas)-1:
            caja.send_keys(Keys.SHIFT,Keys.ENTER)

#Funcion para abrir el cuadro de publicacion; si un popup de Facebook lo tapa se cierra con Escape y se reintenta
def abrir_composer():
    xpath = "//span[contains(text(),'Escribe algo') or contains(text(),'Write something')]"
    time.sleep(5)
    for intento in range(4):
        driver.find_element(By.TAG_NAME,'body').send_keys(Keys.ESCAPE)
        time.sleep(2)
        try:
            wait.until(ec.element_to_be_clickable((By.XPATH,xpath))).click()
            return
        except Exception:
            if intento == 3:
                raise
            time.sleep(3)

#Avisos con los que Facebook informa de un bloqueo o limite temporal de la cuenta (minusculas)
PATRONES_BLOQUEO = ('bloqueado temporalmente','bloqueo temporal','temporalmente bloquead','restringido temporalmente','temporalmente restringid','no puedes publicar','no puedes usar esta funci','limitamos la frecuencia','hemos limitado','actividad inusual','temporarily blocked','temporarily restricted',"you can't post",'you can\u2019t post','we limit how often','unusual activity')

#Funcion para detectar si Facebook limito la cuenta: busca esos avisos en ventanas y alertas de la pagina o una pagina de verificacion
def detectar_bloqueo():
    try:
        if any(x in driver.current_url for x in ('checkpoint','two_step')):
            return 'pagina de verificacion de Facebook (checkpoint)'
        textos = driver.execute_script("return [...document.querySelectorAll('[role=\"dialog\"],[role=\"alert\"]')].map(e=>e.innerText).join(' | ')") or ''
        textos = textos.lower()
        for patron in PATRONES_BLOQUEO:
            if patron in textos:
                return f'aviso de Facebook: "{patron}"'
    except Exception:
        pass
    return ''

#Funcion para realizar una publicacion con texto e imagen
def publicar_grupo(c,url,texto,imagen):
    dialogo = "//div[@role='dialog']"
    try:
        driver.get(url)
        #Abrimos el contenedor de publicaciones
        abrir_composer()
        #Aqui va el texto de la publicacion
        caja = wait.until(ec.element_to_be_clickable((By.XPATH,f"{dialogo}//div[@role='textbox' and @contenteditable='true']")))
        escribir_texto(caja,texto)
        #El cuadro ya incluye el input de archivo, no hace falta pulsar el boton de foto
        archivo = wait.until(ec.presence_of_element_located((By.XPATH,f"{dialogo}//input[@type='file' and contains(@accept,'image')]")))
        archivo.send_keys(str(imagen))
        #Clic al boton publicar (solo se habilita cuando la imagen termino de subir)
        publicar = WebDriverWait(driver,90).until(ec.element_to_be_clickable((By.XPATH,f"{dialogo}//div[@role='button' and (@aria-label='Publicar' or @aria-label='Post') and not(@aria-disabled='true')]")))
        publicar.click()
        #El dialogo se cierra cuando la publicacion fue enviada
        WebDriverWait(driver,90).until(ec.invisibility_of_element_located((By.XPATH,dialogo)))
        return True,''
    except Exception as e:
        motivo = f'{type(e).__name__} {str(e)[:100]}'.strip()
        log.error(f'[{c.slug}] Fallo al publicar en {url}: {motivo}')
        #Captura para saber que vio el bot cuando fallo
        driver.save_screenshot(str(DIR_LOGS / f'error_{c.slug}_{datetime.now():%Y%m%d_%H%M%S}.png'))
        aviso = detectar_bloqueo()
        if aviso:
            motivo = f'BLOQUEO: {aviso}'
        return False,motivo

#Funcion para comprobar si hay sesion iniciada
def sesion_activa(espera=90):
    fin = time.time() + espera
    while time.time() < fin:
        try:
            if driver.find_elements(By.CSS_SELECTOR,'input[type="search"]'):
                return True
            #Si aparece el formulario de login la sesion ya no es valida
            if driver.find_elements(By.NAME,'email'):
                return False
        except Exception:
            pass
        time.sleep(2)
    return False

#Funcion para leer los grupos a los que pertenece la cuenta y sumar los nuevos a grupos.txt del cliente
#Los grupos que ya estaban se conservan y, si la lectura falla, la lista actual no se toca; devuelve cuantos grupos nuevos entraron
def obtener_grupos(c):
    driver.get('https://www.facebook.com/groups/joins/')
    time.sleep(5)
    excluidos = {'joins','feed','discover','create','search','notifications','your_groups'}
    encontrados = {}
    sin_nuevos = 0
    errores = 0
    while sin_nuevos < 4 and errores < 5:
        try:
            antes = len(encontrados)
            for a in driver.find_elements(By.CSS_SELECTOR,'a[href*="/groups/"]'):
                m = re.match(r'https://www\.facebook\.com/groups/([^/?#]+)',a.get_attribute('href') or '')
                if m and m.group(1) not in excluidos:
                    encontrados.setdefault(m.group(1),a.text.strip().split('\n')[0] or m.group(1))
            sin_nuevos = sin_nuevos + 1 if len(encontrados) == antes else 0
            driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        except Exception as e:
            errores += 1
            log.warning(f'[{c.slug}] Error leyendo grupos ({type(e).__name__}), reintento {errores}/5')
        time.sleep(3)
    if not encontrados:
        log.warning(f'[{c.slug}] No se leyo ningun grupo, se conserva la lista actual')
        return 0
    actuales = {}
    if c.archivo_grupos.is_file():
        for linea in c.archivo_grupos.read_text(encoding='utf-8').splitlines():
            url = linea.split('  #')[0].strip()
            if url and not url.startswith('#'):
                actuales[url] = linea.strip()
    nuevos = 0
    for slug,nombre in encontrados.items():
        url = f'https://www.facebook.com/groups/{slug}'
        if url not in actuales:
            actuales[url] = f'{url}  # {nombre}'
            nuevos += 1
    c.archivo_grupos.write_text('# Una url de grupo por linea. Las lineas con # se ignoran.\n' + '\n'.join(actuales.values()) + '\n',encoding='utf-8')
    log.info(f'[{c.slug}] Grupos en la cuenta: {len(encontrados)}; en grupos.txt: {len(actuales)} ({nuevos} nuevos)')
    return nuevos

#Funcion para entrar a facebook con las cookies del cliente (nunca con contrasena: no se guardan contrasenas ajenas)
def logging_fb(c):
    if not c.archivo_cookies.is_file():
        raise LoginError(f'[{c.slug}] No hay cookies. Ejecuta login_manual.py {c.slug} en el PC y sube clientes/{c.slug}/cookies.json')
    log.info(f'[{c.slug}] Realizando login por cookies..')
    #Accedemos a una pagina ligera del dominio para poder cargar las cookies
    driver.get(URL_robot)
    for cookie in json.loads(c.archivo_cookies.read_text(encoding='utf-8')):
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass
    driver.get(URL_logg)
    if sesion_activa():
        log.info(f'[{c.slug}] Login por cookies: OK')
        return
    #No se borran las cookies ni se intenta otro login: Facebook lo veria como un acceso sospechoso
    driver.save_screenshot(str(DIR_LOGS / f'login_error_{c.slug}.png'))
    raise LoginError(f'[{c.slug}] La sesion no es valida (cookies caducadas o verificacion pendiente). Repite login_manual.py {c.slug} y sube las cookies; ver logs/login_error_{c.slug}.png')

#Funcion para tomar el turno de la tanda (solo una a la vez)
def tomar_turno():
    if ARCHIVO_LOCK.exists() and time.time() - ARCHIVO_LOCK.stat().st_mtime < 6*3600:
        return False
    ARCHIVO_LOCK.write_text(str(os.getpid()))
    return True

def soltar_turno():
    ARCHIVO_LOCK.unlink(missing_ok=True)

#Funcion para esperar entre publicaciones: mantiene el latido y comprueba si desde la web pausaron al cliente
def esperar(c,segundos):
    fin = time.time() + segundos
    while time.time() < fin:
        time.sleep(min(30,max(0,fin - time.time())))
        if nube.ACTIVO:
            nube.latido(f'publicando: {c.nombre}')
            if not nube.cliente_activo(c.slug):
                return False
    return True

#Funcion que publica en los grupos pendientes de hoy del cliente, uno cada 8 a 10 minutos
def ejecutar_tanda(c,estado,grupos,limite=None,manual=False):
    global driver,wait
    publicaciones = cargar_publicaciones(c)
    if not publicaciones:
        log.error(f'[{c.slug}] No hay publicaciones con imagen, se cancela la tanda')
        avisar(f'⚠️ <b>{esc(c.nombre)}</b>: no hay publicaciones con imagen, tanda cancelada.')
        #Se da por abortada hasta manana: si no, se reintentaria (y avisaria) cada minuto
        estado['abortada'] = 'Sin publicaciones con imagen'
        guardar_estado(c,estado)
        return
    if limite is None:
        limite = c.max_grupos
    log.info(f'[{c.slug}] Iniciando tanda: {len(pendientes(estado,grupos))} grupos pendientes')
    estado['en_curso'] = True
    estado['inicio'] = estado['inicio'] or datetime.now().strftime('%H:%M')
    guardar_estado(c,estado)
    driver = run_firefox()
    wait = WebDriverWait(driver,20)
    fallos_seguidos = 0
    hechos = 0
    abortada = ''
    try:
        logging_fb(c)
        #Cada tanda empieza revisando los grupos de la cuenta: la lista crece sola, los nuevos entran hoy mismo
        try:
            estado['nuevos_grupos'] += obtener_grupos(c)
            #Con Supabase: los grupos nuevos suben a la web y se vuelve a bajar la lista (respeta los desactivados)
            nube.subir_grupos(c)
            nube.bajar_grupos(c)
        except Exception as e:
            log.warning(f'[{c.slug}] No se pudo revisar la lista de grupos ({type(e).__name__}), se usa la anterior')
        grupos = cargar_grupos(c)
        #Los grupos rotan segun el cursor: si hay tope diario, cada dia toca un tramo distinto
        cursor = estado['cursor'] % len(grupos) if grupos else 0
        orden = grupos[cursor:] + grupos[:cursor]
        while pendientes(estado,orden) and (limite is None or hechos < limite):
            url = pendientes(estado,orden)[0]
            #Las publicaciones rotan en orden, asi no se repite el mismo post en dias seguidos
            txt,imagen = publicaciones[estado['indice'] % len(publicaciones)]
            estado['indice'] += 1
            log.info(f'[{c.slug}] Publicando {txt.stem} en el grupo: {url}')
            hechos += 1
            ok,motivo = publicar_grupo(c,url,txt.read_text(encoding='utf-8'),imagen)
            nube.registrar(c,estado['fecha'],url,nombres_grupos(c).get(url),txt.stem,ok,motivo)
            if ok:
                estado['publicados'].append(url)
                fallos_seguidos = 0
                log.info(f'[{c.slug}] Publicado correctamente')
            else:
                estado['fallidos'].append(url)
                estado['motivos'][url] = motivo
                fallos_seguidos += 1
                if motivo.startswith('BLOQUEO'):
                    #Facebook limito la cuenta: seguir publicando solo lo empeora, se avisa y se detiene la tanda de hoy
                    estado['bloqueo'] = motivo
                    abortada = 'Facebook limito o bloqueo la cuenta, tanda detenida'
                    log.error(f'[{c.slug}] {abortada}: {motivo}')
                    avisar(f'🚫 <b>{esc(c.nombre)}: posible bloqueo temporal</b>\n{esc(motivo)}\nGrupo: {esc(url)}\nPublicadas hoy antes del bloqueo: {len(estado["publicados"])}',c.tg_chat)
                    break
                if fallos_seguidos >= MAX_FALLOS_SEGUIDOS:
                    abortada = f'{fallos_seguidos} fallos seguidos, tanda abortada'
                    log.error(f'[{c.slug}] {abortada}. Revisa logs/')
                    avisar(f'⚠️ <b>{esc(c.nombre)}</b>: {esc(abortada)}.\nUltimo error: {esc(motivo)}',c.tg_chat)
                    break
            guardar_estado(c,estado)
            if pendientes(estado,orden) and (limite is None or hechos < limite):
                espera = random.uniform(c.espera_min*60,c.espera_max*60)
                log.info(f'[{c.slug}] Siguiente publicacion en {espera/60:.1f} min')
                if not esperar(c,espera) and not manual:
                    abortada = 'Cliente pausado desde la web, tanda detenida'
                    log.warning(f'[{c.slug}] {abortada}')
                    break
        estado['cursor'] = (cursor + hechos) % len(grupos) if grupos else 0
        log.info(f'[{c.slug}] Tanda terminada: {len(estado["publicados"])} publicados, {len(estado["fallidos"])} fallidos')
    except LoginError as e:
        log.error(f'Login: {e}')
        avisar(f'🚨 <b>{esc(c.nombre)}: error de login</b>\n{esc(e)}')
        #Se da por abortada hasta manana: reintentar el login cada minuto levantaria sospechas en Facebook
        abortada = f'Error de login: {str(e)[:150]}'
        return
    finally:
        driver.quit()
        estado['en_curso'] = False
        estado['fin'] = datetime.now().strftime('%H:%M')
        if abortada:
            estado['abortada'] = abortada
        guardar_estado(c,estado)

#Funcion para leer los nombres de los grupos (comentarios de grupos.txt) y mostrar nombres en vez de urls
def nombres_grupos(c):
    nombres = {}
    if c.archivo_grupos.is_file():
        for linea in c.archivo_grupos.read_text(encoding='utf-8').splitlines():
            if '  #' in linea:
                url,nombre = linea.split('  #',1)
                nombres[url.strip()] = nombre.strip()
    return nombres

#Funcion para enviar el resumen del dia por Telegram (administrador y cliente); una vez al dia a HORA_RESUMEN
def resumen_diario(c,estado,grupos,marcar=True):
    nombres = nombres_grupos(c)
    nombre = lambda u: esc(nombres.get(u,u))
    if not estado['publicados'] and not estado['fallidos']:
        msg = [f'📊 <b>{esc(c.nombre)} · Resumen del {estado["fecha"]}</b>','Hoy no se publico nada. Revisa el servicio.']
    else:
        horario = f'{estado["inicio"]} a {estado["fin"]}' if estado['fin'] else f'desde las {estado["inicio"]} (aun en curso)'
        msg = [f'📊 <b>{esc(c.nombre)} · Resumen del {estado["fecha"]}</b>',
               f'✅ Publicadas: {len(estado["publicados"])}',
               f'❌ Fallidas: {len(estado["fallidos"])}',
               f'⏳ Pendientes: {len(pendientes(estado,grupos))}',
               f'📋 Grupos en la lista: {len(grupos)} ({estado["nuevos_grupos"]} nuevos hoy)',
               f'🕙 Horario: {horario}']
        if estado['bloqueo']:
            msg.append(f'🚫 Bloqueo detectado: {esc(estado["bloqueo"])}')
        elif estado['abortada']:
            msg.append(f'⚠️ {esc(estado["abortada"])}')
        if estado['publicados']:
            msg.append('\n<b>Exitos:</b>')
            msg += [f'• {nombre(u)}' for u in estado['publicados']]
        if estado['fallidos']:
            msg.append('\n<b>Fracasos:</b>')
            msg += [f'• {nombre(u)}\n   {esc(estado["motivos"].get(u,""))}' for u in estado['fallidos']]
    avisar('\n'.join(msg),c.tg_chat)
    if marcar:
        estado['resumen_enviado'] = True
        guardar_estado(c,estado)

#Funcion que decide si ya toca enviar el resumen del dia (pasada HORA_RESUMEN, una sola vez y sin tanda en curso)
def toca_resumen(c,estado):
    if c.dias is not None and datetime.now().weekday() not in c.dias:
        return False
    hora,minuto = map(int,HORA_RESUMEN.split(':'))
    ya_es_hora = datetime.now() >= datetime.now().replace(hour=hora,minute=minuto,second=0,microsecond=0)
    return ya_es_hora and not estado['resumen_enviado'] and not estado['en_curso']

#Funcion que decide si al cliente le toca tanda ahora
def le_toca(c,estado,grupos):
    ahora = datetime.now()
    if c.dias is not None and ahora.weekday() not in c.dias:
        return False
    #Pasada la hora de inicio arranca la tanda del dia; si el bot cayo a mitad de una tanda (en_curso) la retoma
    sin_empezar = not estado['publicados'] and not estado['fallidos']
    return ahora >= c.inicio_hoy() and bool(pendientes(estado,grupos)) and ((sin_empezar and not estado['abortada']) or estado['en_curso'])

#Funcion para correr una tanda con su turno (manual o programada); devuelve False si hay otra en marcha
def tanda_con_turno(c,limite=None,manual=False):
    if not tomar_turno():
        log.warning(f'[{c.slug}] Hay otra tanda en marcha, se intentara mas tarde')
        return False
    try:
        ejecutar_tanda(c,cargar_estado(c),cargar_grupos(c),limite,manual)
    finally:
        soltar_turno()
    return True

#Funcion para releer los grupos de la cuenta de un cliente (orden "leer_grupos" de la web); devuelve los grupos nuevos
def leer_grupos(c):
    global driver,wait
    if not tomar_turno():
        raise RuntimeError('hay una tanda en marcha')
    driver = run_firefox()
    wait = WebDriverWait(driver,20)
    try:
        logging_fb(c)
        nuevos = obtener_grupos(c)
        nube.subir_grupos(c)
        nube.bajar_grupos(c)
        return nuevos
    finally:
        driver.quit()
        soltar_turno()

#Funcion para ejecutar las ordenes que llegan desde la web (publicar ahora, releer grupos, enviar resumen)
def procesar_ordenes():
    for o in nube.ordenes_pendientes():
        nube.marcar_orden(o['id'],'en_proceso')
        try:
            slug = nube.slug_de(o['cliente_id'])
            if not slug:
                raise RuntimeError('cliente no encontrado en el bot')
            c = Cliente(slug)
            if o['tipo'] == 'publicar_ahora':
                #Publica en los grupos que queden pendientes hoy, sin esperar a la hora de inicio ni al dia de la semana
                if not tanda_con_turno(c,(o.get('parametros') or {}).get('limite'),manual=True):
                    raise RuntimeError('hay otra tanda en marcha')
                e = cargar_estado(c)
                resultado = f'{len(e["publicados"])} publicadas y {len(e["fallidos"])} fallidas hoy; {len(pendientes(e,cargar_grupos(c)))} pendientes'
            elif o['tipo'] == 'leer_grupos':
                resultado = f'{leer_grupos(c)} grupos nuevos'
            elif o['tipo'] == 'enviar_resumen':
                resumen_diario(c,cargar_estado(c),cargar_grupos(c),marcar=False)
                resultado = 'resumen enviado'
            else:
                raise RuntimeError(f'orden desconocida: {o["tipo"]}')
            nube.marcar_orden(o['id'],'hecha',resultado)
        except Exception as e:
            log.error(f'[nube] orden {o["id"]} ({o["tipo"]}): {e}')
            nube.marcar_orden(o['id'],'error',f'{type(e).__name__}: {e}')

def uso():
    print('Uso: python Facebook_bot.py [--nuevo <slug> "<Nombre>" <min> <max> | --grupos <slug> | --ahora <slug> [N] | --resumen <slug> | --sync | --lista]')
    print('Sin argumentos: servicio permanente (tanda diaria de cada cliente activo)')

if __name__ == '__main__':
    configurar_log()
    args = sys.argv[1:]
    try:
        if args and args[0] == '--nuevo':
            #El intervalo entre publicaciones lo decide cada cliente: es obligatorio, no hay valor por defecto
            try:
                slug,nombre,minimo,maximo = args[1],args[2],float(args[3]),float(args[4])
                assert 1 <= minimo <= maximo
            except (IndexError,ValueError,AssertionError):
                print('Falta o es invalido el intervalo entre publicaciones (lo decide el cliente).')
                print('Uso: python Facebook_bot.py --nuevo <slug> "<Nombre>" <min_minutos> <max_minutos>   ej: --nuevo juan "Juan Perez" 10 15')
                sys.exit(1)
            crear_cliente(slug,nombre,minimo,maximo)
        elif args and args[0] == '--resumen' and len(args) >= 2:
            c = Cliente(args[1])
            resumen_diario(c,cargar_estado(c),cargar_grupos(c),marcar=False)
        elif args and args[0] == '--lista':
            for c in cargar_clientes(False):
                e = cargar_estado(c)
                print(f'{c.slug:15} {"ACTIVO " if c.activo else "inactivo"} {c.hora_inicio} grupos={len(cargar_grupos(c))} hoy: {len(e["publicados"])} ok / {len(e["fallidos"])} fallos | cookies={"si" if c.archivo_cookies.is_file() else "NO"}')
        elif args and args[0] == '--grupos' and len(args) >= 2:
            c = Cliente(args[1])
            driver = run_firefox();wait = WebDriverWait(driver,20)
            try:
                logging_fb(c);obtener_grupos(c)
            finally:
                driver.quit()
        elif args and args[0] == '--ahora' and len(args) >= 2:
            limite = int(args[2]) if len(args) > 2 and args[2].isdigit() else None
            tanda_con_turno(Cliente(args[1]),limite,manual=True)
        elif args and args[0] == '--sync':
            print(f'Supabase {"activo" if nube.ACTIVO else "NO configurado"}; clientes bajados: {nube.bajar_todo()}')
        elif args:
            uso()
        else:
            #Servicio permanente: al arrancar se libera un turno que haya quedado colgado por una caida
            soltar_turno()
            log.info('Servicio iniciado' + (' (Supabase activo)' if nube.ACTIVO else ' (solo archivos)'))
            while True:
                try:
                    #Con Supabase: latido, configuracion de la web y ordenes pendientes antes de revisar las tandas
                    if nube.ACTIVO:
                        nube.latido()
                        nube.bajar_todo()
                        procesar_ordenes()
                    #Los clientes se releen en cada vuelta: un cliente nuevo se activa sin reiniciar
                    for c in cargar_clientes():
                        if le_toca(c,cargar_estado(c),cargar_grupos(c)):
                            tanda_con_turno(c)
                        estado = cargar_estado(c)
                        if toca_resumen(c,estado):
                            resumen_diario(c,estado,cargar_grupos(c))
                    time.sleep(60)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    log.exception(f'Error inesperado: {e}')
                    avisar(f'🚨 <b>Bot: error inesperado</b>\n{esc(type(e).__name__)}: {esc(str(e)[:300])}')
                    time.sleep(300)
    except LoginError as e:
        log.error(f'Login: {e}')
        avisar(f'🚨 <b>Error de login</b>\n{esc(e)}')
    except KeyboardInterrupt:
        log.info('Bot detenido')
        soltar_turno()
