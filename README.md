# Ollama Tools Chat - Chatbot with Ollama

This project implements an autonomous chat system using Ollama cappable of running LLMs with tools.

## 📋 Description

The project allows creating a chat with MCP endpoint tools enabled.

## 🚀 Features

OpenAPI server support.
Raw tools support. (currently, requires editing source code)
     
## 🛠 Requirements

- Python 3.7+
- Ollama installed and running
- Required packages:
  - `ollama`
  - `aiss_ollama_chat`

## 📦 Installation

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Clone the repository:
   ```bash
   git clone <your-repository>
   cd ollamaChat
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install package using:
   ```bash
   pip install .
   ```

## ▶️ Usage

Run the program with:
```bash
ollama-tools-chat <model> <prompt> <maxLength> <mcpServerAddress> <mcpServerPassword>
```

Example:
```bash
ollama-tools-chat gemma3:12b-it-q8_0 ./sysPrompt.txt 10 127.0.0.1:8100 password123
```

## 📁 Project Structure

```
.
├── aiss_ollama_chat_autonomous/
│   ├── __init__.py
│   ├── chat.py
│   └── run.py
├── run.sh
├── setup.py
├── sysPrompt.txt
├── LICENSE
└── README.md
```

## 📄 Output

Conversation history is saved in a timestamped folder:
```
Chat-A_2025-11-09_21-00-00/
├── chat.log
└── params.py
Chat-B_2025-11-09_21-00-00/
├── chat.log
└── params.py
```

## 🤝 Contributions

Contributions are welcome! Please open an issue or submit a pull request.

## 📄 License

This project is licensed under the MIT License.