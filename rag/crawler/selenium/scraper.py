from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from IsisModules import get_all_course_id, scrape_course, scrape_all_course_videos, scrape_course_resources
from IsisForums.ScrapeDiscussions.get_content_from_forums_of_all_courses import (
    get_content_from_forums_of_all_courses,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import ChromiumOptions
from selenium.common.exceptions import TimeoutException, WebDriverException, StaleElementReferenceException
import time
import queue

from paths import ISIS_COURSE_ID_FILE, ISIS_FILES_DIR, ISIS_VIDEOS_DIR, ensure_dir



def ensure_folder_exists(folder_path):
    ensure_dir(folder_path)
    print(f"Folder ready: {folder_path}")


def build_driver(download_dir):
    ensure_dir(download_dir)
    options = ChromiumOptions()
    options.add_argument("--headless=new")
    prefs = {
        "download.default_directory": str(download_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(options=options)
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": str(download_dir)},
        )
    except Exception:
        pass
    return driver

def relogin(driver, username, password):
    try:
        logout(driver)
        time.sleep(3)
    except Exception as exc:
        print(f"Logout failed, continuing with fresh login: {exc}")
    login(driver, username, password)


def login(driver, username, password):
    time.sleep(2)

    print('Logging in...')

    driver.get("https://isis.tu-berlin.de/login/index.php")

    def click_with_retry(locator, retries=3):
        for attempt in range(retries):
            try:
                WebDriverWait(driver, 10).until(EC.element_to_be_clickable(locator)).click()
                return
            except StaleElementReferenceException:
                if attempt == retries - 1:
                    raise
                time.sleep(0.5)

    def send_keys_with_retry(locator, value, retries=3):
        for attempt in range(retries):
            try:
                element = WebDriverWait(driver, 10).until(EC.visibility_of_element_located(locator))
                element.clear()
                element.send_keys(value)
                return
            except StaleElementReferenceException:
                if attempt == retries - 1:
                    raise
                time.sleep(0.5)

    click_with_retry((By.ID, "shibbolethbutton"))

    try:
        send_keys_with_retry((By.ID, "username"), username)
        send_keys_with_retry((By.ID, "password"), password)
    except TimeoutException:
        driver.get("https://isis.tu-berlin.de/login/index.php")
        click_with_retry((By.ID, "shibbolethbutton"))
        send_keys_with_retry((By.ID, "username"), username)
        send_keys_with_retry((By.ID, "password"), password)

    click_with_retry((By.ID, "login-button"))

def logout(driver):
    driver.set_page_load_timeout(5)
    try:
        tu_logout_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.LINK_TEXT, "Logout"))
        )
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tu_logout_button)
            driver.execute_script("arguments[0].click();", tu_logout_button)
            return
        except Exception:
            try:
                tu_logout_button.click()
                return
            except Exception:
                pass
    except TimeoutException:
        pass
    except Exception:
        pass

    # Fallback: at least land on login page so the session can be re-authenticated.
    try:
        driver.get("https://isis.tu-berlin.de/login/index.php")
    except Exception:
        pass

def start_crawl_single_course(queue, username, password, course_id):
    print("1")
    download_dir = ISIS_FILES_DIR / "_downloads"
    driver = build_driver(download_dir)

    print("2")
    login(driver, username, password)
    print("4")
    ensure_folder_exists(ISIS_VIDEOS_DIR)
    print("5")

    scrape_course.scrape_course(driver, course_id)
    scrape_course_resources.scrape_course_resources(driver, course_id)
    scrape_all_course_videos.scrape_and_extract_transcript(driver, course_id, queue)
    if not queue.empty():
        print("Waiting for transcription queue to drain...")
    while not queue.empty():
        time.sleep(1)
    driver.quit()

def start_single_crawl_but_all_courses(queue, username, password):
    start_crawl(queue, username, password)




def start_crawl(queue, username, password):
    print("1")
    download_dir = ISIS_FILES_DIR / "_downloads"
    driver = build_driver(download_dir)

    print("2")
    login(driver, username, password)
    print("3")
    get_all_course_id.get_all_course_id(driver)
    print("4")
    ensure_folder_exists(ISIS_VIDEOS_DIR)
    print("5")
    try:
        get_content_from_forums_of_all_courses(driver)
    except Exception as exc:
        print(f"Forum scraping failed: {exc}")


    with open(ISIS_COURSE_ID_FILE, 'r', encoding="utf-8") as file:
        course_ids = json.load(file)
    print("6")

    for course_id in course_ids:
        scrape_course.scrape_course(driver, course_id)
        scrape_course_resources.scrape_course_resources(driver, course_id)
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
