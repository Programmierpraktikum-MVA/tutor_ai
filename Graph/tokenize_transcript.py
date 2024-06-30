import json
import nltk
nltk.download('punkt')
from nltk.tokenize import sent_tokenize


# Beispieltranskript
transkript = '[{"lecture": "38479_104_course_video", "Timestamps": [{"text": "  Liebe Studentinnen, liebe Studenten, ich begruesse Sie sehr herzlich. Willkommen in der wunderbaren  Welt der Algorithmen und Datenstruktur. In diesem Jahr ist es eine Welt, in der Sie viel  Flexibilitaet und Eigenverantwortung haben werden. Wir haben neue Formate fuer das Lehren  und Lernen ohne Praesenzbetrieb entwickelt. Das wird Sie vor neue Herausforderungen stellen.", "start": 0.0, "end": 28.8}, {"text": "  Und auch uns, das Team Algorith. Um diese Herausforderungen aus Chance zu nutzen,  bitten wir Sie kontinuierlich um Rueckmeldung. So koennen wir die Lehrveranstaltung waehrend des  Semesters anpassen. Ausserdem erfahren wir, welche der neuen Elemente die Lehrer auch in Zukunft  bereichern koennen. Fuer die Rueckmeldung werden Sie Frageboegen auf der Kurswebseite finden.", "start": 28.8, "end": 51.480000000000004}, {"text": "  Das Team Algorith freut sich auf diese besondere Ausgabe des Kurses und wuenscht Ihnen viel Spass  und viel Erfolg.", "start": 51.480000000000004, "end": 52.56}]}]'

# JSON-Transkript laden
transkript_data = json.loads(transkript)

# Funktion zum Extrahieren und Tokenisieren von Sätzen
def extract_and_tokenize_sentences(transkript_data):
    all_sentences = []
    for lecture in transkript_data:
        for timestamp in lecture["Timestamps"]:
            text = timestamp["text"]
            sentences = sent_tokenize(text)
            all_sentences.extend(sentences)
    return all_sentences

# Tokenisieren der Sätze
sentences = extract_and_tokenize_sentences(transkript_data)

# Ausgabe der tokenisierten Sätze
for i, sentence in enumerate(sentences):
    print(f"Sentence {i+1}: {sentence}")
