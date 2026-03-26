import uvicorn
import asyncio
import json
import os
import uuid
from copy import deepcopy
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from mirai.core.chatbot import MiraiBot
from mirai.utils.tool import TOOL_REGISTRY, execute_registered_tool, load_tools_from_directory

class ChatRequest(BaseModel):
    prompt: str
    session_id: str = "default"

bot = MiraiBot(model_name='sorc/qwen3.5-instruct-uncensored:latest', think=False)

ACTIVE_CONNECTIONS = {}
EDGE_TOOLS_REGISTRY = {}
PENDING_TOOL_CALLS = {}
TOOL_CALL_TIMEOUT_SECONDS = 30
LOCAL_TOOLS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")

def stream_event(event_type: str, **payload) -> str:
    return json.dumps({"type": event_type, **payload}) + "\n"

def get_all_tool_schemas():
    all_tools = [tool_data["schema"] for tool_data in TOOL_REGISTRY.values()]
    for edge_tools in EDGE_TOOLS_REGISTRY.values():
        all_tools.extend(edge_tools.values())
    return all_tools

def cleanup_edge_connection(edge_name: str, websocket: WebSocket):
    if ACTIVE_CONNECTIONS.get(edge_name) is websocket:
        del ACTIVE_CONNECTIONS[edge_name]
        EDGE_TOOLS_REGISTRY.pop(edge_name, None)

    for call_id, pending in list(PENDING_TOOL_CALLS.items()):
        if pending["edge_name"] != edge_name or pending["websocket"] is not websocket:
            continue

        future = pending["future"]
        if not future.done():
            future.set_exception(
                ConnectionError(f"Edge device '{edge_name}' disconnected during tool execution.")
            )
        PENDING_TOOL_CALLS.pop(call_id, None)

