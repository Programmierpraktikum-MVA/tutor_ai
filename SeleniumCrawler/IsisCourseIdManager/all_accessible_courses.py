from selenium import webdriver
from selenium.webdriver.common.by import By
import json
import get_all_existing_course_ids

import time


def get_all_accessible_course(driver):
    with open("all_course_ids.json") as f:
        data = json.load(f)

    all_course_ids = data["course_ids"]  # creates a list of course IDs

    all_accessible_course_ids = []  # creates a list of accessible course IDs

    # demo list for testing purposes, delete later
    # all_course_ids = ["39279", "39308",
    #                   "39259", "39062"]  # [0] is in english, [1] is in german, [2] in german, [3] needs a password

    for course_id in all_course_ids:
        url = "https://isis.tu-berlin.de/course/view.php?id=" + course_id
        driver.get(url)

        # Try-catch block for finding an enrolment form
        try:
            element = driver.find_element(By.CLASS_NAME, "form-control-static")  # Every non-password protected course
        except:
            print("password protected")
            continue

        all_accessible_course_ids.append(id)
        print("enrolling successfully")


# Helper function to log in, can be deleted later
def log_in():
    # Load login data
    with open('config.json') as config_file:
        config_data = json.load(config_file)

    # Extract username and password from config data
    USERNAME_TOKEN = config_data['username']
    PASSWORD_TOKEN = config_data['password']

    # Initialize webdriver
    driver = webdriver.Chrome()
    driver.set_window_size(1000, 1000)
    driver.get("https://isis.tu-berlin.de/login/index.php")
    title = driver.title
    driver.implicitly_wait(0.5)

    # Log in to ISIS with your credentials
    tu_login_button = driver.find_element(by=By.ID, value="shibbolethbutton")

    tu_login_button.click()

    title_new = driver.title
    print(title_new)
    username_login = driver.find_element(by=By.ID, value="username")
    password_login = driver.find_element(by=By.ID, value="password")

    username_login.send_keys(USERNAME_TOKEN)
    password_login.send_keys(PASSWORD_TOKEN)

    final_login_button = driver.find_element(by=By.ID, value="login-button")
    final_login_button.click()

    title_second = driver.title

    return driver


if __name__ == '__main__':
    driver = log_in()
    get_all_accessible_course(driver)
