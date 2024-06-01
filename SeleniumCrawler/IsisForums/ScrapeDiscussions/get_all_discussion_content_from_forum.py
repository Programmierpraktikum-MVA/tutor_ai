from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from get_discussion_content import get_discussion_content
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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

    discussion_urls = [(discussion.get_attribute("href"), discussion.get_attribute("title")) for discussion in discussions]

    for discussion_url, discussion_name in discussion_urls:
        try:
            if discussion_name is None:
                discussion_name = "No title available"
            discussion_id = discussion_url[-6:]

            # Rufe die Seite der Diskussion auf, um deren Inhalt zu extrahieren
            driver.get(discussion_url)
            messages = get_discussion_content(discussion_id, driver)

            # Gehe zurück zur Forenseite und warte, bis sie vollständig geladen ist
            driver.get(actual_url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[class='w-100 h-100 d-block']")))

            discussions_dict.append({
                "Discussion_Name": discussion_name,
                "Discussion_Id": discussion_id,
                "Messages": messages
            })
            
        
        except Exception as e:
            print(f"Fehler beim Verarbeiten der Diskussion: {e}")
    return discussions_dict   

    """with open('forum.json', 'w') as f:
        json.dump(discussions_dict, f, ensure_ascii=False, indent=4)"""



