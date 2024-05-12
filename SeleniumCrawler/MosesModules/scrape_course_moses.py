from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os
import re

from bs4 import BeautifulSoup
from bs4.element import NavigableString


def get_html_text(html_input):
    soup = BeautifulSoup(html_input, 'lxml')
    texts = []
    for element in soup.descendants:
        if isinstance(element, NavigableString) and element.parent.name not in ['script', 'style']:
            text = element.strip()
            if text:
                texts.append(text)
    return texts

def sanitize_filename(filename):
    # Remove invalid characters from the filename
    sanitized = re.sub(r'[\\/*?:"<>|]', "", filename)
    # Replace reserved words and trim excessive whitespace
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    # Avoid names like CON, PRN, AUX, NUL etc on Windows
    sanitized = re.sub(r'^(CON|PRN|AUX|NUL|COM\d|LPT\d)(\..+)?$', '_reserved_', sanitized, flags=re.I)
    return sanitized

def scrape_course(driver, course_id, version_text):
    #Get Course ISIS Site
    driver.get(f"https://moseskonto.tu-berlin.de/moses/modultransfersystem/bolognamodule/beschreibung/anzeigen.html?nummer={course_id}&version={version_text}&sprache=1")

    #Wait for everything to be loaded and get all all sections
    wait = WebDriverWait(driver, 10)
    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, '#j_idt47')))
    #for element in elements:
    #        print(element.text)

    #Get course Title, e.g. AlgoDat
    title = driver.find_element(by=By.TAG_NAME, value='h1').text
    title = sanitize_filename(title)
    #print(title)
    folder_path = f"CourseInfosMoses/{title}"

    #create folder for the course
    if not os.path.exists(folder_path):
        # Create the folder
        os.makedirs(folder_path)
        print(f"Folder created: {folder_path}")
    else:
        print(f"Folder already exists: {folder_path}")

    #number of sections
    sections_count = len(driver.find_elements(By.XPATH, '//*[@id="j_idt47"]/div'))
    print(f"Sections count: {sections_count}")

    #get the title of every section
    for i in range(2, sections_count+1):
        #1st section(div) skipped as it only describes the language of the page
        #finds the section div wanted
        section_name_div = driver.find_element(by=By.XPATH, value=f'//*[@id="j_idt47"]/div[{i}]')
        #gets the htmlText out of that section
        htmlText = section_name_div.get_attribute("outerHTML")
        #gets just the text out of htmlText
        htmlTextInfos = get_html_text(htmlText)

        #saves the htmlTextInfos in json files named after its sectors
        if i == 2: sectionName = "Modul"
        else:
            sectionName = driver.find_element(by=By.XPATH, value=f'//*[@id="j_idt47"]/div[{i}]/div/div/div/div[1]/h3').text
            sectionName = sanitize_filename(sectionName)
        with open(f"CourseInfosMoses/{title}/{sectionName}.json", 'w', encoding="utf-8") as f:
            json.dump(htmlTextInfos, f, ensure_ascii=False, indent=4)

        #print(attribute_value)
    Box = ["BoxBestandteile", "BoxVerwendbarkeit"]
    print(len(Box))
    for i in range(0, len(Box)):
        #finds the section div wanted
        section_name_div = driver.find_element(by=By.XPATH, value=f'//*[@id="j_idt47:{Box[i]}"]')
        #gets the htmlText out of that section
        htmlText = section_name_div.get_attribute("outerHTML")
        #gets just the text out of htmlText
        htmlTextInfos = get_html_text(htmlText)
        sectionName = driver.find_element(by=By.XPATH,
                                          value=f'//*[@id="j_idt47:{Box[i]}"]/div/div/div/div[1]/div/h3').text
        sectionName = sanitize_filename(sectionName)
        with open(f"CourseInfosMoses/{title}/{sectionName}.json", 'w', encoding="utf-8") as f:
            json.dump(htmlTextInfos, f, ensure_ascii=False, indent=4)

