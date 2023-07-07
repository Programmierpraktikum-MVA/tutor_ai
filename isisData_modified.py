import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver import ActionChains
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.firefox.options import Options

from urllib.request import Request, urlopen
from bs4 import BeautifulSoup

from tkinter import *
from tkinter.ttk import *
from functools import partial

import json

import csv

import concurrent.futures

from time import sleep

PATH = "C:\Program Files (x86)\chromedriver.exe" #path for chromedriver

class ISISWebdriver():
    def __init__(self, url, user_agend):
        self.url = url
        self.ua = user_agend
        self.userName = None
        self.pw = None
        self.isLoggedIn = False
        self.data = {}
        self.foren = None
        self.driver = self.getDriver()

    def getDriver(self):

        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f'----user-agent={self.ua}')
        #chrome_options.add_argument('--headless')

        driver = webdriver.Chrome(executable_path=PATH, options=chrome_options)
        return driver

    def setLogin(self):
        self.userName = self.entry_name.get()
        self.pw = self.entry_pw.get()
        self.master.destroy()

    def setLoginData(self):
        self.master = Tk()
        self.master.geometry("900x400")
        label_front = Label(self.master, text="Geben Sie bitte ihre Isis login Daten ein")
        label_front.config(font=("Courier", 25))
        label_front.pack(pady=30)

        label_name = Label(self.master, text="Username")
        label_name.pack()

        self.entry_name = Entry(self.master)
        self.entry_name.pack()

        label_pw = Label(self.master, text="Password")
        label_pw.pack()

        self.entry_pw = Entry(self.master)
        self.entry_pw.pack()

        button_save = Button(self.master, text="submit", command = self.setLogin)
        button_save.pack()
        mainloop()

    def login(self):
        self.setLoginData()

        try:

            self.driver.get(self.url)
            time.sleep(2)
            tu_login_btn = self.driver.find_element(By.ID,"shibboleth-login-button") #updated String
            #self.driver.execute_script("arguments[0].click();", tu_login_btn)
            tu_login_btn.submit()
            time.sleep(2)

            username = self.driver.find_element(By.NAME,"j_username")
            username.send_keys(self.userName)
            time.sleep(2)
            pwd = self.driver.find_element(By.NAME,"j_password")
            pwd.send_keys(self.pw)
            time.sleep(2)

            submit_login = self.driver.find_element(By.ID,"login-button")
            submit_login.click()

            time.sleep(3)
            if self.driver.current_url == "https://isis.tu-berlin.de/my/":
                self.userName = None
                self.pw = None
                self.isLoggedIn = True

        except:
            self.setLoginData()


    def search_course(self, course):
        #try:
        #    dropdown = Select(self.driver.find_element(By.XPATH,"//a[@data-toggle='dropdown']")) #class name of drop menu
        #    dropdown.select_by_visible_text("Suche")
        #except:
        #    self.driver.quit()

        #search_box = self.driver.find_element(By.XPATH,"//input[@role = 'searchbox']") # name of search box
        try:
            search_box = WebDriverWait(self.driver,10).until(ec.presence_of_element_located((By.XPATH,"//input[@placeholder='Suchen']")))
        except:
            self.driver.quit()
        #search_box = self.driver.find_element()
        time.sleep(1)
        search_box.send_keys(course)
        search_box.send_keys("\n")
        time.sleep(2)
        try:
            search_result = WebDriverWait(self.driver,10).until(ec.presence_of_element_located((By.XPATH,"//a[@class='aalink coursename']")))
        except:
            self.driver.quit()

        search_result.click()

        self.course = {"name":course,"link":self.driver.current_url,"messages":[]}
        #self.courseName = course
       # time.sleep(3)




    def getData(self):
        #time.sleep(2)
        #title = self.driver.find_element_by_class_name("discussionname")
        #title = title.text
        #content = self.driver.find_elements_by_class_name("post-content-container")
        #links = self.driver.find_elements_by_class_name("btn.btn-link")
        #links = self.driver.find_elements_by_link_text("Dauerlink")
        #print(test[0].get_attribute("href"))
        #print(links[0].get_property('attributes')[0])
        messages = []
        counter = 0
        try:
            container = WebDriverWait(self.driver, 3).until(ec.presence_of_all_elements_located((By.CLASS_NAME,"d-flex.body-content-container")))
            #container = self.driver.find_elements(By.CLASS_NAME,"d-flex.body-content-container")
        except:
            return messages



        for content in container:
            text_elem = content.find_element(By.CLASS_NAME,"post-content-container")
            text = text_elem.text
            text = text.replace("\n"," ")

            link_elem = content.find_element(By.LINK_TEXT,"Dauerlink")
            link = link_elem.get_attribute("href")
            if text != "+1":
                messages.append({"text":text,"answers_in_thread":len(container),"tutor_answer_in_thread":"","link": link})
                counter += 1
        #data = {'title': title, 'posts': messages}
        self.driver.back()
        return messages


    def clickLink(self):
        #time.sleep(3)
        #forum = self.course[self.courseName]["forum"]
        counter = 0
        for f in self.foren:
            #link = self.driver.find_element_by_link_text(f["name"])
            """if "IntroProg" in f["name"]:
                self.driver.get(f["link"])
                time.sleep(3)
            else:
                pass"""

            self.driver.get(f["link"])
            #time.sleep(3)

            #liste = self.driver.find_elements(By.CLASS_NAME,"w-100.h-100.d-block")

            #self.course[self.courseName]["forum"][counter]["entry"] = []
            #page_link = self.driver.find_element_by_link_text("Next")

            while True:
                try:
                    liste = WebDriverWait(self.driver, 3).until(ec.presence_of_all_elements_located((By.CLASS_NAME, "w-100.h-100.d-block"))) #find threads in forum
                except:
                    break   # if not try next forum
                for i in range(len(liste)):
                    try:
                        liste = WebDriverWait(self.driver, 10).until(ec.presence_of_all_elements_located((By.CLASS_NAME, "w-100.h-100.d-block"))) # find all messages in thread
                        #liste = self.driver.find_elements(By.CLASS_NAME,"w-100.h-100.d-block")
                        print(i,len(liste))
                        liste[i].click()
                        #self.course[self.courseName]["forum"][counter]["entry"].append(self.getData())
                        self.course["messages"].extend(self.getData())
                        #time.sleep(2)
                    except:
                        continue

                try:
                    next_link = WebDriverWait(self.driver, 3).until(ec.presence_of_element_located((By.CSS_SELECTOR, "[aria-label=Next]"))) # look for next button ?
                    #next_link = self.driver.find_element(By.CSS_SELECTOR,"[aria-label=Next]")
                    next_link.click()
                except:
                    break


            self.driver.back()
            counter += 1

    def getForenFromCourse(self,key):
        try:
            allActivities = WebDriverWait(self.driver, 10).until(ec.presence_of_all_elements_located((By.XPATH, "//a[contains(@class,'aalink stretched-link')]"))) # get all forums
        except:
            self.driver.quit()
        #allActivities = self.driver.find_elements(By.CLASS_NAME," aalink stretched-link")
        self.foren = []

        #self.course[key]["forum"] = []

        for activities in allActivities:
            ac_link = activities.get_attribute('href')

            if "forum" in ac_link: #get only links with forum in it
                #ac_name = activities.find_element_by_class_name("instancename").text
                ac_name = activities.text
                #self.course[key]["forum"].append({"name":ac_name,"link":ac_link})
                self.foren.append({"name":ac_name,"link":ac_link})



if __name__ == "__main__":
    url = "https://www.isis.tu-berlin.de"
    user_agend = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.93 Safari/537.36" # use right version of chrome
    #course = "IntroProg"
    #foren = ["Nachrichtenforum","C-Kurs","Offenes Forum","IntroProg"]

    course = ["Verteilte Systeme SoSe 23"]
    course_name = ["2021_Einfuehrung_Programmierung", "1920_Einfuehrung_Programmierung"]

    #foren = ["C-Kurs", "Offenes Forum", "Häufig gestellte Fragen und technische Fragen zu Hausaufgaben und Vorlesungen im Semester","Nachrichtenforum"]
    crowler = ISISWebdriver(url, user_agend)

    while crowler.isLoggedIn == False:
        crowler.login()

    c = 0
    for course in course:
        crowler.course = None
        crowler.search_course(course)
        crowler.getForenFromCourse(course)
        crowler.clickLink()
        crowl_data = crowler.course

        with open(f'{course[c]}.json', 'w') as outfile:
            json.dump(crowl_data, outfile)
        c += 1

    print("JSON Created ................")
    crowler.driver.quit()
    print("Quiting ................")




