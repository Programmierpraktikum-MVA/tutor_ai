from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import get_all_course_id

import get_all_course_id

with open('config.json') as config_file:
    config_data = json.load(config_file)

# Extract username and password from config data
USERNAME_TOKEN = config_data['username']
PASSWORD_TOKEN = config_data['password']

driver = webdriver.Chrome()

# Make the browser run in full screen mode
driver.maximize_window()

driver.get("https://isis.tu-berlin.de/")



title = driver.title

driver.implicitly_wait(0.5)

tu_login_button = driver.find_element(by=By.ID, value="shibboleth-login-button")
tu_login_button.click()

title_new = driver.title
print(title_new)
username_login = driver.find_element(by=By.ID, value="username")
password_login = driver.find_element(by=By.ID, value="password")

username_login.send_keys(USERNAME_TOKEN)
password_login.send_keys(PASSWORD_TOKEN)

final_login_button = driver.find_element(by=By.ID, value="login-button")
final_login_button.click()

title_second =driver.title
print(title_second)

driver.get("https://isis.tu-berlin.de/my/courses.php")

third =driver.title
print(third)

get_all_course_id.get_all_course_id(driver)


driver.quit()
