from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from get_discussion_content import get_discussion_content
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from get_all_discussion_content_from_forum import get_all_discussion_content_from_forum
from selenium.common.exceptions import NoSuchElementException
from get_content_from_forums_of_one_course import get_content_from_forums_of_one_course
from paths import ISIS_COURSE_ID_FILE, ISIS_FORUM_DATA_DIR, ensure_dir, ensure_json_file

def get_content_from_forums_of_all_courses(driver):
    #course_dict = []
    
    # Load course data from JSON file
    ensure_json_file(ISIS_COURSE_ID_FILE, default=[])
    with open(ISIS_COURSE_ID_FILE, 'r', encoding="utf-8") as data:
        course_data = json.load(data)
    ensure_dir(ISIS_FORUM_DATA_DIR)
        
    # Iterate through each course
    for course in course_data:
        try:
            file_name = "course_"+course
            
            # Retrieve forum content for the current course
            course_forums_content = get_content_from_forums_of_one_course(course, driver)
            #course_dict.append(course_forums_content)
            output_path = ISIS_FORUM_DATA_DIR / f"{file_name}.json"
            with open(output_path, 'w', encoding="utf-8") as c:
                json.dump(course_forums_content, c, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"Failed to retrieve forum content for course {course}: {e}")
    
   
