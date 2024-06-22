from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from misc import misce
import requests
import subprocess
import os
import json
from transcribe import transcribe_audio
import time
import multiprocessing
import queue



KEEP_DOWNLOADED_VIDEOS = False

#gets mp3 from mp4 file
def extract_audio(local_video_path, output_file):
    try:
        ffmpeg_command = f'ffmpeg -i "{local_video_path}" -vn -acodec libmp3lame -y "{output_file}"'
        subprocess.call(ffmpeg_command, shell=True)
    except Exception as e:
        print(f"Error during audio extraction: {e}")

#cookies needed to access the videos for whatsoever reason
def setup_session_with_cookies(driver):
    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie['domain'])
    return session

#downloads the video
def download_video(session, video_url, local_video_path, title, href):
    response = session.get(video_url, stream=True)
    if response.status_code == 200:
        with open(local_video_path, 'wb') as f:
            for chunk in response.iter_content(1024):
                f.write(chunk)
        log_entry(title, video_url, href)
    else:
        print(f"Failed to download video from {video_url}, Response Code = {response.status_code}")


def log_entry(title, link, href):
    entry = {"Title": title, "Link": link, "Website": href}
    try:
        with open('download_log.json', 'r+') as log_file:
            log_data = json.load(log_file)
            log_data.append(entry)
            log_file.seek(0)
            json.dump(log_data, log_file, indent=4)
    except FileNotFoundError:
        with open('download_log.json', 'w') as log_file:
            json.dump([entry], log_file, indent=4)


def scrape_and_extract_transcript(driver, courseId, queue):
    misce.ensure_json_file_exists("download_log.json")
    folder_path = f"downloaded_videos/{courseId}"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Folder created: {folder_path}")
    else:
        print(f"Folder already exists: {folder_path}")

    driver.get(f"https://isis.tu-berlin.de/mod/videoservice/view.php/course/{courseId}/browse")
    processed_urls = set()
    session = setup_session_with_cookies(driver)
    links = []
    try:
        links = WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.thumbnail-container a')))
    except TimeoutException:
        print("No thumbnail-container found")
    hrefs = [link.get_attribute('href') for link in links]
    i = 0
    for href in hrefs:
        driver.get(href)
        time.sleep(3)
        try:
            video_element = driver.find_element(by=By.TAG_NAME, value="video")
            video_source_url = video_element.get_attribute('src')
            if video_source_url:
                if not misce.url_exists("download_log.json", video_source_url):
                    if video_source_url not in processed_urls:
                        processed_urls.add(video_source_url)
                        title = f'{courseId}_{i}_course_video'
                        path = f'{folder_path}/{title}'
                        local_video_path = f'{path}.mp4'
                        download_video(session, video_source_url, local_video_path, title, href)
                        queue.put(local_video_path)
                i = i + 1
        except (NoSuchElementException, TimeoutException):
            print(f"Timeout or element not found on page {href}.")


