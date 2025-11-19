import sys
import argparse
import time

from aiss_ollama_tools_chat.chat import Chat


def main():
    parser = argparse.ArgumentParser(
        description='OpenAPI user-assistant chat app with tools support.',
        epilog='Example: ollama-tools-chat gemma3:12b-it-q8_0 sysPrompt.txt -l 20 -u MyName -c context.json -s 127.0.0.1:8100 -p password123'
    )
    
    parser.add_argument('model', help='Model to use')
    parser.add_argument('sysPrompt', help='Plain text file with the system prompt')
    parser.add_argument('--maxLength', '-l', type=int, default=20,
                        help='Maximum context lenght (default: 20)')
    parser.add_argument('--userName', '-u', type=str, default="User",
                        help='User name (default: "User")')
    parser.add_argument('--prevContext', '-c', type=str, default=None,
                        help='Txt file path with previous chat context (default: None)')
    parser.add_argument('--serverAddress', '-s', type=str, default=None,
                        help='MCP server IP:PORT')
    parser.add_argument('--serverPassword', '-p', type=str, default=None,
                        help='Server password')
    
    args = parser.parse_args()
    
    chat = Chat(args.model, args.sysPrompt, args.maxLength, args.userName, args.prevContext, args.serverAddress, args.serverPassword)
    while True:
        prompt = input(f"{chat.userName}: ")
        try:
            if prompt in ["quit", "exit"]:
                print("Good bye!")
                break
            elif prompt.startswith("save"):
                if prompt.startswith("save:"):
                    chat.serializeContext(prompt[len("save:"):].strip())
                else:
                    chat.serializeContext("./context.json")
            elif prompt.startswith("restore"):
                if prompt.startswith("restore:"):
                    chat.deserializeContext(prompt[len("restore:"):].strip())
                else:
                    chat.deserializeContext("./context.json")
            elif prompt.startswith("rewind"):
                if prompt.startswith("rewind:"):
                    chat.rewind(int(prompt[len("rewind:"):].strip()))
                else:
                    chat.rewind()
            else:
                print(f"\n{chat.model}: {chat.doChat(prompt)}\n")
        except Exception as e:
            print(f"{e}\n")
    chat.makeBackup()
    return

if __name__ == "__main__":
    main()