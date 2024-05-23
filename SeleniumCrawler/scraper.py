from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from IsisModules import get_all_course_id, scrape_course, scrape_all_course_videos
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def relogin(driver):
    logout(driver)
    time.sleep(1)
    login(driver)


def login(driver):

    with open('config.json') as config_file:
        config_data = json.load(config_file)

    # Extract username and password from config data
    USERNAME_TOKEN = config_data['username']
    PASSWORD_TOKEN = config_data['password']

    print('Logging in...')

    driver.get("https://isis.tu-berlin.de/login/index.php")

    tu_login_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "shibbolethbutton"))
    )
    tu_login_button.click()

    username_login = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "username"))
    )
    password_login = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "password"))
    )

    username_login.send_keys(USERNAME_TOKEN)
    password_login.send_keys(PASSWORD_TOKEN)

    final_login_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "login-button"))
    )
    final_login_button.click()

def logout(driver):
    driver.set_page_load_timeout(5)
    tu_logout_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.LINK_TEXT, "Logout"))
    )
    tu_logout_button.click()


def main():


    driver = webdriver.Chrome()

    login(driver)

    get_all_course_id.get_all_course_id(driver)



    with open('course_id_saved.json', 'r') as file:
        course_ids = json.load(file)

    for course_id in course_ids:
        scrape_course.scrape_course(driver, course_id)
        scrape_all_course_videos.scrape_and_extract_audio(driver, course_id)
        relogin(driver)

    driver.quit()


if __name__ == "__main__":
    main()