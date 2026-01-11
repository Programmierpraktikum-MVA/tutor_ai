from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from paths import MOSES_COURSE_ID_FILE, ensure_json_file


def get_all_course_id(driver):
    driver.get(
        "https://moseskonto.tu-berlin.de/moses/modultransfersystem/bolognamodule/suchen.html?text=&modulversionGueltigkeitSemester=72")

    wait = WebDriverWait(driver, 10)
    elements = driver.find_elements(By.XPATH, '//a[contains(@title, "Modul anzeigen")]')
    versions = driver.find_elements(By.XPATH, '//small')
    # Extract the 'data-course-id' from each element and print it
    kursids = []
    versionen = []
    course_data = []
    for element in elements:
        if element.text == "":
            continue
        else:
            kursids.append(element.text)
            #print(element.text)

    for version in versions:
        if version.text == "":
            continue
        else:
            versionen.append(version.text.strip('()'))
            #print(version.text)
    versionen.pop(0)
    for kursid, vers in zip(kursids, versionen):
            course_data.append((kursid, vers))
            #print(kursid, vers)

    # Saving the course IDs to a JSON file
    ensure_json_file(MOSES_COURSE_ID_FILE, default=[])
    with open(MOSES_COURSE_ID_FILE, 'w', encoding="utf-8") as file:
        json.dump(course_data, file)
