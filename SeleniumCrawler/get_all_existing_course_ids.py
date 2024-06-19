from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json

import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import re

def open_all_course_page(driver):
    # Give the driver enough time to load the full page
    # driver.implicitly_wait(300)

    # Load the page with all courses
    driver.get("https://isis.tu-berlin.de/course/search.php?excludearchived=1&perpage=all")

    # Get the html_content
    html_content = driver.page_source

    # download the html content
    with open("all_courses.html", "w", encoding="utf-8") as f:
        f.write(html_content)


def scrape_all_course_html():
    with open("all_courses.html", "r") as f:
        all_courses = f.read()

    # Now use Beautiful Soup
    soup = BeautifulSoup(all_courses, "html.parser")

    print("parsing the file ya sahbi")
    # target_links = [link['href'] for link in soup.find_all("a", href=True)
    #                 if link['href'].startswith("https://isis.tu-berlin.de/course/view.php?id=")]

    html_text = soup.get_text()  # Convert soup to text
    link_pattern = re.compile(r"https://isis\.tu-berlin\.de/course/view\.php\?id=\d+")
    target_links = link_pattern.findall(html_text)

    link_count = len(target_links)
    print(f"Target link size is: {link_count}")

    # Extract course IDs
    course_ids = []
    for link in target_links:
        parsed_url = urlparse(link)
        query_params = parse_qs(parsed_url.query)
        course_ids.append(query_params['id'][0])

    data = {"course_ids": course_ids}

    with open("course_ids.json", "w") as json_file:
        json.dump(data, json_file, indent=4)


    # # Click "alles aufklappen"
    # unfold_all = driver.find_element(By.CSS_SELECTOR, ".collapseexpand")
    # unfold_all.click()
    #
    # h3_buttons = driver.find_elements(By.CSS_SELECTOR, "h3.categoryname.aabtn")
    # print(len(h3_buttons))
    #
    # for h3_button in h3_buttons:
    #     h3_button.click()
    #     h4_buttons = driver.find_elements(By.CSS_SELECTOR, "h4.categoryname.aabtn")
    #     print(len(h4_buttons))


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


if __name__ == '__main__':
    print("lets go")
    scrape_all_course_html()
