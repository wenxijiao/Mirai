import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from copy import deepcopy
from mirai.core.chatbot import MiraiBot
from mirai.core.chatbot import ChatRequest

bot = MiraiBot(model_name='qwen3.5:0.8b', think=False)

ACTIVE_CONNECTIONS = {}
EDGE_TOOLS_REGISTRY = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
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
        # Receive the first message after connect for registration.
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

            # Prefix edge tool names to avoid cross-device collisions.
            for tool_schema in tools:
                original_name = tool_schema["function"]["name"]
                prefixed_name = f"edge_{edge_name}__{original_name}"
                
                schema_copy = deepcopy(tool_schema)
                schema_copy["function"]["name"] = prefixed_name
                EDGE_TOOLS_REGISTRY[edge_name][prefixed_name] = schema_copy

            print(f"[Edge Connected] Device [{edge_name}] is online with {len(tools)} mounted tools.")

            # Keep the socket open and listen for follow-up messages.
            while True:
                data = await websocket.receive_json()
                print(f"[Message from {edge_name}] {data}")
                # TODO: Handle tool execution results and wake the waiting LLM flow.

    except WebSocketDisconnect:
        print(f"[Edge Disconnected] Device [{edge_name}] went offline.")
        if ACTIVE_CONNECTIONS.get(edge_name) is websocket:
            del ACTIVE_CONNECTIONS[edge_name]
        if ACTIVE_CONNECTIONS.get(edge_name) is None and edge_name in EDGE_TOOLS_REGISTRY:
            del EDGE_TOOLS_REGISTRY[edge_name]
            print(f"[Cleanup] Cleared in-memory tool cache for [{edge_name}].")

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        bot.chat_stream(request.prompt, request.session_id), 
        media_type="text/plain"
    )

@app.post("/clear")
async def clear_endpoint(session_id: str = "default"):
    bot.clear_memory(session_id)
    return {"status": "success", "message": f"Cleared memory for session: {session_id}"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)