import json
import os
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from misc import misce
from paths import ISIS_COURSE_ID_FILE, ensure_json_file

#Input: driver
#Output: json-file with all course ID's


def _extract_course_ids_from_nav_courses(page_source):
    match = re.search(
        r"theme_nephthys/nav_courses.*?amd\\.init\\((\\[.*?\\])\\s*,\\s*\\d+\\s*,\\s*\\d+\\)",
        page_source,
        re.DOTALL,
    )
    if not match:
        return []
    try:
        courses = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    return [str(course["id"]) for course in courses if course.get("id")]


def get_all_course_id(driver):
    override_raw = os.environ.get("ISIS_COURSE_ID")
    if override_raw:
        course_ids = [cid.strip() for cid in override_raw.split(",") if cid.strip()]
        ensure_json_file(ISIS_COURSE_ID_FILE, default=[])
        with open(ISIS_COURSE_ID_FILE, 'w', encoding="utf-8") as file:
            json.dump(course_ids, file)
        return course_ids

    misce.ensure_json_file_exists(ISIS_COURSE_ID_FILE)
    driver.get("https://isis.tu-berlin.de/my/courses.php")

    course_ids = _extract_course_ids_from_nav_courses(driver.page_source)

    if not course_ids:
        wait = WebDriverWait(driver, 10)
        elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".card.dashboard-card")))
        course_ids = [element.get_attribute("data-course-id") for element in elements]

    print(len(course_ids))
    # Saving the course IDs to a JSON file
    with open(ISIS_COURSE_ID_FILE, 'w', encoding="utf-8") as file:
        json.dump(course_ids, file)
    return course_ids
