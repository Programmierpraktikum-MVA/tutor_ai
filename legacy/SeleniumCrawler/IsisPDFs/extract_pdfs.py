import os

from unstructured.partition.pdf import partition_pdf




#with open ("/../../scraping/demo_folder") as demo_folder:

# Returns a List[Element] present in the pages of the parsed pdf document
# sudo apt install tesseract-ocr
print(os.getcwd())
elements = partition_pdf("pdf_folder/introprog-v03-komplexitaet.pdf", strategy = "hi_res")

for elem in elements:
    print(elem)
    print("break_____________________\n")