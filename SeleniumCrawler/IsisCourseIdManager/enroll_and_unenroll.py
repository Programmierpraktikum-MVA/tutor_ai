from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
from selenium.webdriver.common.by import By

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

    # Open all your course IDs
    with open('all_your_courses.json') as file:
        my_course_ids = json.load(file)

    # Navigate to All Courses Page and iteratively log in to all courses, then log out
    for course in all_accessible_courses:
        url = "https://isis.tu-berlin.de/enrol/index.php?id=" + course  # This also opens the course page
        driver.get(url)

        # Scrape one page at a time
        # TODO: Insert all files for scraping here

        # Done scraping

        # Check if you are actually enrolled in this course as part of your studies. If yes, don't unenroll.
        if course in my_course_ids:
            print("Not enrolling, since you are enrolled as part of your studies.")
            continue
        else:
            # Click the unenroll button
            unenroll_url = driver.find_element(By.CSS_SELECTOR,
                                               "a[href^='https://isis.tu-berlin.de/enrol/self/unenrolself.php?']").get_attribute(
                "href")
            driver.get(unenroll_url)

            # Click the "Weiter" Button
            weiter_button = driver.find_element(By.XPATH, "//button[text()='Weiter']")
            weiter_button.click()
            print("Unenrolled from course.")

    driver.implicitly_wait(5)
    driver.quit()


if __name__ == '__main__':
    enroll_and_unenroll()
