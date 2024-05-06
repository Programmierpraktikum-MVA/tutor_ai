from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from IsisModules import get_all_course_id, scrape_course

with open('config.json') as config_file:
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

get_all_course_id.get_all_course_id(driver)

with open('course_id_saved.json', 'r') as file:
    course_ids = json.load(file)

for course_id in course_ids:
    scrape_course.scrape_course(driver, course_id)


driver.quit()