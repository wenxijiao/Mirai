import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from mirai.core.chatbot import MiraiBot

class ChatRequest(BaseModel):
    prompt: str
    session_id: str = "default"

# bot = MiraiBot(model_name='sorc/qwen3.5-instruct-uncensored:latest', think=False)
bot = MiraiBot(model_name='qwen3.5:0.8b', think=False)

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