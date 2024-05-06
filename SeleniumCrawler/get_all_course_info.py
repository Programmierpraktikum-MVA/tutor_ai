from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json


def get_all_course_info(driver):
    driver.get("https://isis.tu-berlin.de/my/courses.php")

    wait = WebDriverWait(driver, 10)
    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card.dashboard-card")))
    # Create a list to store the data
    data = []

    for element in elements:

        course_id = element.find_element(By.XPATH, ".//span[@data-course-id]").get_attribute("data-course-id")
        print(course_id)

        name = element.find_element(By.XPATH, ".//span[@class='sr-only']").text
        print(name)

        link = element.find_element(By.XPATH, ".//a").get_attribute("href")
        print(link)

        # Add the data to the list
        data.append({"course_id": course_id, "course_name": name, "course_link": link})

    # Save the data to a JSON file
    with open("course_info.json", "w") as file:
        json.dump(data, file, indent=4)


    driver.quit()