from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from get_discussion_content import get_discussion_content
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from get_all_discussion_content_from_forum import get_all_discussion_content_from_forum
from selenium.common.exceptions import NoSuchElementException
from get_content_from_forums_of_one_course import get_content_from_forums_of_one_course

def get_content_from_forums_of_all_courses(driver):
    course_dict = []
    
    # Load course data from JSON file
    with open('course_id_saved.json','r') as data:
        course_data = json.load(data)
        
    # Iterate through each course
    for course in course_data:
        try:
            # Retrieve forum content for the current course
            course_forums_content = get_content_from_forums_of_one_course(course, driver)
            course_dict.append(course_forums_content)
        except Exception as e:
            print(f"Failed to retrieve forum content for course {course}: {e}")
    
    # Save results to a new JSON file
    with open('all_courses.json', 'w') as c:
        json.dump(course_dict, c, ensure_ascii=False, indent=4)