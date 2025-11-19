# Ollama Tools Chat - Chatbot with Ollama

Ollama chat app cappable of running LLMs with tools.

## 📋 Description

The project allows creating a chat with MCP endpoint tools enabled.

## 🚀 Features

- Real-time interaction with local models
- Conversation history saved in JSON format
- Support for multiple Ollama models
- OpenAPI server support. (tested with FastMCP)
- Raw tools support. (currently, adding new raw tools requires to edit source code)
- Exit commands (`quit` or `exit`)
  - When used, the app makes a backup at "./logs/date_time" located at run path.
- Save and restore commands (`save`, `save:`, `restore`, `restore:`, `rewind` and `rewind:`)
  - `save` - Stores a conversational context file named "context.json" at run path.
  - `save:` - Stores a conversational context file at path inidicated next, related to run path.
  - `restore` - Restores a conversational context file at "context.json" located at run path.
  - `restore:` - Restores a conversational context file at path inidicated next, related to run path.
  - `rewind` - Goes back to a previous turn.
  - `rewind:` - Goes back an ammount of turns indicated next.
     
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
   ```

3. Install package using:
   ```bash
   pip install ./OllamaToolsChat
   ```

## ▶️ Usage

Run the program with:
```bash
ollama-tools-chat <model> <prompt> [options]
```

Where options are:
--maxLength or -l: Maximum context length (default: 20)
--userName or -u: User name (default: "User")  
--prevContext or -c: Path to previous chat context file (default: None)
--mcpServerAddress or -s: MCP server address (format: `http://-.-.-.-:-`)
--mcpServerPassword or -p: MCP server password
```

Example:
```bash
ollama-tools-chat gemma3:12b-it-q8_0 ./sysPrompt.txt 10 http://127.0.0.1:8100 password123
```

## 📁 Project Structure

```
.
├── aiss_ollama_tools_chat/
│   ├── __init__.py
│   ├── chat.py
│   └── run.py
├── run.sh
├── setup.py
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