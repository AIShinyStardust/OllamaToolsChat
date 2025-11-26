import signal
import sys
import argparse
import time

from aiss_ollama_tools_chat.chat import Chat

FORCE_EXIT:int = 3

def main():
    def signalHandler(sig, frame):
        global FORCE_EXIT
        if FORCE_EXIT == 0:
            print("\n--FORCE EXIT--")
            sys.exit(0)
        else:
            print(f"\n--FORCE EXIT IN {FORCE_EXIT}--")
            FORCE_EXIT -= 1
        return

    signal.signal(signal.SIGINT, signalHandler)
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
    parser.add_argument('--addDateTimeToPrompt', '-t', type=str, default=False,
                    help='Experimental feature. Add date and time to prompt, so the AI assistant can tell what time it is (default: False)')
    parser.add_argument('--rawToolsFunctions', type=str, default=None,
                        help='File with RAW tool Python functions.')
    parser.add_argument('--rawToolsDefinitions', type=str, default=None,
                        help='(JSON) File with RAW tool definitions.')
    parser.add_argument('--serverAddress', '-s', type=str, default=None,
                        help='MCP server IP:PORT')
    parser.add_argument('--serverPassword', '-p', type=str, default=None,
                        help='Server password')
    
    args = parser.parse_args()
    
    chat = Chat(args.model, args.sysPrompt, args.maxLength, args.userName, args.prevContext, args.addDateTimeToPrompt,
                args.rawToolsFunctions, args.rawToolsDefinitions, args.serverAddress, args.serverPassword)
    while True:
        global FORCE_EXIT
        FORCE_EXIT = 3
        prompt = input(f"{chat.userName}: ")
        try:
            if prompt.startswith("exit"):
                print("Good bye!")
                break
            prompt = chat.chat(prompt)
            print(f"\n\n{prompt}")
        except Exception as e:
            print(f"{e}\n")
    chat.makeBackup()
    return

if __name__ == "__main__":
    main()