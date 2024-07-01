
# Knowledge Graph Creation from Transcripts

Dieses Projekt erstellt einen Knowledge Graphen aus Transkripten, wobei jeder Satz als Knoten behandelt wird und Kanten basierend auf inhaltlicher Ähnlichkeit und Reihenfolge der Sätze erstellt werden.

## Voraussetzungen

Stellen Sie sicher, dass Sie Python 3.7 oder höher installiert haben.

## Installation

1. Erstellen Sie eine virtuelle Umgebung (optional, aber empfohlen):
   ```bash
   python -m venv env
   source env/bin/activate  # Linux/MacOS
   env\Scripts\activate  # Windows
   ```

2. Installieren Sie die erforderlichen Bibliotheken:
   ```bash
   pip install nltk
   pip install spacy
   python -m spacy download de_core_news_sm
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118  # für CUDA 11.8
   pip install torch-geometric
   pip install transformers sentence-transformers
   pip install networkx matplotlib
   ```

## Verwendung

1. Platzieren Sie Ihre Transkriptdateien im `transcripts` Ordner. Die Dateien sollten im JSON-Format vorliegen und die folgenden Felder enthalten:
   ```json
   [
       {
           "Timestamps": [
               {
                   "text": "Die Binärsuche ist ein Suchverfahren, häufig genutzt in der Informatik"
               },
               {
                   "text": "Die Laufzeit beträgt O(log(n))"
               }
           ]
       }
   ]
   ```

2. Führen Sie das Hauptskript aus, um den Knowledge Graph zu erstellen:
   ```bash
   python main.py
   ```

3. Das Skript erstellt den Graphen und speichert ihn in einer Datei namens `graph_data.pth`. Es lädt auch den Graphen und gibt ihn aus.

## Projektstruktur

- `preprocessing.py`: Enthält die Logik zum Vorverarbeiten der Transkripte und Extrahieren der Sätze.
- `extractRelations.py`: Enthält die Logik zum Extrahieren von Entitäten und Berechnen der Ähnlichkeit zwischen Sätzen.
- `createGraph.py`: Enthält die Logik zum Erstellen und Aktualisieren des Knowledge Graphen.
- `main.py`: Hauptskript, das den gesamten Prozess steuert.

## Beispiel

1. Platzieren Sie Ihre JSON-Transkripte im `transcripts` Ordner.
2. Führen Sie das Skript `main.py` aus, um den Knowledge Graph zu erstellen und zu speichern.

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert. Weitere Informationen finden Sie in der LICENSE-Datei.
