from selenium.webdriver.common.by import By
import json


def get_all_forum_id(driver):
    base_url = "https://isis.tu-berlin.de/course/view.php?id="

    # Open the course ID JSON file
    with open("../../course_id_saved.json", 'r') as f:
        course_id_data = json.load(f)

    # Create a dictionary for all forum IDs
    forum_id_dict = []

    # Iterate over each entry in the course ID database
    for course_id in course_id_data:
        course_url = base_url + course_id
        driver.get(course_url)

        # CSS Selector for all forum links
        links = driver.find_elements(By.CSS_SELECTOR, "a[href^='https://isis.tu-berlin.de/mod/forum/view']")

        # Create a list for all forum IDs
        forum_ids = []

        # Iterate over each link
        for link in links:
            link_url = link.get_attribute("href")
            print(link_url)

            # Extract the forum ID from the link
            forum_id = link_url[-7:]

            # Add the ID to the forum list
            forum_ids.append(forum_id)

            # Add the list to the course list
            forum_id_dict.append({
                "course_id": course_id,
                "forum_ids": forum_ids
            })

    forum_file = "forum_id_saved.json"

    # Save the forum ID JSON file
    with open(forum_file, 'w') as f:
        json.dump(forum_id_dict, f)
