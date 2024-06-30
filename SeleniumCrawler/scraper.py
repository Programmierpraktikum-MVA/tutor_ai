from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from IsisModules import get_all_course_id, scrape_course, scrape_all_course_videos
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import ChromiumOptions
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
import os
import queue



def ensure_folder_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Folder '{folder_path}' created.")
    else:
        print(f"Folder '{folder_path}' already exists.")

def relogin(driver, username, password):
    logout(driver)
    time.sleep(3)
    login(driver, username, password)


def login(driver, username, password):
    time.sleep(2)

    print('Logging in...')

    driver.get("https://isis.tu-berlin.de/login/index.php")

    tu_login_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "shibbolethbutton"))
    )
    tu_login_button.click()

    try:
        username_login = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
    except TimeoutException:
        driver.get("https://isis.tu-berlin.de/login/index.php")
        username_login = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

    password_login = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "password"))
    )

    username_login.send_keys(username)
    password_login.send_keys(password)

    final_login_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "login-button"))
    )
    final_login_button.click()

def logout(driver):
    driver.set_page_load_timeout(5)
    try:
        tu_logout_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Logout"))
        )
        tu_logout_button.click()
    except TimeoutException:
        try:
            second_tu_logout_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.LINK_TEXT, "Logout"))
            )
            second_tu_logout_button.click()
            driver.get("https://isis.tu-berlin.de/login/index.php")
        except TimeoutException:
            driver.get("https://isis.tu-berlin.de/login/index.php")
            time.sleep(2)
            driver.get("https://isis.tu-berlin.de/login/index.php")

        print("Logout button not found")

def start_crawl_single_course(queue, username, password, course_id):
    print("1")

    options = ChromiumOptions()

    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)


    print("2")
    login(driver, username, password)
    print("4")
    ensure_folder_exists('downloaded_videos')
    print("5")

    scrape_course.scrape_course(driver, course_id)
    scrape_all_course_videos.scrape_and_extract_transcript(driver, course_id, queue)
    while not queue.empty():
        continue
    driver.quit()

def start_single_crawl_but_all_courses(queue, username, password):

    print("1")

    options = ChromiumOptions()

    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)


    print("2")
    login(driver, username, password)
    print("3")
    get_all_course_id.get_all_course_id(driver)

    with open('course_id_saved.json', 'r') as file:
        course_ids = json.load(file)
    print("6")

    for course_id in course_ids:
        try:
            start_crawl_single_course(queue, username, password, course_id)
        except (TimeoutException, WebDriverException) as e:
            print(f"An error occurred: {e}")




def start_crawl(queue, username, password):
    print("1")

    options = ChromiumOptions()

    options.add_argument("--headless=new")
    driver = webdriver.Chrome(options=options)


    print("2")
    login(driver, username, password)
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
        while not queue.empty():
            continue
        relogin(driver, username, password)
    queue.put("end.txt")
    driver.quit()

def main():
    username = input("Enter your username: ")
    password = input("Enter your password: ")
    video_queue = queue.Queue()
    start_crawl(video_queue, username, password)

if __name__ == "__main__":
    main()