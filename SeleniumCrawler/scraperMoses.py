from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from MosesModules import get_course_id_moses, scrape_course_moses

with open('config.json') as config_file:
    config_data = json.load(config_file)

# Extract username and password from config data
USERNAME_TOKEN = config_data['username']
PASSWORD_TOKEN = config_data['password']

driver = webdriver.Chrome()

driver.get("https://moseskonto.tu-berlin.de/moses/index.html")

title = driver.title

driver.implicitly_wait(0.5)

tu_login_button = driver.find_element(by=By.CLASS_NAME, value="nav-top-user")
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

driver.get("https://moseskonto.tu-berlin.de/moses/modultransfersystem/bolognamodule/suchen.html?text=&modulversionGueltigkeitSemester=72")

third =driver.title
print(third)

get_course_id_moses.get_all_course_id(driver)

with open('../course_id_saved_moses.json', 'r') as file:
    course_ids = json.load(file)

for course_id, version_text in course_ids:
    scrape_course_moses.scrape_course(driver, course_id, version_text)


driver.quit()