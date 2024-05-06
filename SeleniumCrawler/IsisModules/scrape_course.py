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

def scrape_course(driver, courseId):
    #Get Course ISIS Site
    driver.get(f"https://isis.tu-berlin.de/course/view.php?id={courseId}")

    #Wait for everything to be loaded and get all all sections
    wait = WebDriverWait(driver, 10)
    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".section.course-section.main.clearfix")))

    #Get course Title, e.g. AlgoDat
    title = driver.find_element(by=By.TAG_NAME, value="h1").text
    title = sanitize_filename(title)
    #print(title)
    folder_path = f"CourseInfos/{title}"

    #create folder for the course
    if not os.path.exists(folder_path):
        # Create the folder
        os.makedirs(folder_path)
        print(f"Folder created: {folder_path}")
    else:
        print(f"Folder already exists: {folder_path}")


    sections = []
    # Extract the 'id' from each element, that is the section number
    for element in elements:
        section_x = element.get_attribute("id")
        sections.append(section_x)
        #print(section_x)

    #get the title of every section
    for i in range(len(sections)):

        #finds the section div wanted
        section_name_div = driver.find_element(by=By.CSS_SELECTOR, value=f"li#section-{i} > div > div > a")
        target_div = driver.find_element(by=By.CSS_SELECTOR, value=f"li#section-{i}")
        #gets the htmlText out of that section
        htmlText = target_div.get_attribute("outerHTML")
        #gets just the text out of htmlText
        htmlTextInfos = get_html_text(htmlText)

        #saves the htmlTextInfos in json files named after its sectors
        sectionName = section_name_div.get_attribute('aria-label')
        sectionName = sanitize_filename(sectionName)
        with open(f"CourseInfos/{title}/{sectionName}.json", 'w', encoding="utf-8") as f:
            json.dump(htmlTextInfos, f, ensure_ascii=False, indent=4)

        #print(attribute_value)

