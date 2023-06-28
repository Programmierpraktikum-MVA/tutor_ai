def structured_input(prompt,transformer):
    Frage = "Frage:"
    Quelle = "Quelle"
    prompt_eng = "beantworte nur die Frage die ich gestellt habe" 
    return Frage + prompt +  transformer + prompt_eng  