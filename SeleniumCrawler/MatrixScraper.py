import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# URL der Webseite
url = "https://chat.tu-berlin.de/#/login"

# Benutzername und Passwort
username = "matrixnutzername"
password = "matrixpassword"

# Erstelle eine Instanz des Chrome Webdrivers
options = Options()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
wait = WebDriverWait(driver, 10)

# Gehe zur Webseite
driver.get(url)
driver.implicitly_wait(3)

# Finde die Eingabefelder für Benutzername und Passwort sowie den Anmelde-Button
username_field = driver.find_element(By.ID, "mx_LoginForm_username")
password_field = driver.find_element(By.ID, "mx_LoginForm_password")

# Fülle die Eingabefelder aus und klicke auf den Anmelde-Button
username_field.send_keys(username)
password_field.send_keys(password)
password_field.send_keys(Keys.ENTER)

# Warte bis die Anmeldung abgeschlossen ist (hier könntest du eine längere Wartezeit einfügen, wenn nötig)
driver.implicitly_wait(10)  # Warte maximal 10 Sekunden, falls Elemente geladen werden müssen

# Finde den Button über die Klasse
verify = wait.until(EC.element_to_be_clickable(
    (By.XPATH, "//div[@class='mx_AccessibleButton mx_AccessibleButton_hasKind mx_AccessibleButton_kind_primary']")))
verify.click()
driver.implicitly_wait(10)

dialog = wait.until(
    EC.element_to_be_clickable((By.XPATH, "//div[@class='mx_AccessibleButton mx_Dialog_cancelButton']")))
dialog.click()
driver.implicitly_wait(10)

#@aria-label bei Bedarf ändern um gewollten Chatroom zu crawlen
chatroom = wait.until(
    EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Programmierpraktikum – MVA' and @role='treeitem']")))
chatroom.click()
driver.implicitly_wait(2)

threads_button = wait.until(EC.element_to_be_clickable((By.XPATH,
                                                        '//*[@id="matrixchat"]/div[1]/div[2]/div[3]/div/div/div/header/div/div[7]')))
threads_button.click()
driver.implicitly_wait(10)

# Erstelle ein Verzeichnis für die Threads, falls es noch nicht existiert
threads_dir = chatroom.get_attribute("aria-label") + ' threads_data'
if not os.path.exists(threads_dir):
    os.makedirs(threads_dir)

# Anzahl der Threads bestimmen
thread_count = len(wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR,
                                                                   "#mx_RightPanel > div > div.mx_AutoHideScrollbar.mx_ScrollPanel.mx_RoomView_messagePanel > div > ol > li"))))

# Iteriere über jedes Thread-Element
for idx in range(1, thread_count+1):
    # Selektor für den aktuellen Thread
    thread_selector = f"#mx_RightPanel > div > div.mx_AutoHideScrollbar.mx_ScrollPanel.mx_RoomView_messagePanel > div > ol > li:nth-child({idx})"

    # Klicke auf das Thread-Element, um es zu öffnen
    thread = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, thread_selector)))
    thread.click()

    # Warte bis der Thread-Inhalt geladen ist (hier ein Beispiel für einen Inhalt mit Klasse mx_EventTile_body)
    message_count = len(wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#mx_RightPanel > div > div.mx_ThreadView_timelinePanelWrapper > div > div > ol > li"))))
    thread_data = []
    previous_sender = ""
    for message_idx in range(2, message_count+1):
        message_selector = f"#mx_RightPanel > div > div.mx_ThreadView_timelinePanelWrapper > div > div > ol > li:nth-child({message_idx})"

        try:
            sender_selector = message_selector + " > div.mx_EventTile_senderDetails > div.mx_DisambiguatedProfile > span"
            sender_element = driver.find_element(By.CSS_SELECTOR, sender_selector)
            sender = sender_element.text
            previous_sender = sender
        except Exception as e:
            print(f"Sender konnte nicht gefunden werden für Nachricht {message_idx} im Thread {idx}: {e}")
            sender = previous_sender

        try:
            body_selector = message_selector + " > div.mx_EventTile_line > div.mx_MTextBody.mx_EventTile_content > span"
            body_element = driver.find_element(By.CSS_SELECTOR, body_selector)
            body = body_element.text
        except Exception as e:
            print(f"Nachrichtentext konnte nicht gefunden werden für Nachricht {message_idx} im Thread {idx}: {e}")
            body = "Keine Nachricht"

        message_data = {
            "Sender": sender,
            "Message": body
        }
        thread_data.append(message_data)

    # Erstelle einen eindeutigen Identifier für den Thread (hier nutzen wir den Index)
    thread_id = f"thread_{idx}"

    # Speichere den Thread-Inhalt als JSON-Datei im Verzeichnis threads_data
    file_path = os.path.join(threads_dir, f"{thread_id}.json")
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(thread_data, f, ensure_ascii=False, indent=4)

    # Gehe zurück zur Liste der Threads
    back_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//div[@class='mx_AccessibleButton mx_BaseCard_back']")))
    back_button.click()
    driver.implicitly_wait(2)

# Schließe den Webdriver
driver.quit()

print("Konversationen wurden als separate JSON-Dateien in den Ordner 'threads_data' gespeichert.")
