import json

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
import math
import torch
import wikipedia
from pathlib import Path
from newspaper import Article, ArticleException
from GoogleNews import GoogleNews
import IPython
from IPython.core.display import display, HTML
from pyvis.network import Network


# Load model and tokenizer
tokenizer = AutoTokenizer.from_pretrained("Babelscape/rebel-large")
model = AutoModelForSeq2SeqLM.from_pretrained("Babelscape/rebel-large")
directory = 'KB_data'

def extract_relations_from_model_output(text):
    relations = []
    relation, subject, relation, object_ = '', '', '', ''
    text = text.strip()
    current = 'x'
    text_replaced = text.replace("<s>", "").replace("<pad>", "").replace("</s>", "")
    for token in text_replaced.split():
        if token == "<triplet>":
            current = 't'
            if relation != '':
                relations.append({
                    'head': subject.strip(),
                    'type': relation.strip(),
                    'tail': object_.strip()
                })
                relation = ''
            subject = ''
        elif token == "<subj>":
            current = 's'
            if relation != '':
                relations.append({
                    'head': subject.strip(),
                    'type': relation.strip(),
                    'tail': object_.strip()
                })
            object_ = ''
        elif token == "<obj>":
            current = 'o'
            relation = ''
        else:
            if current == 't':
                subject += ' ' + token
            elif current == 's':
                object_ += ' ' + token
            elif current == 'o':
                relation += ' ' + token
    if subject != '' and relation != '' and object_ != '':
        relations.append({
            'head': subject.strip(),
            'type': relation.strip(),
            'tail': object_.strip()
        })
    return relations

class KB():
    def __init__(self):
        self.entities = []  #{} { entity_title: {...} }
        self.relations = []  # [ head: entity_title, type: ..., tail: entity_title,
        # meta: { article_url: { spans: [...] } } ]
        self.sources = {}  # { article_url: {...} }

    def are_relations_equal(self, r1, r2):
        return all(r1[attr] == r2[attr] for attr in ["head", "type", "tail"])

    def exists_relation(self, r1):
        return any(self.are_relations_equal(r1, r2) for r2 in self.relations)

    def get_wikipedia_data(self, candidate_entity):
        try:
            page = wikipedia.page(candidate_entity, auto_suggest=False)
            entity_data = {
                "title": page.title,
                "url": page.url,
                "summary": page.summary
            }
            return entity_data
        except:
            return None

    def merge_with_kb(self, kb2):
        for r in kb2.relations:
            article_url = list(r["meta"].keys())[0]
            source_data = kb2.sources[article_url]
            self.add_relation(r, source_data["article_title"],
                              source_data["article_publish_date"])

    def add_entity(self, e):
        #self.entities[e["title"]] ={k: v for k, v in e.items() if k != "title"}
       if e not in self.entities:
            self.entities.append(e)

    #def merge_relations(self, r1):
    #    r2 = [r for r in self.relations
    #          if self.are_relations_equal(r1, r)][0]
    #    spans_to_add = [span for span in r1["meta"]["spans"]
    #                    if span not in r2["meta"]["spans"]]
    #    r2["meta"]["spans"] += spans_to_add

    def add_relation(self, r, article_title, article_publish_date):
        # check on wikipedia
        candidate_entities = [r["head"], r["tail"]]
        #entities = [self.get_wikipedia_data(ent) for ent in candidate_entities] # for entity linking
        entities =[]

        #entities that are sentences are not helpful
        for e in range(len(candidate_entities)):
            tmp = candidate_entities[e].split()
            if len(tmp) < 3:
                entities.append(candidate_entities[e])

        # if one entity does not exist, stop
        #if any(ent is None for ent in entities):
        #    return
        if(len(entities) != 2):
            return

        # manage new entities
        for e in entities:
            self.add_entity(e)
        #self.add_entity(entities[0])
        #self.add_entity(entities[1])

        # rename relation entities with their wikipedia titles
        #r["head"] = entities[0]["title"]
        #r["tail"] = entities[1]["title"]

        # add source if not in kb
        article_url = list(r["meta"].keys())[0]
        if article_url not in self.sources:
            self.sources[article_url] = {
                "article_title": article_title,
                "article_publish_date": article_publish_date
            }

        # manage new relation
        if not self.exists_relation(r):
            self.relations.append(r)
        else:
            self.merge_relations(r)

    def merge_relations(self, r2):
        r1 = [r for r in self.relations
              if self.are_relations_equal(r2, r)][0]

        # if different article
        article_url = list(r2["meta"].keys())[0]
        if article_url not in r1["meta"]:
            r1["meta"][article_url] = r2["meta"][article_url]

        # if existing article
        else:
            spans_to_add = [span for span in r2["meta"]["spans"]
                            if span not in r1["meta"]["spans"]]
            r1["meta"]["spans"] += spans_to_add

    def print(self):
        print("Entities:")
        for e in self.entities:
            print(f"  {e}")
        print("Relations:")
        for r in self.relations:
            print(f"  {r}")
        print("Sources:")
        for s in self.sources.items():
            print(f"  {s}")


