from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
from selenium.webdriver.common.by import By
import get_all_your_course_ids

""" Enrolls in all accessible ISIS courses, scrapes them. If you were not enrolled in this course originally, 
it unenrolls you automatically.CAUTION: Keep your all_your_courses.json file up-to-date. 

CAUTION: Incorrect information in this file can lead to unintentional unenrollment from courses you're actually taking.

Scraping: The function currently has a placeholder for scraping course data. Simply insert the functions for scraping."""


def enroll_and_unenroll():
    # Load login data
    with open('../config.json') as config_file:
        config_data = json.load(config_file)

    # Extract username and password from config data
    USERNAME_TOKEN = config_data['username']
    PASSWORD_TOKEN = config_data['password']

    # Initialize webdriver
    driver = webdriver.Chrome()
    driver.set_window_size(1000, 500)
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

    # Open all accessible course IDs
    with open('all_accessible_courses.json') as file:
        all_accessible_courses = json.load(file)

    # Get all your courses
    # get_all_your_course_ids.get_all_course_id(driver) # TODO: uncomment
    # Open all your course IDs
    with open('my_course_ids.json') as file:
        my_course_ids = json.load(file)

    # Navigate to All Courses Page and iteratively log in to all courses, then log out

    # TODO: Delete test lists
    all_accessible_courses = ["39318", "39313", "39312", "39311"]
    my_course_ids = []

    # Boolean for checking if course is part of your Course IDs
    course_is_in_my_course_ids = False

    for course in all_accessible_courses:
        url = f"https://isis.tu-berlin.de/course/view.php?id={course}"
        driver.get(url)

        if course in my_course_ids:
            print(f"course {course} is in my course list.")
            course_is_in_my_course_ids = True

        if not course_is_in_my_course_ids:
            try:
                # Enroll in this course
                print("ENROLLING NOW.")
                enroll_button = driver.find_element(By.ID, value = "id_submitbutton")
                enroll_button.click()
            except:
                print("Enrolling not possible. Skip this course.")
                continue


        # Scrape one page at a time
        try:
            # TODO: Insert all files for scraping here
            print("scraping now")
        except:
            print("scraping not possible for this course")
        # Done scraping

        # Check if you are actually enrolled in this course as part of your studies. If yes, don't unenroll.
        if course_is_in_my_course_ids:
            print(f"Not unenrolling, since you are enrolled in course {course} as part of your studies.")
        else:
            # Click the unenroll button
            unenroll_url = driver.find_element(By.CSS_SELECTOR,
                                               "a[href^='https://isis.tu-berlin.de/enrol/self/unenrolself.php?']").get_attribute(
                "href")
            driver.get(unenroll_url)

            # Click the "Weiter" Button
            weiter_button = driver.find_element(By.XPATH, "//button[text()='Weiter']")
            weiter_button.click()
            print(f"Unenrolled from course {course}.")

        # Reset boolean for next iteration
        course_is_in_my_course_ids = False

    driver.implicitly_wait(5)
    driver.quit()


if __name__ == '__main__':
    enroll_and_unenroll()
