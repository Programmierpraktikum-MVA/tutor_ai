import spacy

# Laden Sie das SpaCy Deutschmodell
nlp = spacy.load('de_core_news_sm')

def preprocess_transcripts(transcripts):
    sentences = []
    for transcript in transcripts:
        for timestamp in transcript['Timestamps']:
            doc = nlp(timestamp['text'])
            sentences.extend([sent.text for sent in doc.sents])
    return sentences

# Beispiel für das Laden und Vorverarbeiten von Transkripten
if __name__ == "__main__":
    import json

    # Beispieltranskript
    transcripts = json.loads('[{"lecture": "38479_104_course_video", "Timestamps": [{"text": "  Liebe Studentinnen, liebe Studenten, ich begruesse Sie sehr herzlich. Willkommen in der wunderbaren  Welt der Algorithmen und Datenstruktur. In diesem Jahr ist es eine Welt, in der Sie viel  Flexibilitaet und Eigenverantwortung haben werden. Wir haben neue Formate fuer das Lehren  und Lernen ohne Praesenzbetrieb entwickelt. Das wird Sie vor neue Herausforderungen stellen.", "start": 0.0, "end": 28.8}, {"text": "  Und auch uns, das Team Algorith. Um diese Herausforderungen aus Chance zu nutzen,  bitten wir Sie kontinuierlich um Rueckmeldung. So koennen wir die Lehrveranstaltung waehrend des  Semesters anpassen. Ausserdem erfahren wir, welche der neuen Elemente die Lehrer auch in Zukunft  bereichern koennen. Fuer die Rueckmeldung werden Sie Frageboegen auf der Kurswebseite finden.", "start": 28.8, "end": 51.480000000000004}, {"text": "  Das Team Algorith freut sich auf diese besondere Ausgabe des Kurses und wuenscht Ihnen viel Spass  und viel Erfolg.", "start": 51.480000000000004, "end": 52.56}]}]')

    sentences = preprocess_transcripts(transcripts)
    for sent in sentences:
        print(sent)
