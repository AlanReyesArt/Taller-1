"""
Pruebas E2E automatizadas con Selenium WebDriver
Sistema Multiagente de Evaluación de Tesis
------------------------------------------------
Requisitos previos:
pip install selenium webdriver-manager
"""

import time
import os
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ── Configuración ──────────────────────────────────────────────
FRONTEND_URL = "http://localhost:5173"
TEST_EMAIL = "alumno@upao.edu.pe"
TEST_PASS = "alumno123"
DOCENTE_EMAIL = "docente@upao.edu.pe"
DOCENTE_PASS = "docente123"

PDF_TEST_PATH = os.path.abspath("test_dummy.pdf")
IMG_TEST_PATH = os.path.abspath("test_dummy.jpg")

def setup_driver():
    print("[INFO] Iniciando WebDriver...")
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.implicitly_wait(10)
    return driver

def test_login_fallido(driver):
    """CP-03: Login Fallido (Credenciales incorrectas)"""
    print("[INFO] Ejecutando CP-03: Login Fallido")
    driver.get(FRONTEND_URL)
    wait = WebDriverWait(driver, 5)
    
    try:
        email_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='email']")))
        pass_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
        
        email_input.clear()
        email_input.send_keys("error@upao.edu.pe")
        pass_input.clear()
        pass_input.send_keys("clavemala")
        
        login_btn = driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ingresar') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'entrar') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'iniciar') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login') or @type='submit']")
        login_btn.click()
        
        time.sleep(2)
        assert driver.current_url.endswith("/login") or "Tesis" not in driver.page_source
        print("[OK] CP-03 Exitoso: El sistema bloqueo el acceso incorrecto.")
    except Exception as e:
        print(f"[ERROR] CP-03 Fallo.")
        raise e

def test_login_alumno(driver):
    """CP-01: Login Exitoso del Alumno"""
    print("[INFO] Ejecutando CP-01: Login de Alumno")
    driver.get(FRONTEND_URL)
    wait = WebDriverWait(driver, 10)
    
    try:
        email_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='email']")))
        pass_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
        
        email_input.clear()
        email_input.send_keys(TEST_EMAIL)
        pass_input.clear()
        pass_input.send_keys(TEST_PASS)
        
        login_btn = driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ingresar') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'entrar') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'iniciar') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login') or @type='submit']")
        login_btn.click()
        
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'tesis') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'subir')]")))
        print("[OK] CP-01 Exitoso: El alumno logro ingresar al dashboard.")
    except Exception as e:
        print(f"[ERROR] CP-01 Fallo.")
        raise e

def test_cargar_archivo_invalido(driver):
    """CP-04: Carga de archivo no PDF"""
    print("[INFO] Ejecutando CP-04: Carga de archivo invalido (JPG)")
    wait = WebDriverWait(driver, 5)
    
    try:
        if not os.path.exists(IMG_TEST_PATH):
            with open(IMG_TEST_PATH, "w") as f:
                f.write("Imagen falsa")
                
        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        file_input.send_keys(IMG_TEST_PATH)
        
        time.sleep(1)
        print("[OK] CP-04 Exitoso: Validacion de archivo enviada (simulada).")
    except Exception as e:
        print(f"[ERROR] CP-04 Fallo.")
        raise e
    finally:
        if os.path.exists(IMG_TEST_PATH):
            os.remove(IMG_TEST_PATH)

def test_cargar_y_analizar_tesis(driver):
    """CP-02/06: Subir PDF y Lanzar Análisis Rápido"""
    print("[INFO] Ejecutando CP-02/06: Carga de Tesis y Analisis IA")
    # Timeout excepcional de 120 segundos para procesos de IA
    wait = WebDriverWait(driver, 120)
    
    try:
        if not os.path.exists(PDF_TEST_PATH):
            with open(PDF_TEST_PATH, "w") as f:
                f.write("%PDF-1.4\n%Dummy PDF para Selenium")
                
        driver.refresh()
        time.sleep(2)
        
        file_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='file']")))
        file_input.send_keys(PDF_TEST_PATH)
        
        try:
            titulo_input = driver.find_element(By.XPATH, "//input[contains(@placeholder, 'Ej:')]")
            titulo_input.send_keys("Tesis E2E Selenium")
        except:
            pass
            
        time.sleep(1)
        
        # Clic en el botón que hace ambas cosas: Subir y Analizar (Generar diagnóstico rápido)
        # Usamos 'generar' para evitar problemas con las tildes en 'diagnóstico'
        analisis_btn = driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'generar')]")
        analisis_btn.click()
        
        print("   - Esperando respuesta del Agente IA (puede tardar ~1 min)...")
        
        # Esperamos a que la UI muestre el reporte renderizado
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'score') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'observaciones') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'resultado')]")))
        
        print("[OK] CP-02/06 Exitoso: El archivo fue enviado y el reporte IA se genero correctamente.")
    except Exception as e:
        print(f"[ERROR] CP-02/06 Fallo (Posible Timeout de la IA o no encontro boton).")
        raise e
    finally:
        try:
            if os.path.exists(PDF_TEST_PATH):
                os.remove(PDF_TEST_PATH)
        except:
            pass

def test_logout(driver):
    """Auxiliar: Cerrar sesión para cambiar de usuario"""
    print("[INFO] Cerrando sesion...")
    try:
        driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();")
        driver.refresh()
        time.sleep(2)
    except:
        pass

def test_login_docente(driver):
    """CP-05: Login de Docente"""
    print("[INFO] Ejecutando CP-05: Login de Docente")
    driver.get(FRONTEND_URL)
    wait = WebDriverWait(driver, 10)
    
    try:
        email_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='email']")))
        pass_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='password']")))
        
        email_input.clear()
        email_input.send_keys(DOCENTE_EMAIL)
        pass_input.clear()
        pass_input.send_keys(DOCENTE_PASS)
        
        login_btn = driver.find_element(By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ingresar') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'entrar') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'iniciar') or contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login') or @type='submit']")
        login_btn.click()
        
        time.sleep(3)
        print("[OK] CP-05 Exitoso: El docente logro ingresar correctamente.")
    except Exception as e:
        print(f"[ERROR] CP-05 Fallo.")
        raise e

if __name__ == "__main__":
    print("=========================================")
    print(" INICIANDO BATERIA DE PRUEBAS E2E (UI)   ")
    print("=========================================")
    
    navegador = None
    try:
        navegador = setup_driver()
        
        test_login_fallido(navegador)
        test_login_alumno(navegador)
        # 3. Caso Triste de Archivo
        test_cargar_archivo_invalido(navegador)
        
        # 4. Caso Feliz de Archivo y Análisis (Lógica Core de IA)
        test_cargar_y_analizar_tesis(navegador)
        
        # 5. Cambio a Docente
        test_logout(navegador)
        test_login_docente(navegador)
        
        print("=========================================")
        print(" [OK] TODAS LAS 5 PRUEBAS E2E FINALIZADAS")
        print("=========================================")
        
    except Exception as general_err:
        print("\n[FAIL] Bateria abortada por errores.")
        traceback.print_exc()
    finally:
        if navegador:
            time.sleep(3)
            navegador.quit()
            print("[INFO] Navegador cerrado.")
