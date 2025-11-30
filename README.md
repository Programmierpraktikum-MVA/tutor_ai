
# Tutor AI

Tutor AI is an innovative project designed to harness the power of advanced language models to provide educational assistance. Built on the LLaMa3 model, Tutor AI offers users personalized learning experiences and intelligent tutoring, that includes Q&A, inspiring brainstorming and up-to-date information.

## Features (current)

- Matrix chatbot (no RAG): Matrix text → local Ollama (llama3.1) → reply back to the room
- Commands: `!help`, `!status`

## Prerequisites

- Python 3.8–3.11, pip, virtualenv
- Local Ollama with model `llama3.1` (or set your model in `config.yaml`)
- Matrix account + access token

## Setup

1) Clone the repo and activate your virtual environment.  
2) Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3) Copy `config.example.yaml` to `config.yaml` and fill in Matrix credentials, allowed rooms ids; adjust Ollama host/model if needed.  
4) Prepare the Ollama model:
   ```bash
   ollama pull llama3.1
   ollama serve
   ```

## Start

From the repo root:
```bash
CONFIG_PATH=config.yaml python -m bot.main
```

## Usage

- Invite the bot to a **non-E2E** room (it auto-joins if the room is allowed).
- Any new message in an allowed room triggers a reply; commands via `!help` and `!status`.

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Maximilian Hans - m.hans@tu-berlin.de

Project Link: [https://github.com/Programmierpraktikum-MVA/tutor_ai](https://github.com/Programmierpraktikum-MVA/tutor_ai)
