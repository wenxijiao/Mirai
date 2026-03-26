import ollama
import asyncio
from pydantic import BaseModel
from mirai.core.memories.memory import Memory


class ChatRequest(BaseModel):
    prompt: str
    session_id: str = "default"


class MiraiBot:
    def __init__(self, model_name: str = 'qwen3.5:9b', think: bool = False):
        self.model_name = model_name
        self.think = think
        self.memories = {}

    def _get_memory(self, session_id: str = "default"):
        if session_id not in self.memories:
            self.memories[session_id] = Memory(session_id=session_id)
        return self.memories[session_id]

    async def _set_model_keep_alive(self, model_name: str, keep_alive: int):
        try:
            await ollama.AsyncClient().generate(
                model=model_name,
                prompt='',
                keep_alive=keep_alive,
            )
        except Exception as e:
            print(f"Model keep-alive request failed: {e}")

    def _schedule_model_keep_alive(self, model_name: str, keep_alive: int):
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(self._set_model_keep_alive(model_name, keep_alive))

    async def warm_up(self):
        await self._set_model_keep_alive(self.model_name, -1)

    async def chat_stream(self, prompt: str = None, session_id: str = "default", tools: list = None, ephemeral_messages: list = None):
        """
        Core streaming chat flow with function-calling support.
        - tools: tool schema list passed to the model
        - ephemeral_messages: temporary context for tool calls and tool results
        """
        memory = self._get_memory(session_id)
        
        if prompt:
            user_message_id = memory.add_message("user", prompt)
            
        messages = memory.get_context()
        
        if ephemeral_messages:
            messages.extend(ephemeral_messages)

        full_response = ""

        try:
            stream = await ollama.AsyncClient().chat(
                model=self.model_name,
                messages=messages,
                think=self.think,
                tools=tools,
                stream=True,
            )
            
            async for chunk in stream:
                message = chunk.get('message', {})
                
                if 'tool_calls' in message and message['tool_calls']:
                    yield {"type": "tool_call", "tool_calls": message['tool_calls']}
                    return
                    
                content = message.get('content', '')
                if content:
                    full_response += content
                    yield {"type": "text", "content": content}
                    
        except Exception as e:
            if prompt:
                memory.delete_message(user_message_id)
            raise e

        if full_response:
            memory.add_message('assistant', full_response)

    def clear_memory(self, session_id: str = "default"):
        memory = self._get_memory(session_id)
        memory.clear_history()
        
    def change_model(self, new_model: str):
        if self.model_name == new_model:
            return

        old_model = self.model_name
        self._schedule_model_keep_alive(old_model, 0)
        
        print(f"🔄 Changing model from {old_model} to {new_model}...")
        self.model_name = new_model

        self._schedule_model_keep_alive(new_model, -1)