@asynccontextmanager
async def lifespan(app: FastAPI):
    loaded_modules = load_tools_from_directory(LOCAL_TOOLS_DIR, "mirai.tools")
    if loaded_modules:
        print(f"[Local Tools] Loaded {len(loaded_modules)} module(s) from mirai.tools.")
    await bot.warm_up()
    yield
    print("cleaning up cache...")
    await bot._set_model_keep_alive(bot.model_name, 0)

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/edge")
async def websocket_edge_endpoint(websocket: WebSocket):
    await websocket.accept()
    edge_name = "Unknown"
    
    try:
        auth_msg = await websocket.receive_json()
        if auth_msg.get("type") == "register":
            edge_name = auth_msg.get("edge_name", "Unknown_Edge")
            tools = auth_msg.get("tools", [])
            previous_websocket = ACTIVE_CONNECTIONS.get(edge_name)

            if previous_websocket is not None and previous_websocket is not websocket:
                print(f"[System] Edge device [{edge_name}] reconnected. Replacing the old socket.")
                await previous_websocket.close(code=1012, reason="Replaced by a newer connection")

            ACTIVE_CONNECTIONS[edge_name] = websocket
            EDGE_TOOLS_REGISTRY[edge_name] = {}

            for tool_schema in tools:
                original_name = tool_schema["function"]["name"]
                prefixed_name = f"edge_{edge_name}__{original_name}"
                schema_copy = deepcopy(tool_schema)
                schema_copy["function"]["name"] = prefixed_name
                EDGE_TOOLS_REGISTRY[edge_name][prefixed_name] = schema_copy

            print(f"[Edge Connected] Device [{edge_name}] is online with {len(tools)} mounted tools.")

            while True:
                data = await websocket.receive_json()
                if data.get("type") == "tool_result":
                    call_id = data.get("call_id")
                    result = data.get("result")

                    pending = PENDING_TOOL_CALLS.pop(call_id, None)
                    if pending:
                        future = pending["future"]
                        if not future.done():
                            future.set_result(result)

    except WebSocketDisconnect:
        print(f"[Edge Disconnected] Device [{edge_name}] went offline.")
        cleanup_edge_connection(edge_name, websocket)

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    async def generate():
        try:
            current_prompt = request.prompt
            ephemeral_messages = []

            while True:
                all_tools = get_all_tool_schemas()
                stream = bot.chat_stream(
                    prompt=current_prompt,
                    session_id=request.session_id,
                    tools=all_tools if all_tools else None,
                    ephemeral_messages=ephemeral_messages
                )

                tool_calls_to_process = None

                async for chunk in stream:
                    if chunk["type"] == "text":
                        yield stream_event("text", content=chunk["content"])
                    elif chunk["type"] == "tool_call":
                        tool_calls_to_process = chunk["tool_calls"]
                        break

                if not tool_calls_to_process:
                    break

                ephemeral_messages.append(
                    {"role": "assistant", "content": "", "tool_calls": tool_calls_to_process}
                )

                for tc in tool_calls_to_process:
                    func_name = tc["function"]["name"]

                    args = tc["function"]["arguments"]
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}

                    if func_name in TOOL_REGISTRY:
                        result = ""
                        try:
                            yield stream_event(
                                "tool_status",
                                status="running",
                                content=f"Running local tool '{func_name}'..."
                            )
                            result = await execute_registered_tool(func_name, args)
                            yield stream_event(
                                "tool_status",
                                status="success",
                                content=f"Local tool '{func_name}' finished successfully."
                            )
                        except Exception as e:
                            result = f"Error: Local tool execution failed: {e}"
                            yield stream_event(
                                "tool_status",
                                status="error",
                                content=f"Local tool '{func_name}' failed: {e}"
                            )

                        ephemeral_messages.append(
                            {"role": "tool", "content": str(result), "name": func_name}
                        )
                        continue

                    target_edge = None
                    original_tool_name = func_name
                    for ename in ACTIVE_CONNECTIONS:
                        prefix = f"edge_{ename}__"
                        if func_name.startswith(prefix):
                            target_edge = ename
                            original_tool_name = func_name[len(prefix):]
                            break

                    if not target_edge:
                        error_message = "Error: Device offline or tool not found."
                        ephemeral_messages.append(
                            {"role": "tool", "content": error_message, "name": func_name}
                        )
                        yield stream_event(
                            "tool_status",
                            status="error",
                            content=f"Tool '{func_name}' is unavailable because the target edge device is offline."
                        )
                        continue

                    ws = ACTIVE_CONNECTIONS.get(target_edge)
                    if ws is None:
                        error_message = "Error: Device offline or tool not found."
                        ephemeral_messages.append(
                            {"role": "tool", "content": error_message, "name": func_name}
                        )
                        yield stream_event(
                            "tool_status",
                            status="error",
                            content=f"Edge device '{target_edge}' went offline before tool execution started."
                        )
                        continue

                    call_id = str(uuid.uuid4())
                    loop = asyncio.get_running_loop()
                    future = loop.create_future()
                    PENDING_TOOL_CALLS[call_id] = {
                        "future": future,
                        "edge_name": target_edge,
                        "websocket": ws,
                    }

                    result = ""
                    try:
                        yield stream_event(
                            "tool_status",
                            status="running",
                            content=f"Calling '{original_tool_name}' on edge device '{target_edge}'..."
                        )

                        await ws.send_json({
                            "type": "tool_call",
                            "name": original_tool_name,
                            "arguments": args,
                            "call_id": call_id
                        })

                        result = await asyncio.wait_for(
                            future,
                            timeout=TOOL_CALL_TIMEOUT_SECONDS,
                        )

                        yield stream_event(
                            "tool_status",
                            status="success",
                            content=f"Tool '{original_tool_name}' finished on edge device '{target_edge}'."
                        )
                    except asyncio.TimeoutError:
                        result = "Error: Tool execution timed out."
                        yield stream_event(
                            "tool_status",
                            status="error",
                            content=f"Tool '{original_tool_name}' timed out on edge device '{target_edge}'."
                        )
                    except Exception as e:
                        result = f"Error: Tool execution failed: {e}"
                        yield stream_event(
                            "tool_status",
                            status="error",
                            content=f"Tool '{original_tool_name}' failed on edge device '{target_edge}': {e}"
                        )
                    finally:
                        PENDING_TOOL_CALLS.pop(call_id, None)

                    ephemeral_messages.append(
                        {"role": "tool", "content": str(result), "name": func_name}
                    )

                current_prompt = None

        except Exception as e:
            yield stream_event("error", content=f"Chat request failed: {e}")

    return StreamingResponse(generate(), media_type="application/x-ndjson")

@app.post("/clear")
async def clear_endpoint(session_id: str = "default"):
    bot.clear_memory(session_id)
    return {"status": "success", "message": f"Cleared memory for session: {session_id}"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)