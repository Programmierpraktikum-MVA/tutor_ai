from selenium import webdriver
from selenium.webdriver.common.by import By
import json
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException


def get_discussion_content(discussion_id, driver):
    base_url = "https://isis.tu-berlin.de/mod/forum/discuss.php?d="
    actual_url = base_url + str(discussion_id)
    messages_dict = []
    driver.get(actual_url)
    article_list = driver.find_elements(By.CSS_SELECTOR, "article.forum-post-container.mb-2")
    
    for article in article_list:
        try:
            response_link=article.find_element(By.CSS_SELECTOR, "a[title='Dauerhafter Link zum Ursprungsbeitrag dieses Beitrags']")
            answer_to=response_link.get_attribute("href")[-8:]
        except NoSuchElementException:
            answer_to="Response to nothing"
            
        if answer_to==article.get_attribute("id"):
            answer_to="This is the original post"
        messages_dict.append({
            "Message_id": article.get_attribute("id"),
            "Author": article.find_element(By.CSS_SELECTOR, "div.mb-3[tabindex='-1'] a").text,
            "DateTime": article.find_element(By.CSS_SELECTOR, "div.mb-3[tabindex='-1'] time").get_attribute("datetime"),
            "Content": article.find_element(By.CSS_SELECTOR, "div.post-content-container").text.replace('\n', ' '),
            "Response to":answer_to
        })
    return messages_dict
    """with open('discussion.json', 'w') as d:
        json.dump(messages_dict, d, ensure_ascii=False, indent=4)"""
