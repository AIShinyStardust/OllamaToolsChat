import sys
import argparse
import time
from chat import Chat


def main():
    parser = argparse.ArgumentParser(
        description='OpenAPI user-assistant chat app with tools support.',
        epilog='Example: ollama-tools-chat gemma3:12b-it-q8_0 sysPrompt.txt 20 127.0.0.1:8100 password123'
    )
    
    # Define argumentos posicionales
    parser.add_argument('model', help='Model to use')
    parser.add_argument('sysPrompt', help='Plain text file with the system prompt')
    parser.add_argument('maxLenght', type=int, help='Max context lenght')
    parser.add_argument('serverAddress', help='MCP server IP:PORT')
    parser.add_argument('serverPassword', help='Server password')
    
    args = parser.parse_args()  # Esto maneja -h automáticamente
    
    chat = Chat(args.model, args.sysPrompt, args.maxLenght, args.serverAddress, args.serverPassword)
    while True:
        prompt = input("You: ")
        if prompt.lower() in ["quit", "exit"]:
            print("Good bye!")
            break
        print(f"\n{chat.model}: {chat.doChat(prompt)}\n")
    chat.printToFile()
    return

if __name__ == "__main__":
    main()