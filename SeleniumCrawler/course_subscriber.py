from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
from selenium.webdriver.common.by import By
import get_all_your_course_ids

# Load login data
with open('config.json') as config_file:
    config_data = json.load(config_file)

# Extract username and password from config data
USERNAME_TOKEN = config_data['username']
PASSWORD_TOKEN = config_data['password']

# Initialize webdriver
driver = webdriver.Chrome()
driver.set_window_size(1000, 500)
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

# Get IDs of all registered courses
# get_all_your_course_ids.get_all_course_id()
# with open("../course_id_saved.json", 'r') as file:
#     my_course_ids = json.load(file)

#TODO: Change all_course_ids to the real list of all courses
all_course_ids = ["38647"]
# Navigate to All Courses Page and iteratively log in to all courses, then log out
for course in all_course_ids:
    url = "https://isis.tu-berlin.de/enrol/index.php?id=" + course  # This also opens the course page
    driver.get(url)

    # Scrape
    # TODO: Insert all files responsible for scraping here

    # Unenrol from the course

    # Click the unrenrol button
    unenrol_url = driver.find_element(By.CSS_SELECTOR,
                                         "a[href^='https://isis.tu-berlin.de/enrol/self/unenrolself.php?']").get_attribute("href")
    driver.get(unenrol_url)

    # Click the "Weiter" Button
    weiter_button = driver.find_element(By.XPATH, "//button[text()='Weiter']")
    weiter_button.click()

    # Now you should be logged out.

driver.implicitly_wait(5)
driver.quit()
