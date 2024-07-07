import json
import networkx as nx
import os

def create_knowledge_graph(dir_path):
    # Knowledge Graph erstellen
    G = nx.DiGraph()

    # Listen zur Speicherung der Daten initialisieren
    all_edges = []
    all_edge_attrs = []
    node_texts = []
    node_types = []
    module_numbers = []

    # Alle JSON-Dateien im Verzeichnis durchlaufen und laden
    for filename in os.listdir(dir_path):
        if filename.endswith('.json'):
            file_path = os.path.join(dir_path, filename)
            try:
                with open(file_path, 'r') as file:
                    course_data = json.load(file)
            except json.JSONDecodeError as e:
                print(f"Fehler beim Laden der Datei {filename}: {e}")
                continue
            
            # Knoten und Kanten basierend auf JSON-Daten hinzufügen
            for course in course_data:
                course_name = course['Course_Name']
                course_id = course['Course_id']
                G.add_node(course_id, label=course_name, type='Course')
                
                # Sicherstellen, dass Forums nicht None ist
                if course['Forums']:
                    for forums in course['Forums']:  # Erste Ebene durchlaufen
                        # Sicherstellen, dass forums nicht None ist
                        if forums:
                            for forum in forums:  # Zweite Ebene durchlaufen
                                # Sicherstellen, dass forum nicht None ist
                                if forum:
                                    forum_name = forum['Forum_name']
                                    forum_id = forum['Forum_id']
                                    
                                    # Knoten hinzufügen
                                    G.add_node(forum_id, label=forum_name, type='Forum')
                                    
                                    # Kante hinzufügen
                                    G.add_edge(course_id, forum_id, relationship='contains')
                                    all_edges.append((course_id, forum_id))
                                    all_edge_attrs.append({'relationship': 'contains'})
                                    
                                    # Weitere Attribute speichern
                                    node_texts.append(forum_name)
                                    node_types.append('Forum')
                                    module_numbers.append(course_id)
                                    
                                    for discussion in forum['Discussions']:
                                        discussion_name = discussion['Discussion_Name']
                                        discussion_id = discussion['Discussion_Id']
                                        
                                        # Knoten hinzufügen
                                        G.add_node(discussion_id, label=discussion_name, type='Discussion')
                                        
                                        # Kante hinzufügen
                                        G.add_edge(forum_id, discussion_id, relationship='contains')
                                        all_edges.append((forum_id, discussion_id))
                                        all_edge_attrs.append({'relationship': 'contains'})
                                        
                                        # Weitere Attribute speichern
                                        node_texts.append(discussion_name)
                                        node_types.append('Discussion')
                                        module_numbers.append(forum_id)
                                        
                                        for message in discussion['Messages']:
                                            message_id = message['Message_id']
                                            author = message['Author']
                                            content = message['Content']
                                            
                                            # Knoten hinzufügen
                                            G.add_node(message_id, label=author, type='Message', content=content)
                                            
                                            # Kante hinzufügen
                                            G.add_edge(discussion_id, message_id, relationship='contains')
                                            all_edges.append((discussion_id, message_id))
                                            all_edge_attrs.append({'relationship': 'contains'})
                                            
                                            # Weitere Attribute speichern
                                            node_texts.append(author)
                                            node_types.append('Message')
                                            module_numbers.append(discussion_id)
    
    return G, all_edges, all_edge_attrs, node_texts, node_types, module_numbers

# Beispielaufruf der Funktion
"""
dir_path = 'course_forum_data/'
knowledge_graph, all_edges, all_edge_attrs, node_texts, node_types, module_numbers = create_knowledge_graph(dir_path)

# Beispiel: Informationen über Knoten ausgeben
for node, data in knowledge_graph.nodes(data=True):
    print(node, data)

# Beispiel: Informationen über gespeicherte Daten ausgeben
print("Gespeicherte Daten:")
print("All Edges:", all_edges)
print("All Edge Attributes:", all_edge_attrs)
print("Node Texts:", node_texts)
print("Node Types:", node_types)
print("Module Numbers:", module_numbers)
"""
