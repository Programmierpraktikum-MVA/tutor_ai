import json
import torch
import socket
from transformers import (AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, pipeline)

config_data = json.load(open("config.json"))
HF_TOKEN = config_data["HF_TOKEN"]

model_name = "meta-llama/Meta-Llama-3-8B-Instruct"

#Quantization Configuration

bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_use_double_quant=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16)
tokenizer = AutoTokenizer.from_pretrained(model_name, token=HF_TOKEN)

tokenizer.pad_token = tokenizer.eos_token
model = AutoModelForCausalLM.from_pretrained(model_name, device_map="auto", quantization_config=bnb_config, token=HF_TOKEN)

text_generator = pipeline ("text-generation", model=model, tokenizer=tokenizer, max_new_tokens=128)

def get_response(prompt):
	sequences = text_generator(prompt)
	gen_text = sequences[0]["generated_text"]
	return gen_text

def get_llama3_response(prompt):
	return get_response(prompt)


def listen_for_prompts():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 65432))
        s.listen()
        print("Waiting for connections...")
        while True:  # Keep listening for connections indefinitely
            conn, addr = s.accept()
            with conn:
                print('Connected by', addr)
                while True:  # Keep processing prompts within the connection
                    data = conn.recv(1024)
                    if not data:
                        break
                    prompt = data.decode('utf-8')
                    response = get_response(prompt)
                    conn.sendall(response.encode('utf-8'))


# Run the function to listen for prompts
listen_for_prompts()
