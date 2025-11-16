#!/usr/bin/env python3
"""ollama_mcp_chat.py - Chat interactivo con tools MCP en una clase Chat"""
from openai import OpenAI
import requests
import json
import os
import datetime


class Chat:
    def __init__(self, model:str, sysPrompt:str, maxChatLenght:int, mcp_url:str=None, mcp_token:str=None):
        self.model = model
        self.sysPrompt = ""
        self.mcp_url = mcp_url
        self.mcp_token = mcp_token
        self.client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"
        )
        self.tools = []
        self.tools = self.load_mcp_tools()
        self.chatHistory = []
        self.sysPrompt:str = ""
        self.extraContext:str = ""
        self.contextualData:str = ""
        self.maxChatLenght:int = maxChatLenght
        self.localTools = {
            "cambiar_system_prompt": self.cambiarSystemPrompt,
            "almacenar_datos_contextuales": self.almacenarDatosContextuales
        }
        with open(sysPrompt, "r") as archivo:
            self.sysPrompt = archivo.read()

    def resolve_ref(self, ref, openapi_spec):
        """Resuelve referencias $ref en el schema"""
        if not ref.startswith("#/"):
            return None
        
        path_parts = ref[2:].split("/")
        current = openapi_spec
        for part in path_parts:
            current = current.get(part, {})
        
        return current

    def openapi_to_openai_tools(self, openapi_spec):
        """Convierte OpenAPI a formato OpenAI tools"""
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
                # Request body
                request_body = details.get("requestBody", {})
                if request_body:
                    schema = request_body.get("content", {}).get("application/json", {}).get("schema", {})
                    if "$ref" in schema: # Resolver $ref si existe
                        schema = self.resolve_ref(schema["$ref"], openapi_spec)
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

    def load_mcp_tools(self):
        """Carga las herramientas desde el servidor MCP"""
        tools = []
        if self.mcp_url and self.mcp_token:
            try:
                openapi_spec = requests.get(f"{self.mcp_url}/openapi.json").json()
                tools = self.openapi_to_openai_tools(openapi_spec)
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
        """
        Cambia el system prompt del chat
        
        """
        nuevo_prompt = args.get("sysPrompt", "")
        self.sysPrompt = nuevo_prompt
        return f"System prompt actualizado ({len(nuevo_prompt)} caracteres)"

    def almacenarDatosContextuales(self, args):
        """
        Almacena datos contextuales que persisten en la conversación
        
        """
        data = args.get("data", "")
        self.contextualData = data
        return f"Datos almacenados. Total: {len(self.contextualData)} caracteres"

    def execute_mcp_tool(self, tool_name, arguments):
        """Ejecuta una herramienta MCP"""
        if tool_name in self.localTools:
            return self.localTools[tool_name](arguments)

        # Limpiar el operationId para obtener la ruta correcta
        path = tool_name.replace("tool_", "").replace("_post", "")
        
        # Aquí ya tienes el path correcto, así que usa el path, no el tool_name
        headers = {"Content-Type": "application/json"}
        if self.mcp_token:
            headers["Authorization"] = f"Bearer {self.mcp_token}"
        
        print(f"[DEBUG] Ejecutando herramienta (path): {path}")
        print(f"[DEBUG] URL completa: {self.mcp_url}{path}")
        
        try:
            response = requests.post(f"{self.mcp_url}{path}", json=arguments, headers=headers, timeout=5)
            response.raise_for_status()
            print(f"[DEBUG] Full response: {response}")
            print(f"[DEBUG] Response status: {response.status_code}")
            print(f"[DEBUG] Response headers: {response.headers}")
            print(f"[DEBUG] Response text: {response.text[:200]}...")  # Solo los primeros 200 caracteres
            
            # Intentar parsear como JSON
            try:
                data = response.json()
                if isinstance(data, dict) and "result" in data:
                    return str(data["result"]) # Si es un dict con "result", extraerlo
                elif isinstance(data, dict):
                    return str(data) # Si es un dict sin "result", devolver todo
                else:
                    return str(data) # Si es otro tipo (int, str, list), devolver directo
            except:
                return response.text # Si no es JSON válido, devolver texto
        except Exception as e:
            return f"Error ejecutando tool: {str(e)}"

    @staticmethod
    def strMsg(event_type:str, content:str) -> dict[str, str]:
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'role': event_type,
            'content': content
        }
    
    def doChat(self, prompt:str, extraMsg:str=None):
        if extraMsg:
            self.chatHistory.append(Chat.strMsg("user", extraMsg))
        self.chatHistory.append(Chat.strMsg("user", prompt))
        messages = [{"role": "system", "content": self.sysPrompt}] + self.chatHistory[-self.maxChatLenght:]
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
                # Sin tool_calls, imprimir respuesta final
                self.chatHistory.append({ "role": "assistant", "content": message.content})
                return message.content


    def printToFile(self, folder:str = None):
        logsFolder = "./logs"
        os.makedirs(logsFolder, exist_ok=True)
        if folder:
            folderName = f"{folder}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        else:
            folderName = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        fullPath = os.path.join(logsFolder, folderName)
        os.makedirs(fullPath, exist_ok=True)
        print(f"Folder '{fullPath}' Created")
        path = os.path.join(fullPath, "chat.log")
        with open(path, "w") as archivo:
            archivo.write(json.dumps(self.chatHistory, indent=2, ensure_ascii=False))
        path = os.path.join(fullPath, "params.log")
        with open(path, "w", encoding="utf-8") as archivo:
            archivo.write(f"""Model:
{self.model}
Max chat lenght:
{self.maxChatLenght}
System prompt:
{self.sysPrompt}
Extra context:
{self.extraContext}
""")
        return
    

