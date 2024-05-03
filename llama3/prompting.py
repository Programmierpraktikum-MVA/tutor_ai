import socket

def send_prompt(prompt):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(('127.0.0.1', 65432))
        s.sendall(prompt.encode('utf-8'))
        response = s.recv(1024)
        return response.decode('utf-8')

while True:
    prompt = input("Enter your prompt: ")
    if prompt.lower() == "exit":
        break
    llama3_response = send_prompt(prompt)
    print("Llama3 response:", llama3_response)
