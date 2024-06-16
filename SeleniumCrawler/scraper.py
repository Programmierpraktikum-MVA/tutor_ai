from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from IsisModules import get_all_course_id, scrape_course, scrape_all_course_videos
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import queue

def ensure_folder_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Folder '{folder_path}' created.")
    else:
        print(f"Folder '{folder_path}' already exists.")

def relogin(driver):
    logout(driver)
    time.sleep(3)
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



def start_crawl(queue):
    print("1")
    driver = webdriver.Chrome()
    print("2")
    login(driver)
    print("3")
    get_all_course_id.get_all_course_id(driver)
    print("4")
    ensure_folder_exists('downloaded_videos')
    print("5")


    with open('course_id_saved.json', 'r') as file:
        course_ids = json.load(file)
    print("6")

    for course_id in course_ids:
        scrape_course.scrape_course(driver, course_id)
        scrape_all_course_videos.scrape_and_extract_transcript(driver, course_id, queue)
        relogin()
    queue.put("end.txt")
    driver.quit()

def main():
    video_queue = queue.Queue()
    start_crawl(video_queue)

if __name__ == "__main__":
    main()