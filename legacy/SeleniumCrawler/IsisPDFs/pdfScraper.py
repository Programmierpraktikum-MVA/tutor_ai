from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
import json
from store_all_pdfs import store_all_pdfs

# Note that this file is preliminary.
# Eventually, we will run all scraper files with one scraper.py

with open('../config.json') as config_file:
    config_data = json.load(config_file)

# Extract username and password from config data
USERNAME_TOKEN = config_data['username']
PASSWORD_TOKEN = config_data['password']

# Set up Chrome options
chrome_options = Options()

# Configure Chrome to automatically download files
prefs = {"download.default_directory": '/home/tomklein/Documents/uni/tutorAI/tutor_ai/scraping/pdf_data',
         "download.prompt_for_download": False,
         "download.directory_upgrade": True,
         "plugins.always_open_pdf_externally": True}

chrome_options.add_experimental_option("prefs", prefs)

# Run the driver with new download options
driver = webdriver.Chrome(options=chrome_options)



driver.set_window_size(1000,500)

driver.get("https://isis.tu-berlin.de/login/index.php")

title = driver.title

driver.implicitly_wait(0.5)

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

store_all_pdfs(driver)

driver.quit()