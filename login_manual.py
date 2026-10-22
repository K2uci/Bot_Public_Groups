#Login manual de un cliente: abre Edge con ventana, el cliente inicia sesion y resuelve el reto, y se guardan sus cookies
#Uso (en tu PC): python login_manual.py <slug_cliente>
import os,sys
from Facebook_bot import *
import Facebook_bot as bot

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Uso: python login_manual.py <slug_cliente>   (ver clientes con: python Facebook_bot.py --lista)')
        sys.exit(1)
    configurar_log()
    c = Cliente(sys.argv[1])
    #En tu PC se usa Edge (Selenium Manager descarga msedgedriver solo)
    bot.driver = webdriver.Edge()
    bot.wait = WebDriverWait(bot.driver,20)
    try:
        bot.driver.get(URL_logg)
        print(f'\n>>> Cliente: {c.nombre}. En la ventana de Edge: inicia sesion y resuelve el reto/verificacion.')
        print('>>> Tienes 10 minutos. No cierres la ventana, el script avisa cuando termine.\n')
        fin = time.time() + 600
        while time.time() < fin:
            try:
                if bot.driver.find_elements(By.CSS_SELECTOR,'input[type="search"]'):
                    break
            except Exception:
                pass
            time.sleep(3)
        else:
            print('Se acabo el tiempo sin detectar sesion iniciada.')
            sys.exit(1)
        c.archivo_cookies.write_text(json.dumps(bot.driver.get_cookies()),encoding='utf-8')
        print(f'Sesion detectada. Cookies guardadas en {c.archivo_cookies}')
        #Aprovechamos la sesion para leer los grupos de la cuenta
        try:
            print(f'Grupos guardados en grupos.txt: {obtener_grupos(c)}')
        except Exception as e:
            print(f'No se pudieron leer los grupos ({type(e).__name__}); se puede repetir luego con --grupos {c.slug}')
    finally:
        bot.driver.quit()
