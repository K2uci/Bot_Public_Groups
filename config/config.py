from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

#Cargamos las variables del archivo .env (sin dependencias externas)
def _cargar_env():
    env = BASE_DIR / '.env'
    if not env.is_file():
        return
    for linea in env.read_text(encoding='utf-8').splitlines():
        linea = linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:
            continue
        clave, valor = linea.split('=', 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))
_cargar_env()

#Url para cargar las cookies (pagina ligera del dominio)
URL_robot = 'https://www.facebook.com/robots.txt'
URL_logg = 'https://www.facebook.com/'

#Telegram: un solo bot; TG_CHAT_ID es el chat del administrador (recibe todos los avisos y resumenes)
TG_TOKEN = os.environ.get('TG_TOKEN', '')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID', '')
ARCHIVO_CHAT = BASE_DIR / 'config' / 'tg_chat.txt'

#Valores por defecto de cada cliente (se pueden cambiar en clientes/<cliente>/cliente.json)
HORA_INICIO = os.environ.get('HORA_INICIO', '10:00')
#Espera aleatoria entre una publicacion y la siguiente (en minutos)
ESPERA_MIN = float(os.environ.get('ESPERA_MIN', '8'))
ESPERA_MAX = float(os.environ.get('ESPERA_MAX', '10'))
#Si fallan estas publicaciones seguidas se aborta la tanda (posible bloqueo o cambio de Facebook)
MAX_FALLOS_SEGUIDOS = int(os.environ.get('MAX_FALLOS_SEGUIDOS', '3'))
#Navegador sin ventana (en el VPS siempre True)
HEADLESS = os.environ.get('HEADLESS', '1') == '1'
#Ruta opcional de geckodriver; si se deja vacia Selenium lo descarga solo
GECKODRIVER_PATH = os.environ.get('GECKODRIVER_PATH', '')

#Rutas del proyecto
DIR_CLIENTES = BASE_DIR / 'clientes'
DIR_LOGS = BASE_DIR / 'logs'
#Solo una tanda a la vez: el VPS no aguanta dos navegadores
ARCHIVO_LOCK = BASE_DIR / 'config' / 'tanda.lock'
EXT_IMAGEN = {'.jpg', '.jpeg', '.png', '.webp'}
