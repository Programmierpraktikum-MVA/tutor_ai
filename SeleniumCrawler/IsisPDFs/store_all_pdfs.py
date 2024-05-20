import json
import os
import glob
import time

from selenium.webdriver.common.by import By


def store_all_pdfs(driver):
    # TODO: Change the directory path
    pdf_data_path = '/home/tomklein/Documents/uni/tutorAI/tutor_ai/scraping/pdf_data'

    # Create the directory if it does not yet exist
    os.makedirs(pdf_data_path, exist_ok=True)

    base_url = "https://isis.tu-berlin.de/course/view.php?id="

    with open("../../course_id_saved.json", 'r') as f:
        course_id_data = json.load(f)

    # Iterate over each entry in the course ID database
    for course_id in course_id_data:
        # Create a folder for the course
        course_path = pdf_data_path + '/' + course_id
        print(course_path)
        os.makedirs(course_path, exist_ok=True)

        course_url = base_url + course_id

        tabs = driver.window_handles
        driver.switch_to.window(tabs[0])

        print(len(tabs))
        driver.get(course_url)

        # Select only the activity grids with the pdf icon included

        activity_grids_with_pdf = driver.find_elements(by=By.CSS_SELECTOR, value=".activity-grid:has(["
                                                                                 "src='https://isis.tu-berlin.de/theme"
                                                                                 "/image.php/nephthys/core/1713890017"
                                                                                 "/f/pdf?filtericon=1'])")

        print("we found that many activity grids with pdfs: " + str(len(activity_grids_with_pdf)))
        # Create empty list of urls
        pdf_ids = []

        # Create a list for tabs
        tabs = driver.window_handles

        # Extract the pdf_id from the activity grid
        for grid in activity_grids_with_pdf:
            driver.switch_to.window(tabs[0])
            url_elem = grid.find_element(By.CSS_SELECTOR, "a[href^='https://isis.tu-berlin.de/mod']")
            url = url_elem.get_attribute("href")
            pdf_id = url[-7:]
            pdf_ids.append(pdf_id)

            # Switch to next tab
            driver.execute_script("window.open('about:blank', '_blank');")
            tabs = driver.window_handles
            driver.switch_to.window(tabs[1])

            # Click the download link
            driver.get(url)
            driver.close()

        # Wait for the downloading process to finish
        print("Waiting for downloads", end="")
        while any([filename.endswith(".crdownload") for filename in
                   os.listdir(pdf_data_path)]):
            print("\n we have to sleep\n")
            time.sleep(2)
            print(".", end="")

        # Move all the pdfs to the right folder
        pdf_files = glob.glob(os.path.join(pdf_data_path, '*.pdf'))
        print("we found that many pdf files: " + str(len(pdf_files)))

        for pdf_file in pdf_files:
            # Extract pdf file name
            file_name = os.path.basename(pdf_file)

            destination_path = os.path.join(course_path, file_name)
            os.rename(pdf_file, destination_path)
bs

