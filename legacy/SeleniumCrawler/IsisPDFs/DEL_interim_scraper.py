from selenium import webdriver
from selenium.webdriver.common.by import By
import json
import DEL_get_all_course_id as d

with open('../config.json') as config_file:
    config_data = json.load(config_file)

# Extract username and password from config data
USERNAME_TOKEN = config_data['username']
PASSWORD_TOKEN = config_data['password']

driver = webdriver.Chrome()

driver.get("https://isis.tu-berlin.de/login/index.php")

title = driver.title

driver.implicitly_wait(0.5)

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

title_second =driver.title
print(title_second)

driver.get("https://isis.tu-berlin.de/my/courses.php")

third =driver.title
print(third)

course_ids = d.get_all_course_id(driver)

driver.quit()