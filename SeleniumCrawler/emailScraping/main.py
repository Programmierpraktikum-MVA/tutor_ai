import time
import json

import selenium
import undetected_chromedriver as uc
from selenium.webdriver.chrome import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import pickle


# Funktion zum Speichern der E-Mails in JSON-Dateien
def save_emails_to_json(emails, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(emails, f, ensure_ascii=False, indent=4)


# Selenium WebDriver konfigurieren
options = Options()
options.add_argument("--start-maximized")
driver = uc.Chrome()


#pickle.dump(driver.get_cookies(), open("cookies.pkl", "wb"))

try:
    # Gmail Login
    driver.get("https://mail.google.com/")
    cookies = pickle.load(open("cookies.pkl", "rb"))
    time.sleep(2)

    # Eingabe der E-Mail-Adresse
    email_input = driver.find_element(By.ID, "identifierId")
    email_input.send_keys("AdaStruct@gmail.com")
    email_input.send_keys(Keys.ENTER)
    time.sleep(5)

    # Eingabe des Passworts
    password_input = driver.find_element(By.NAME, "Passwd")
    password_input.send_keys("dfjefiu3t9TIOFK)R")
    password_input.send_keys(Keys.ENTER)
    time.sleep(3)

    # Warten, bis Gmail geladen ist
    time.sleep(60)

    # E-Mails abrufen
    emails = []
    email_elements = driver.find_elements(By.CSS_SELECTOR, "tr.zA")

    for email_element in email_elements:
        email = {}
        email['subject'] = email_element.find_element(By.CSS_SELECTOR, "span.bog").text

        # E-Mail öffnen
        email_element.click()
        time.sleep(2)  # Warten, bis die E-Mail vollständig geladen ist

        sender_element = driver.find_element(By.CLASS_NAME, "gD")
        email['sender'] = sender_element.get_attribute('data-hovercard-id')

        # E-Mail-Inhalt extrahieren
        try:
            for i in range(1, 4 + 1):
                for j in range(1, 4 + 1):
                    email_body_element = driver.find_element(By.CSS_SELECTOR, "body > table > tbody > tr:nth-child({i}) > td > table > tbody > tr:nth-child({j}) > td > table > tbody > tr:nth-child(1) > td")
                    email_body = email_body_element.text
                    email['body'] = email_body
        except:
            email_body_element = driver.find_element(By.CSS_SELECTOR, "div.a3s")
            email_body = email_body_element.text

        email['body'] = email_body
        # Öffnen des Dropdown-Menüs
        #dropdown_button = driver.find_element(By.ID, ":4s")
        #dropdown_button.click()
        #time.sleep(2)  # Warten, bis das Dropdown-Menü geöffnet ist

        # Zusätzliche E-Mail-Informationen extrahieren
        #email_details = driver.find_element(By.XPATH, '//*[@id=":5n"]/div[1]/div[2]/div[2]')
        #email_text = email_details.text

        # Informationen parsen
        #lines = email_text.split('\n')
        #for line in lines:
        #    if line.startswith("from:"):
        #        email['from'] = line[len("from:"):].strip()
        #    elif line.startswith("to:"):
        #        email['to'] = line[len("to:"):].strip()
        #    elif line.startswith("date:"):
        #        email['date'] = line[len("date:"):].strip()

        # E-Mail-Empfänger extrahieren
        recipients_elements = driver.find_elements(By.CSS_SELECTOR, "span.g2")
        recipients = [element.get_attribute('email') for element in recipients_elements if
                      element.get_attribute('email')]
        email['recipients'] = recipients
        date_element = driver.find_element(By.CSS_SELECTOR, "span.g3")
        email['date'] = date_element.get_attribute('alt')

        #email_from = driver.find_element(By.CSS_SELECTOR, "#\:5n > div.adn.ads > div.gs > div.ajA.SK > div > table > tbody > tr.UszGxc.ajv > td.gL > span > span > span.go").text
        #email['from'] = email_from
        #email_to = driver.find_element(By.CSS_SELECTOR,"#\:5n > div.adn.ads > div.gs > div.ajA.SK > div > table > tbody > tr:nth-child(3) > td.gL > span > span").text
        #email['to'] = email_to
        #email_date = driver.find_element(By.CSS_SELECTOR,"#\:5n > div.adn.ads > div.gs > div.ajA.SK > div > table > tbody > tr:nth-child(4) > td.gL > span").text
        #email['date'] = email_date

        # Zurück zum Posteingang
        driver.find_element(By.CSS_SELECTOR, "#\:4 > div:nth-child(2) > div.iH.bzn > div > div:nth-child(1) > div > div").click()
        time.sleep(5)  # Warten, bis der Posteingang vollständig geladen ist

        emails.append(email)

    # E-Mails in JSON speichern
    save_emails_to_json(emails, "emails.json")
    # for cookie in cookies:
    #     driver.add_cookie(cookie)

finally:
    # WebDriver schließen
    driver.quit()