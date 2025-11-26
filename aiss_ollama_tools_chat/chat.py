#!/usr/bin/env python3
from openai import OpenAI
from pathlib import Path
import requests
import json
import os
import datetime

# ToolLoader
import importlib.util
import sys
import json

from aiss_ollama_chat.chat import Chat as BaseChat
from aiss_ollama_chat.fileIO import FileIO

class Chat(BaseChat):

    @staticmethod
    def strMsg(eventType:str, content:str) -> dict[str, str]:
        return {
            'timestamp': datetime.datetime.now().isoformat(),
            'role': eventType,
            'content': content
        }

    def __init__(self, model:str, sysPrompt:str, maxChatLength:int=20, userName:str="user", prevContext:str=None, addDateTimeToPrompt:bool=False,
                 rawToolsFunctions:str=None, rawToolsDefinitions:str=None, mcpUrl:str=None, mcpToken:str=None):
        self.model:str = model
        self.sysPrompt:str = ""
        self.maxChatLength:int = maxChatLength
        self.userName:str = userName
        self.addDateTimeToPrompt:bool = addDateTimeToPrompt
        self.chatHistory:dict[str, str] = []
        self.operations = {
            "save": self._handleSave,
            "restore": self._handleRestore,
            "rewind": self._handleRewind
        }
        self.mcpUrl = mcpUrl
        self.mcpToken = mcpToken
        self.localTools = {}
        self.tools = self.loadOpenAPImcpTools()
        if rawToolsFunctions and rawToolsDefinitions:
            self.localTools = self.loadPyFile(rawToolsFunctions)
            self.tools.extend(self.loadJsonFile(rawToolsDefinitions))
        print(self.localTools)
        print(self.tools)
        self.client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"
        )
        # self.localTools = {
        #     "cambiar_system_prompt": self.cambiarSystemPrompt,
        #     "almacenar_datos_contextuales": self.almacenarDatosContextuales
        # }
        with open(sysPrompt, "r") as archivo:
            self.sysPrompt = archivo.read()
        if prevContext:
            FileIO.deserializeDict(prevContext)

    def loadPyFile(self, path):
        # Cargamos el módulo desde el archivo .py
        spec = importlib.util.spec_from_file_location("dynamic_module", path)
        dynamicModule = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dynamicModule)
        
        # Obtenemos las funciones del módulo
        functions = [attr for attr in dir(dynamicModule) if callable(getattr(dynamicModule, attr))]
        
        # Creamos el diccionario de herramientas con funciones wrapper
        localTools = {}
        for funcName in functions:
            func = getattr(dynamicModule, funcName)
            # Creamos un wrapper que mantenga el self del ToolLoader
            def make_wrapper(func, self_ref):
                def wrapper(args):
                    return func(self_ref, args)
                return wrapper
            
            localTools[funcName] = make_wrapper(func, self)

        return localTools

    def loadJsonFile(self, path):
        # Cargamos el archivo JSON con las definiciones de funciones
        with open(path, 'r') as file:
            data = json.load(file)
        
        # Aquí podrías procesar los datos del JSON si es necesario
        # Por ahora, solo lo cargamos
        return data

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

    def loadOpenAPImcpTools(self):
        tools = []
        if self.mcpUrl and self.mcpToken:
            try:
                openApiSpec = requests.get(f"{self.mcpUrl}/openapi.json").json()
                tools = self.openapiToOpenaiTools(openApiSpec)
            except Exception as e:
                print(f"Error cargando herramientas MCP: {e}")
                return
        return tools

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

    

