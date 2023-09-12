import requests
from bs4 import BeautifulSoup
import json
"""
Import the class and call the execute method with the needed parameters
"""


# Don't copy text from links
def remove_link_content(soup):
    exclude = soup.find_all("ul", class_="ui-treenode-children")  # find class where text link is stored
    for e in exclude:
        e.decompose()  # remove it


def manual_corrections(facts, lang):
    if lang == 1:
        try:
            del facts["POS-Verknüpfungen"]
            del facts["Modulbestandteile"]
            del facts["Literaturhinweise, Skripte"]
            del facts["Abschluss des Moduls"]
        except KeyError:
            pass
    else:
        try:
            del facts["POS-Verknüpfungen"]
            del facts["Module Components"]
            del facts["Recommended reading, Lecture notes"]
            del facts["Module completion"]
        except KeyError:
            pass
    return facts


def execute(moses_id: int, version: int, language: str) -> dict:
    lang = 1 if language == "de" else 2
    url = f'https://moseskonto.tu-berlin.de/moses/modultransfersystem/bolognamodule/beschreibung/anzeigen.html?number={moses_id}&version={version}&sprache={lang}'
    page = requests.get(url)
    if page == None:
        return dict()
    samples = BeautifulSoup(page.content, 'html.parser')

    remove_link_content(samples)

    strips = list(samples.stripped_strings)
    labels = samples.find_all('label')
    infos = samples.find_all('h3')
    spans = samples.find_all('h4')

    res = []

    #res.append(f'url')
    for s in labels:
        res.append(s.get_text())
    for s in infos:
        res.append(s.text)
    for s in spans:
        res.append(s.text)

    facts = dict()
    facts["url"] = url
    for r in res:
        if r == 'Abschluss des Moduls':
            continue
        if r == 'Bestätigung':
            break
        if r in strips:
            j = strips.index(r)
            s = ''
            while j + 1 < len(strips) and strips[j + 1] not in res:
                if 'Moses-Version' in strips[j + 1]:
                    break
                s = s + ' ' + strips[j + 1]
                j = j + 1
        s = s.replace('\r', '')
        s = s.replace('\n', '')
        while '  ' in s:
            s = s.replace('  ', ' ')
        while '  ' in r:
            r = r.replace('  ', ' ')

        facts[r.replace(':', '')] = s

    facts = manual_corrections(facts, lang)

    empty_keys = [k for k, v in facts.items() if v == '']
    for e in empty_keys:
        facts[e] = "No information available."

    facts = {k: v.strip() for k, v in facts.items()}

    return facts

course_ids = [40213,40464]
for course_id in course_ids:
    # '1' for moses version , 'de' for language, '1' can change
    test = execute(course_id, 1, "de")
    with open(f'{course_id}.json', 'w') as outfile:
        json.dump(test, outfile)
    print(test)