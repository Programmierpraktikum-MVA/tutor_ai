
# LLama3 Installation und Startanleitung

Diese Anleitung zeigt Ihnen, wie Sie LLama3 auf Ihrem System installieren und verwenden können.

## Voraussetzungen
- Python 3.8 oder höher
- pip
- virtualenv
- cuda

## Installation

Folgen Sie diesen Schritten, um LLama3 auf Ihrem System zu installieren:

1. **Virtuelle Umgebung erstellen**

   Erstellen Sie eine neue virtuelle Umgebung namens `llama3testing`:

   ```bash
   virtualenv llama3testing
   ```

2. **Virtuelle Umgebung aktivieren**

   Aktivieren Sie die virtuelle Umgebung:

   ```bash
   source llama3testing/bin/activate
   ```

3. **Abhängigkeiten installieren**

   Installieren Sie die notwendigen Pakete mit pip:

   ```bash
   pip install accelerate==0.29.3 bitsandbytes==0.43.1 transformers==4.40.0
   ```

4. **Hugging Face Token konfigurieren**

   Erstellen Sie eine `config.json` Datei im Hauptverzeichnis Ihrer Anwendung und speichern Sie Ihren Hugging Face Token im folgenden Format:

   ```json
   {"HF_TOKEN":"Ihr_Token_hier"}
   ```

   Ersetzen Sie `Ihr_Token_Hier` mit Ihrem tatsächlichen Hugging Face Token.

5. **Anwendung starten**

   Starten Sie die Anwendung durch Ausführen der `startup.py` Datei:

   ```bash
   python startup.py
   ```
   Ingorieren Sie die 3 definierten Funktionen am Ende, diese sind lediglich eine Schnittstelle zum Prompting mit LLaMa3 und kann nach belieben angepasst werden.
   

## Nutzung

Nachdem Sie LLama3 installiert und die `startup.py` ausgeführt haben, sollte die Anwendung laufen und bereit für die Nutzung sein.

Dazu kann die Datei `prompting.py` genutzt werden und Dient als Schnittstellen zwischen der LLM und einem UI. Die hier eingegebenen Prompts werden an die LLM weitergeleiten.
   ```bash
     python prompting.py
   ```
Das ist rein Optional und kann nach belieben angepasst werden
