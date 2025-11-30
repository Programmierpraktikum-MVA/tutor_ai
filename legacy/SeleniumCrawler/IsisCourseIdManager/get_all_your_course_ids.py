from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json


def get_all_course_id(driver):
    """Retrieves all course IDs from the user's ISIS TU Berlin dashboard.

    Args:
        driver: A Selenium WebDriver instance, authenticated and logged into ISIS.

    Returns:
        A list of course IDs (strings) extracted from the dashboard.
    """
    driver.get("https://isis.tu-berlin.de/my/courses.php")

    wait = WebDriverWait(driver, 10)
    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card.dashboard-card")))

    # Extract the 'data-course-id' from each element and print it
    for element in elements:
        course_id = element.get_attribute("data-course-id")

    course_ids = [element.get_attribute("data-course-id") for element in elements]


    # Saving the course IDs to a JSON file
    with open("my_course_ids.json", 'w') as file:
        json.dump(course_ids, file)

