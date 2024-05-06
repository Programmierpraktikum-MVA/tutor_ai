from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import os

def scrape_course(driver, courseId):
    driver.get(f"https://isis.tu-berlin.de/course/view.php?id={courseId}")

    wait = WebDriverWait(driver, 10)
    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".section.course-section.main.clearfix")))

    title = driver.find_element(by=By.TAG_NAME, value="h1").text
    print(title)
    folder_path = f"CourseInfos/{title}"

    if not os.path.exists(folder_path):
        # Create the folder
        os.makedirs(folder_path)
        print(f"Folder created: {folder_path}")
    else:
        print(f"Folder already exists: {folder_path}")


    sections = []
    # Extract the 'data-course-id' from each element and print it
    for element in elements:
        section_x = element.get_attribute("id")
        sections.append(section_x)
        print(section_x)

    for i in range(len(sections)):

        target_div = driver.find_element(by=By.CSS_SELECTOR, value=f"li#section-{i} > div > div > a")

        # Get an attribute, for example 'data-example'
        attribute_value = target_div.get_attribute('aria-label')

        print(attribute_value)
    #course_ids = [element.get_attribute("data-course-id") for element in elements]
