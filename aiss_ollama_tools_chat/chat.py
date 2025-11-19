#!/usr/bin/env python3
from openai import OpenAI
from pathlib import Path
import requests
import json
import os
import datetime


class Chat:

    @staticmethod
    def strMsg(eventType:str, content:str) -> dict[str, str]:
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'role': eventType,
            'content': content
        }

    def __init__(self, model:str, sysPrompt:str, maxChatLength:int, userName:str="User", prevContext:str=None, mcpUrl:str=None, mcpToken:str=None):
        self.model = model
        self.sysPrompt = ""
        self.userName = userName
        self.mcpUrl = mcpUrl
        self.mcpToken = mcpToken
        self.client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"
        )
        self.tools = []
        self.tools = self.loadMcpTools()
        self.chatHistory = []
        self.sysPrompt:str = ""
        self.extraContext:str = ""
        self.contextualData:str = ""
        self.maxChatLength:int = maxChatLength
        self.localTools = {
            "cambiar_system_prompt": self.cambiarSystemPrompt,
            "almacenar_datos_contextuales": self.almacenarDatosContextuales
        }
        with open(sysPrompt, "r") as archivo:
            self.sysPrompt = archivo.read()
        if prevContext:
            self.deserializeContext(prevContext)

    def resolveRef(self, ref, openapi_spec):
        if not ref.startswith("#/"):
            return None
        
        path_parts = ref[2:].split("/")
        current = openapi_spec
        for part in path_parts:
            current = current.get(part, {})
        
        return current

    def openapiToOpenaiTools(self, openapi_spec):
        tools = []
        
        for path, methods in openapi_spec.get("paths", {}).items():
            for method, details in methods.items():
                operation_id = details.get("operationId")
                if not operation_id:
                    continue
                
                description = details.get("summary", "") or details.get("description", "")
                
                parameters = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
                request_body = details.get("requestBody", {})
                if request_body:
                    schema = request_body.get("content", {}).get("application/json", {}).get("schema", {})
                    if "$ref" in schema:
                        schema = self.resolveRef(schema["$ref"], openapi_spec)
                    if "properties" in schema:
                        parameters["properties"] = schema["properties"]
                    if "required" in schema:
                        parameters["required"] = schema["required"]
                
                tools.append({
                    "type": "function",
                    "function": {
                        "name": operation_id,
                        "description": description,
                        "parameters": parameters
                    }
                })
        return tools

    def loadMcpTools(self):
        tools = []
        if self.mcpUrl and self.mcpToken:
            try:
                openApiSpec = requests.get(f"{self.mcpUrl}/openapi.json").json()
                tools = self.openapiToOpenaiTools(openApiSpec)
            except Exception as e:
                print(f"Error cargando herramientas MCP: {e}")
                return
        tools.extend([
            {
                "type": "function",
                "function": {
                    "name": "cambiar_system_prompt",
                    "description": "Cambia el system prompt del chat\nImportante: El nuevo system prompt sustituirá por completo al anterior",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sysPrompt": {
                                "type": "string",
                                "description": "Nuevo system prompt"
                            }
                        },
                        "required": ["sysPrompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "almacenar_datos_contextuales",
                    "description": "Almacena datos que persisten en la conversación.\nEstos datos se añaden al principio del prompt para ayudar a recordar cosas\nImportante: Los nuevos datos contextuales sustituirán por completo al anterior",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "string",
                                "description": "Datos a almacenar"
                            }
                        },
                        "required": ["data"]
                    }
                }
            }
        ])
        return tools

    def cambiarSystemPrompt(self, args):
        nuevo_prompt = args.get("sysPrompt", "")
        self.sysPrompt = nuevo_prompt
        return f"System prompt actualizado ({len(nuevo_prompt)} caracteres)"

    def almacenarDatosContextuales(self, args):
        data = args.get("data", "")
        self.contextualData = data
        return f"Datos almacenados. Total: {len(self.contextualData)} caracteres"

    def execute_mcp_tool(self, toolName, arguments):
        if toolName in self.localTools:
            return self.localTools[toolName](arguments)
        path = toolName.replace("tool_", "").replace("_post", "")
        headers = {"Content-Type": "application/json"}
        if self.mcpToken:
            headers["Authorization"] = f"Bearer {self.mcpToken}"
        
        # print(f"[DEBUG] Ejecutando herramienta (path): {path}")
        # print(f"[DEBUG] URL completa: {self.mcpUrl}{path}")
        
        try:
            response = requests.post(f"{self.mcpUrl}{path}", json=arguments, headers=headers, timeout=5)
            response.raise_for_status()
            # print(f"[DEBUG] Full response: {response}")
            # print(f"[DEBUG] Response status: {response.status_code}")
            # print(f"[DEBUG] Response headers: {response.headers}")
            # print(f"[DEBUG] Response text: {response.text[:200]}...")
            try:
                data = response.json()
                if isinstance(data, dict) and "result" in data:
                    return str(data["result"])
                elif isinstance(data, dict):
                    return str(data)
                else:
                    return str(data)
            except:
                return response.text
        except Exception as e:
            return f"Error ejecutando tool: {str(e)}"

    def doChat(self, prompt:str, extraMsg:str=None):
        if extraMsg:
            self.chatHistory.append(Chat.strMsg("user", extraMsg))
        self.chatHistory.append(Chat.strMsg("user", prompt))
        messages = [{"role": "system", "content": self.sysPrompt}] + self.chatHistory[-self.maxChatLength:]
        while True:
            response = self.client.chat.completions.create(model=self.model, messages=messages, tools=self.tools, stream=False)
            message = response.choices[0].message
            if message.tool_calls:
                assistant_msg = {"role": "assistant", "content": message.content or "", "tool_calls": [
                        {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                        for tc in message.tool_calls
                    ]
                }
                messages.append(assistant_msg)
                self.chatHistory.append(assistant_msg)
                for tc in message.tool_calls:
                    print(tc)
                    print(f"[usando {tc.function.name}...]", end=" ", flush=True)
                    result = self.execute_mcp_tool(tc.function.name, json.loads(tc.function.arguments))
                    
                    tool_msg = {"role": "tool", "tool_call_id": tc.id, "content": str(result)}
                    messages.append(tool_msg)
                    self.chatHistory.append(tool_msg)
                    continue
                self.chatHistory.append({ "role": "assistant", "content": message.content})
                continue
            else:
                self.chatHistory.append({ "role": "assistant", "content": message.content})
                return message.content


    def getChatHistory(self) -> str:
        return self.chatHistory
    
    def getChatHistoryFormatted(self) -> str:
        formattedStrings = []
        i = 0
    
        for dictionary in self.chatHistory:
            turnNum = (i // 2) * 2
            role = dictionary.get("role", "")
            content = dictionary.get("content", "")
            if role == "user":
                formattedString = f"Turn {turnNum} - {self.userName}: {content}"
            else:
                formattedString = f"Turn {turnNum} - {self.model}: {content}"
            formattedStrings.append(formattedString)
            i += 1
        return "\n".join(formattedStrings)

    def rewind(self, turns=1) -> str:
        if turns < 0:
            raise ValueError(f"Rewind parameter `turns` cannot be a negative value. Request: {turns}")
        self.chatHistory = self.chatHistory[:-min(turns*2, len(self.chatHistory))]

    def _safeSerialize(self, path, data) -> None:
        try:
            fullPath = Path(path)
            fullPath.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as file:
                file.write(json.dumps(data, indent=2, ensure_ascii=False))
        except FileNotFoundError:
            raise FileNotFoundError(f"The file '{path}' does not exist")
        except PermissionError:
            raise PermissionError(f"You don't have permissions to access '{path}'")
        except UnicodeDecodeError:
            raise UnicodeDecodeError(f"Encoding error in '{path}'")
        except Exception as e:
            raise Exception(f"Unknown error: {e}")
        return None

    def _safeDeserialize(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"The file '{path}' does not exist")
        except PermissionError:
            raise PermissionError(f"You don't have permissions to access '{path}'")
        except UnicodeDecodeError:
            raise UnicodeDecodeError(f"Encoding error in '{path}'")
        except Exception as e:
            raise Exception(f"Unknown error: {e}")
        return None

    def serializeContext(self, path):
        self._safeSerialize(path, self.chatHistory)
    
    def deserializeContext(self, path):
        self.chatHistory = self._safeDeserialize(path)

    def serializeParams(self, path):
        self._safeSerialize(path, {
                "app":"aiss_ollama_tools_chat",
                "model":self.model,
                "maxChatLength":self.maxChatLength,
                "userName":self.userName,
                "mcpUrl":self.mcpUrl,
                "sysPrompt":self.sysPrompt
            })

    def deserializeParams(self, path):
        data = self._safeDeserialize(path)
        self.model = data["model"]
        self.maxChatLength = data["maxChatLength"]
        self.userName = data["userName"]
        self.sysPrompt = data["sysPrompt"]
    

    def makeBackup(self, folder:str = None):
        logsFolder = "./logs"
        os.makedirs(logsFolder, exist_ok=True)
        if folder:
            folderName = f"{folder}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        else:
            folderName = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fullPath = os.path.join(logsFolder, folderName)
        os.makedirs(fullPath, exist_ok=True)
        print(f"Folder '{fullPath}' Created")
        self.serializeContext(os.path.join(fullPath, "chat.json"))
        self.serializeParams(os.path.join(fullPath, "params.log"))
        return
    

