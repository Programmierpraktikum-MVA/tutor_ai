
# Tutor AI

Tutor AI is an innovative project designed to harness the power of advanced language models to provide educational assistance. Built on locally hosted LLMs via Ollama, Tutor AI offers users personalized learning experiences and intelligent tutoring, including Q&A, brainstorming, and up-to-date information.

## Features (current)

- Matrix chatbot (no RAG): Matrix text → local Ollama (`gemma3:12b` by default) → reply back to the room
- Commands: `!help`, `!status`

## Prerequisites

- Python 3.8–3.11, pip, virtualenv
- Local Ollama with model `gemma3:12b` (or set your model in `config.yaml`)
- Matrix account + access token

## Setup (first time)

1) Clone the repo and create/activate a virtual environment:
   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   ```
2) Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3) Copy `config.example.yaml` to `config.yaml` and fill in Matrix credentials, allowed room IDs; adjust Ollama host/model if needed.
4) Start Ollama once and pull the model:
   ```bash
   ollama serve
   ollama pull gemma3:12b
   ```

## How to use

1) Start Ollama: `ollama serve`
2) Activate your virtual environment (if not already active):
   ```bash
   . .venv/bin/activate
   ```
3) From the repo root, start the bot:
   ```bash
   python3 -m bot.main
   ```
4) Invite the bot to a **non-E2E** room listed in `allowed_room_ids`. Any message in an allowed room triggers a reply; commands: `!help`, `!status`.

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Contact

Maximilian Hans - m.hans@tu-berlin.de

Project Link: [https://github.com/Programmierpraktikum-MVA/tutor_ai](https://github.com/Programmierpraktikum-MVA/tutor_ai)
