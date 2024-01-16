from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from config.config import *
from config.colores import *
import os,pickle,time,sys,random

#Funcion para inicializar el driver Firefox
def run_firefox():  
    #Direccion del driver de Firefox
    path = '/home/rool/.wdm/drivers/geckodriver/linux64/v0.33.0/geckodriver'  
    options = Options()
    options.add_argument('--headless')#No muestra el navegador
    options.add_argument('--disable-extensions')#Desabilita las extenciones del navegador
    options.add_argument('--disable-notifications')#Desabilita las notificaciones
    options.add_argument('--ignore-certificate-errors')#Ignora los certificados de error
    options.add_argument('--no-sandbox')#Ni puta idea
    options.add_argument('--allow-running-insecure-contet')#Abre sin verificar la seguridad de la pagina
    options.add_argument('--no-first-run')#Evitar las tareas de inicializacion
    options.add_argument('--no-proxy-server')#Confirma que no existe un server proxi intermedio
    options.add_argument('--lang=es')#Selecciona el idioma del navegador
    service = Service(executable_path=path)
    driver = webdriver.Firefox(service=service,options=options)
    return driver

#Funcion para realizar una publicacion
def publicar_grupo(url):
    try:
        driver.get(url)
        #Abrimos el contenedor de publicacines
        inbox = wait.until(ec.element_to_be_clickable((By.XPATH,"//span[contains(text(),'Escribe')]")))
        inbox.click()
        #Aqui seleccionamos el color de fondo
        color = wait.until(ec.element_to_be_clickable((By.CSS_SELECTOR,'div[aria-label="Mostrar opciones de fondo"]')))
        color.click()
        select_color = wait.until(ec.element_to_be_clickable((By.CSS_SELECTOR,'div[aria-label="Gradiente, de rojo a azul, fondo"]')))
        select_color.click()
        #Aqui va la publicacion
        inbox = wait.until(ec.element_to_be_clickable((By.CSS_SELECTOR,'div[class="notranslate _5rpu"]')))
        inbox.click()
        #Abrimos el archivo con las publicaciones guardadas de manera aleatoria
        ran = random.randint(1,len(os.listdir('Publicaciones/'))+1)
        with open(f'Publicaciones/publicacion{ran}.txt','r') as f:file=f.readlines()
        inbox.send_keys(file)
        #Clic al boton publicar 
        #publicar = wait.until(ec.element_to_be_clickable((By.CSS_SELECTOR,'div[aria-label="Publicar"]')))  
        #publicar.click()
        return True
    except:
        return False
    
#Funcion para obtener los 20 primeros grupos
def obtener_grupo():
    driver.get(URL_group);atrb = set()
    #Funcion para obtener los 20 primeros urls
    urls = wait.until(ec.visibility_of_all_elements_located((By.CSS_SELECTOR,'a[aria-label="View group"]')))
    #Funcion para saber el total real de grupos
    all_groups = int(wait.until(ec.visibility_of_element_located((By.XPATH,'//span[contains(text(),"Todos los")]'))).text.split()[-1].replace('(','').replace(')',''))
    for url in urls:
        atrb.add(url.get_attribute('href'))
    #Funcion para obtener el resto de los urls
    while len(atrb) < int(all_groups/10)*10:
        #Script para realizar scroll al final de la pagina
        driver.execute_script('window.scrollTo(0, document.body.scrollHeight)')
        try:
            urls = wait.until(ec.visibility_of_all_elements_located((By.CSS_SELECTOR,'a[aria-label="Ver grupo"]')))
            for url in urls:
                atrb.add(url.get_attribute('href'))
        except:
            pass

    input()
    return atrb 

#Funcion para logearse en facebook
def logging():
    if os.path.isfile('config/cookie.cok'):
        print('Realizando loogin por cookies..')
        #Accedemos a la pagina para abrir el archivo txt
        driver.get(URL_robot)
        cookies = pickle.load(open('config/cookie.cok','rb'))
        #Agregamos todas las cookies al navegador
        for cookie in cookies:
            driver.add_cookie(cookie)
        #Accedemos a la pagina y tratamos de clicear algun elemento para cmprobar login
        driver.get(URL_logg)
        try:    
            waitt = WebDriverWait(driver,30)
            waitt.until(ec.visibility_of_element_located((By.CSS_SELECTOR,'input[type="search"]')))
            console_up()
            print(f'{magenta}Login por cookies: {verde}OK{gris}')  
            return 1
        except:
            console_up()
            print(f'{magenta}Login por cookies: {rojo}BAD{gris}')
            os.remove('config/cookie.cok')
    print('Realizando loogin desde cero ...')
    driver.get(URL_logg)
    #Estructura para esperar a que un elemento este disponible en la pagina
    user = wait.until(ec.visibility_of_element_located((By.NAME,'email')))
    user.send_keys(user_)  
    pasw = wait.until(ec.visibility_of_element_located((By.NAME,'pass')))
    pasw.send_keys(pass_)
    bott = wait.until(ec.visibility_of_element_located((By.NAME,'login')))
    bott.click()
    #Confirmamos si se realiza el login correctamente
    try:    
        waitt = WebDriverWait(driver,30)
        waitt.until(ec.visibility_of_element_located((By.CSS_SELECTOR,'input[type="search"]')))
        console_up()
        print(f'{magenta}Login desde cero: {verde}OK{gris}')   
    except:
        console_up()
        print(f'{magenta}Login desde cero: {rojo}BAD{gris}') 
        sys.exit(1)
        return 0
    #Creamos el archivo para guardar las cookies logeads 
    cookie = driver.get_cookies()
    pickle.dump(cookie, open('config/cookie.cok','wb'))
    print(f'{magenta}Se ha creado el archivo cookies{gris}')   

if __name__ == '__main__':
    print(f'{magenta}Iniciando driver ...{gris}')
    #Inicializamos el driver
    driver = run_firefox()
    #Tiempo de espera maximo para encontrar un elemento
    wait = WebDriverWait(driver,20)
    logging()
    #Recogemos en una variable todos los grupos que pertenece el bot
    group = obtener_grupo()
    print(f'{magenta}Se detectaron: {verde}{len(group)} grupos{gris}')
    for url in group:
        #Publicamos de grupo en grupo
        print(f'{magenta}Se esta publicando en el grupo: {verde}{url}{gris}')
        if publicar_grupo(url):
            print(f'{verde}Se publico sin exepciones{gris}')
            time.sleep(60)
        else:
            print(f'{rojo}Se publico con exepciones{gris}')
            