def from_small_text_to_kb(text, verbose=False):
    kb = KB()

    # Tokenizer text
    model_inputs = tokenizer(text, max_length=512, padding=True, truncation=True,
                            return_tensors='pt')
    if verbose:
        print(f"Num tokens: {len(model_inputs['input_ids'][0])}")

    # Generate
    gen_kwargs = {
        "max_length": 216,
        "length_penalty": 0,
        "num_beams": 3,
        "num_return_sequences": 3
    }
    generated_tokens = model.generate(
        **model_inputs,
        **gen_kwargs,
    )
    decoded_preds = tokenizer.batch_decode(generated_tokens, skip_special_tokens=False)

    # create kb
    for sentence_pred in decoded_preds:
        relations = extract_relations_from_model_output(sentence_pred)
        for r in relations:
            kb.add_relation(r)

    return kb

def from_text_to_kb(text, article_url, span_length=128, article_title=None,
                    article_publish_date=None, verbose=False):
    # tokenize whole text
    inputs = tokenizer([text], return_tensors="pt")

    # compute span boundaries
    num_tokens = len(inputs["input_ids"][0])
    if verbose:
        print(f"Input has {num_tokens} tokens")
    num_spans = math.ceil(num_tokens / span_length)
    if verbose:
        print(f"Input has {num_spans} spans")
    overlap = math.ceil((num_spans * span_length - num_tokens) /
                        max(num_spans - 1, 1))
    spans_boundaries = []
    start = 0
    for i in range(num_spans):
        spans_boundaries.append([start + span_length * i,
                                 start + span_length * (i + 1)])
        start -= overlap
    if verbose:
        print(f"Span boundaries are {spans_boundaries}")

    # transform input with spans
    tensor_ids = [inputs["input_ids"][0][boundary[0]:boundary[1]]
                  for boundary in spans_boundaries]
    tensor_masks = [inputs["attention_mask"][0][boundary[0]:boundary[1]]
                    for boundary in spans_boundaries]
    inputs = {
        "input_ids": torch.stack(tensor_ids),
        "attention_mask": torch.stack(tensor_masks)
    }

    # generate relations
    num_return_sequences = 3
    gen_kwargs = {
        "max_length": 256,
        "length_penalty": 0,
        "num_beams": 3,
        "num_return_sequences": num_return_sequences
    }
    generated_tokens = model.generate(
        **inputs,
        **gen_kwargs,
    )

    # decode relations
    decoded_preds = tokenizer.batch_decode(generated_tokens,
                                           skip_special_tokens=False)

    # create kb
    kb = KB()
    i = 0
    for sentence_pred in decoded_preds:
        current_span_index = i // num_return_sequences
        relations = extract_relations_from_model_output(sentence_pred)
        for relation in relations:
            relation["meta"] = {

                    "spans": [spans_boundaries[current_span_index]]

            }
            kb.add_relation(relation, article_title, article_publish_date)
        i += 1

    return kb


def save_network_html(kb, filename="network.html"):
    # create network
    net = Network(directed=True, width="700px", height="700px", bgcolor="#eeeeee",notebook=True)

    # nodes
    color_entity = "#00FF00"
    for e in kb.entities:
        net.add_node(e, shape="circle", color=color_entity)

    # edges
    for r in kb.relations:
        net.add_edge(r["head"], r["tail"], title=r["type"], label=r["type"])

    # save network
    net.repulsion(
        node_distance=200,
        central_gravity=0.2,
        spring_length=200,
        spring_strength=0.05,
        damping=0.09
    )
    net.set_edge_smooth('dynamic')
    net.show(filename)

def from_json_to_kb(path):
    with open(f'{path}') as json_file:
        v = json.load(json_file)
    string = ""
    for m in v['messages']:
        string += m['text'] + ". "

    kb = from_text_to_kb(string, article_title=v['name'], article_url=v['link'])
    return kb

def from_dir_to_text():
    files = Path(directory).glob('*')
    kb = KB()
    bigstring = " "
    for file in files:
        kb1 = from_json_to_kb(file)
        kb.merge_with_kb(kb1)

    return kb



text = "Napoleon Bonaparte (born Napoleone di Buonaparte; 15 August 1769 – 5 " \
"May 1821), and later known by his regnal name Napoleon I, was a French military " \
"and political leader who rose to prominence during the French Revolution and led " \
"several successful campaigns during the Revolutionary Wars. He was the de facto " \
"leader of the French Republic as First Consul from 1799 to 1804. As Napoleon I, " \
"he was Emperor of the French from 1804 until 1814 and again in 1815. Napoleon's " \
"political and cultural legacy has endured, and he has been one of the most " \
"celebrated and controversial leaders in world history."

#kb = from_small_text_to_kb(text, verbose=True)
#kb = from_json_to_kb('LMI_fixed.json')
#kb =from_text_to_kb(text,article_url="lol")
kb = from_dir_to_text()
filename = "network_3_google.html"
save_network_html(kb, filename=filename)
#IPython.lib.display.HTML(filename=filename)
display(HTML(filename=filename))
#kb.print()
# Num tokens: 133
# Relations:
#   {'head': 'Napoleon Bonaparte', 'type': 'date of birth', 'tail': '15 August 1769'}
#   {'head': 'Napoleon Bonaparte', 'type': 'date of death', 'tail': '5 May 1821'}
#   {'head': 'Napoleon Bonaparte', 'type': 'participant in', 'tail': 'French Revolution'}
#   {'head': 'Napoleon Bonaparte', 'type': 'conflict', 'tail': 'Revolutionary Wars'}
#   {'head': 'Revolutionary Wars', 'type': 'part of', 'tail': 'French Revolution'}
#   {'head': 'French Revolution', 'type': 'participant', 'tail': 'Napoleon Bonaparte'}
#   {'head': 'Revolutionary Wars', 'type': 'participant', 'tail': 'Napoleon Bonaparte'}