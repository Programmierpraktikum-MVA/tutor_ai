
# Tutor AI Scraper

Scraper for ISIS and MOSES

## Features

- **Information scraping:** Get All Information of a course

## Prerequisites

Before you begin, ensure you have met the following requirements:
- Python 3.8 or newer
- Pip and virtualenv installed on your machine

## Installation

Follow these steps to get your Tutor AI Scraper up and running:

1. **Create Virtual Environment**

   ```bash
   virtualenv SelEnv
   ```
   
2. **Start Environment**
3. **Install selenium and whisper**
      ```bash
   pip install -r requirements.txt
   #pip install selenium
   #pip install -U git+https://github.com/linto-ai/whisper-timestamped
   ```
4. **Install pytorch**
   ```
   https://pytorch.org/
   ```

## Usage

You can add modules to further improve our search capabilities

```
SeleniumCrawler/
│
├── CourseInfos/                    # Überordner für alle Modulinfos
│   └── AlgoDat                     # Beispielordner von einem Modul
│       ├── allgemein.json          # Bsp json
│       └── GreedyAlgorithm.json    # 2. Bsp json
│
├── config.json       #json mit login daten für ISIS
│
├── course_id_saved.json/           # All saved course ID's
│
├── IsisModules/                    # All modules created for isis scraping
│  
├── scraper.py                      # Main File
│
│── SelEnv                          #Virtualenv for this project
│
└── README.md                       # Diese README-Datei
```



## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Maximilian Hans - m.hans@tu-berlin.de

Project Link: [https://github.com/Programmierpraktikum-MVA/tutor_ai](https://github.com/Programmierpraktikum-MVA/tutor_ai)