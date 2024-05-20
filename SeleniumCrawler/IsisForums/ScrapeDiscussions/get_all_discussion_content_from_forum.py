from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from get_discussion_content import get_discussion_content


def get_all_discussion_content_from_forum(forum_id, driver):
    base_url = "https://isis.tu-berlin.de/mod/forum/view.php?id="
    actual_url = base_url + str(forum_id)
    driver.get(actual_url)
    discussions_dict = []

    # Überprüfe, ob Diskussionselemente gefunden wurden
    discussions = driver.find_elements(By.CSS_SELECTOR, "a[class='w-100 h-100 d-block']")
    if not discussions:
        print("Keine Diskussionen gefunden.")
        return
    
    for discussion in discussions:
        try:
            discussion_name = discussion.get_attribute("title")
            if discussion_name is None:
                discussion_name = "No title available"
            discussion_id = discussion.get_attribute("href")[-6:]
            messages = get_discussion_content(discussion_id, driver)
            discussions_dict.append({
                "Discussion_Name": discussion_name,
                "Discussion_Id": discussion_id,
                "Messages": messages
            })
        except Exception as e:
            print(f"Fehler beim Verarbeiten der Diskussion: {e}")
    
    with open('forum.json', 'w') as f:
        json.dump(discussions_dict, f, ensure_ascii=False, indent=4)
