from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests
import subprocess
import os
import json


def extract_audio(local_video_path, output_file):
    try:
        ffmpeg_command = f'ffmpeg -i "{local_video_path}" -vn -acodec libmp3lame -y "{output_file}"'
        subprocess.call(ffmpeg_command, shell=True)
        #os.remove(local_video_path)  # Delete the .mp4 file after conversion
    except Exception as e:
        print(f"Error during audio extraction: {e}")


def setup_session_with_cookies(driver):
    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
    return session


def download_and_extract_audio(session, video_url, courseID, index, page_link, processed_urls):
    if video_url in processed_urls:
        print(f"Skipping duplicate video URL: {video_url}")
        return
    processed_urls.add(video_url)
    local_video_path = f'downloaded_videos/{courseID}/{courseID}_{index}.mp4'
    output_file = f'downloaded_videos/{courseID}/{courseID}_{index}.mp3'
    title = f'{courseID}_{index}'
    response = session.get(video_url, stream=True)
    if response.status_code == 200:
        with open(local_video_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        extract_audio(local_video_path, output_file)
        log_entry(title, page_link)
        print(f'Audio extracted and saved as {output_file}')
    else:
        print(f"Failed to download video from {video_url}, Response Code = {response.status_code}")


def log_entry(title, link):
    entry = {"Title": title, "Link": link}
    try:
        with open('download_log.json', 'r+') as log_file:
            log_data = json.load(log_file)
            log_data.append(entry)
            log_file.seek(0)
            json.dump(log_data, log_file, indent=4)
    except FileNotFoundError:
        with open('download_log.json', 'w') as log_file:
            json.dump([entry], log_file, indent=4)


def scrape_and_extract_audio(driver, courseId):
    folder_path = f"downloaded_videos/{courseId}"
    if not os.path.exists(folder_path):
        # Create the folder
        os.makedirs(folder_path)
        print(f"Folder created: {folder_path}")
    else:
        print(f"Folder already exists: {folder_path}")

    driver.get(f"https://isis.tu-berlin.de/mod/videoservice/view.php/course/{courseId}/browse")
    processed_urls = set()
    session = setup_session_with_cookies(driver)
    links = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.thumbnail-container a')))
    hrefs = [link.get_attribute('href') for link in links]
    i = 0
    for href in hrefs:
        driver.get(href)
        try:
            video_element = driver.find_element(by=By.TAG_NAME, value="video")
            video_source_url = video_element.get_attribute('src')
            if video_source_url:
                download_and_extract_audio(session, video_source_url, courseId, i ,href, processed_urls)
                i = i +1
        except TimeoutException:
            print(f"Timeout or element not found on page {href}.")

