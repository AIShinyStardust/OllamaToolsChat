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

from aiss_ollama_chat.chat import Chat
from aiss_file.file import FileIO

class ToolsChat(Chat):

    def __init__(self, model:str, sysPrompt:str, maxChatLength:int=20, userName:str="user", assistantName:str="assistant", prevContext:str=None, addTimestampToOllamaDict:bool=False, addTurnToOllamaDict:bool=False, addDateTimeToPrompt:bool=False, sysPromptDropTurn:int=0, rawToolsFunctions:str=None, rawToolsDefinitions:str=None, mcpUrl:str=None, mcpToken:str=None):
        super().__init__(model, sysPrompt, maxChatLength, userName, assistantName, prevContext, addTimestampToOllamaDict, addTurnToOllamaDict, addDateTimeToPrompt, sysPromptDropTurn)
        self.mcpUrl = mcpUrl
        self.mcpToken = mcpToken
        self.localTools = {}
        self.tools = self.loadOpenAPImcpTools()
        if rawToolsFunctions and rawToolsDefinitions:
            self.localTools = self.loadPyFile(rawToolsFunctions)
            self.tools.extend(self.loadJsonFile(rawToolsDefinitions))
        print(f"Num RAW tools: {len(self.localTools)}")
        print(f"Num OpenAPI tools: {len(self.tools)}")
        self.client = OpenAI(
            base_url="http://localhost:11434/v1",
            api_key="ollama"
        )

    def loadPyFile(self, path):
        spec = importlib.util.spec_from_file_location("dynamic_module", path)
        dynamicModule = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dynamicModule)
        functions = [attr for attr in dir(dynamicModule) if callable(getattr(dynamicModule, attr))]
        localTools = {}
        for funcName in functions:
            func = getattr(dynamicModule, funcName)
            def make_wrapper(func, self_ref):
                def wrapper(args):
                    return func(self_ref, args)
                return wrapper
            
            localTools[funcName] = make_wrapper(func, self)

        return localTools

    def loadJsonFile(self, path):
        with open(path, 'r') as file:
            data = json.load(file)
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

    def doChat(self, prompt:str):
        turn = self.getLastContextTurn()+1 if self.addTurnToOllamaDict else None
        self.chatHistory.append(self.strMsg("user", prompt, turn))
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
                    print(f"[using {tc.function.name}...]", end=" ", flush=True)
                    result = self.execute_mcp_tool(tc.function.name, json.loads(tc.function.arguments))
                    
                    tool_msg = {"role": "tool", "tool_call_id": tc.id, "content": str(result)}
                    messages.append(tool_msg)
                    self.chatHistory.append(tool_msg)
                    continue
                self.chatHistory.append(self.strMsg("assistant", message.content, turn))
                continue
            else:
                self.chatHistory.append(self.strMsg("assistant", message.content, turn))
                return message.content

    

