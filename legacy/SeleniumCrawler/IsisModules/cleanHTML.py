from bs4 import BeautifulSoup
from bs4.element import NavigableString


def get_html_text(html_input):
    soup = BeautifulSoup(html_input, 'lxml')
    texts = []
    for element in soup.descendants:
        if isinstance(element, NavigableString) and element.parent.name not in ['script', 'style']:
            text = element.strip()
            if text:
                texts.append(text)
    return texts


def main():
    with open("../temp.html", "r", encoding="utf-8") as file:
        html_content = file.read()
    text = get_html_text(html_content)
    print(text)

if __name__ == '__main__':
    main()