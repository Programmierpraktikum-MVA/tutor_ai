import os

from unstructured.partition.pdf import partition_pdf
from paths import ISIS_PDFS_DIR




#with open ("/../../scraping/demo_folder") as demo_folder:

# Returns a List[Element] present in the pages of the parsed pdf document
# sudo apt install tesseract-ocr
print(os.getcwd())
elements = partition_pdf(str(ISIS_PDFS_DIR / "introprog-v03-komplexitaet.pdf"), strategy = "hi_res")

for elem in elements:
    print(elem)
    print("break_____________________\n")
