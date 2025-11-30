from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from get_discussion_content import get_discussion_content
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from get_all_discussion_content_from_forum import get_all_discussion_content_from_forum
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException


def get_content_from_forums_of_one_course(course_id, driver):
    base_url = "https://isis.tu-berlin.de/course/view.php?id="
    actual_url = base_url + str(course_id)
    driver.get(actual_url)
    course_dict = []

    try:
        course_name = driver.find_element(By.CSS_SELECTOR, "div.page-header-headings > h1.h2").text
        #print(course_name)
    except NoSuchElementException:
        course_name = "No title found"

    forums_dict = []

    # Sammle alle Forum-URLs und -Namen
    forums = driver.find_elements(By.CSS_SELECTOR, "a[href^='https://isis.tu-berlin.de/mod/forum/view'].aalink.stretched-link")
    #for forum in forums:
        #print(forum.get_attribute("href"))
    
    forum_info = [{"name": forum.text, "url": forum.get_attribute("href")} for forum in forums]

    for info in forum_info:
        try:
            forum_id = info["url"][-7:]
              # Lade die Forum-Seite neu, um sicherzustellen, dass das Element aktuell ist
            forum = get_all_discussion_content_from_forum(forum_id, driver)
            forums_dict.append(forum)
            
        except StaleElementReferenceException:
            print(f"Stale element reference exception encountered for forum URL: {info['url']}. Skipping...")

    course_dict.append({
                "Course_Name": course_name,
                "Course_id": course_id,
                "Forums": forums_dict
            })
    return course_dict
""" with open('courses.json', 'w') as c:
    json.dump(course_dict, c, ensure_ascii=False, indent=4)"""
