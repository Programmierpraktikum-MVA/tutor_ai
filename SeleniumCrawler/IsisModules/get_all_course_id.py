from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json

#Input: driver
#Output: json-file with all course ID's
def get_all_course_id(driver):
    driver.get("https://isis.tu-berlin.de/my/courses.php")

    wait = WebDriverWait(driver, 10)
    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card.dashboard-card")))

    # Extract the 'data-course-id' from each element and print it
    for element in elements:
        course_id = element.get_attribute("data-course-id")
        print(course_id)

    course_ids = [element.get_attribute("data-course-id") for element in elements]

    # Saving the course IDs to a JSON file
    with open("../course_id_saved.json", 'w') as file:
        json.dump(course_ids, file)
