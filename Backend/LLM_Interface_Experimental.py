from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import numpy as np
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.common.exceptions import StaleElementReferenceException

import pinecone
import scraper as scp


from sentence_transformers import SentenceTransformer,util 

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import fake_useragent

from pyvis.network import Network

def plot_entities_and_relations(entities, relations):
    # Create an empty graph
    graph = Network(height="500px", width="100%", notebook=True)

    # Create a set to store nodes with relations
    nodes_with_relations = set()

    # Add relations as edges to the graph and collect nodes with relations
    for relation in relations:
        entity1, rel, entity2 = relation
        nodes_with_relations.add(entity1)
        nodes_with_relations.add(entity2)

    # Add nodes with relations to the graph
    for node in nodes_with_relations:
        graph.add_node(node)

    # Add relations as edges to the graph with relation tags
    for relation in relations:
        entity1, rel, entity2 = relation
        if entity1 in nodes_with_relations and entity2 in nodes_with_relations:
            graph.add_edge(entity1, entity2, title=rel, label=rel)

    # Show the graph
    graph.show("graph.html")


def parse_input_string(input_data_str):
    # Clean the input string
    input_data_str = input_data_str.replace("\n", "").replace("\r", "").replace("\t", "")

    # Extract entities
    entities_start = input_data_str.index('"entities": [') + len('"entities": [')
    entities_end = input_data_str.index(']', entities_start)
    entities = [entity.strip().strip('"') for entity in input_data_str[entities_start:entities_end].split(",")]

    # Extract relations
    relations_start = input_data_str.index('"relations": [') + len('"relations": [')
    relations_end = input_data_str.rindex(']')
    relations_str = input_data_str[relations_start:relations_end]
    relation_items = [item.strip().strip('()') for item in relations_str.split("),")]
    relations = [tuple(item.split(",")) for item in relation_items]

    # Return the extracted entities and relations
    return entities, relations


#########################################################################
URL = 'https://chat.corsin.io/chat/'

prompt = 'extract the 10 relevant entities and the relations of the following text. store the entities in an array colled "entities" and store the relations in an array called "relations" dont do anything else and only give me the two arrays as a response dont give me anything else. Relations are always between two entities. Relations and Entities are not longer than two words. please keep the names for the relations short. the format is {"entities": ["A", "B", "C"], "relations": [(A,relation,B), (B,relation,C)]}. here is the text:'



# Generate a fake user agent
def load_LLM(URL):
    user_agent = fake_useragent.UserAgent().random

    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument(f'user-agent={user_agent}')
    # chrome_options.add_argument('--headless')  # Run in headless mode

    # Set up webdriver
    driver = webdriver.Chrome(options=chrome_options)

    # Open URL
    driver.get(URL)
    time.sleep(2)
    return driver

def user_message(prompt,prompt_template,driver):
    text_area = driver.find_element("id", "message-input")
    text_area.send_keys(prompt + prompt_template)
    button = driver.find_element(By.CSS_SELECTOR, "i.fa-regular.fa-paper-plane-top")
    button.click()



def GPT_response(laenge,driver,printer):
    # Wait for the response to load
    previous_length = 0
    zero_counter = 0
    leng = 0
    while zero_counter<10:
        try:
            response_divs = driver.find_elements(By.XPATH, '//div[contains(@class, "content") and starts-with(@id, "gpt")]')
            leng = len(response_divs)
            # print(leng)
            
            # print(leng)
            # if len(response_divs)>1:
                # print(zero_counter)
                # print(response_divs[1].text)

            if len(response_divs) > laenge:
                response_div = response_divs[-1]  # Select the last matching div element
                current_text = response_div.text

                if len(current_text) > previous_length:
                    # print("hallo\n")
                    # print(zero_counter)
                    new_text = current_text[previous_length:]
                    if printer == 1:
                        print(new_text, end='', flush=True)
                    previous_length = len(current_text)
                    zero_counter = 0
                elif len(current_text) <= previous_length and len(response_divs[laenge].text) != 0: 
                    zero_counter = zero_counter + 1 
                    # print("bye\n")
                    # print(zero_counter)
            
        except StaleElementReferenceException:
            # Wait for a short period and attempt to find the elements again
            time.sleep(0.1)
            continue

        time.sleep(0.1)
    return leng, current_text








model = SentenceTransformer('all-mpnet-base-v2',device='cuda') 

pinecone.init(api_key="52dbaa6b-b37f-441b-a134-5d5a9ed38504", environment="us-west4-gcp-free") 
index = pinecone.Index("tutorai")

def find_match(query,k):
    query_em = model.encode(query).tolist()
    result = index.query(query_em, top_k=k, includeMetadata=True)
    
    return [result['matches'][i]['metadata']['title'] for i in range(k)],[result['matches'][i]['metadata']['context'] for i in range(k)]





def query(driver,driver2):
    laenge = 0
    laenge2 = 0
    while 1:
        print("User:" , end="")
        x = input()
        if x == "quit()":
            break
        else:
            transformer = str(find_match(x,1))
            #user_message(prompt,transformer,driver2)
            user_message(x,transformer,driver)
            print("TutorAI:" , end="")
            laenge, _= GPT_response(laenge,driver,1)
            #laenge2,input_data= GPT_response(laenge2,driver2,0)
            #entities, relations = parse_input_string(input_data)
            # print(entities)
            # print(relations)

            # Call the function with extracted entities and relations
            # plot_entities_and_relations(entities, relations)
            print("\n")

driver = load_LLM(URL)
driver2 = 0
print("\n")
query(driver, driver2)


#time.sleep(200)