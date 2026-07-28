from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm_extractor import ask_llm
from supabase_client import get_all_events

app = FastAPI()

# Allow React to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.4.43:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return {"message": "LifeLens API is running!"}


@app.post("/chat")
def chat(request: ChatRequest):
    events = get_all_events()
    answer = ask_llm(events, request.question)

    return {
        "answer": answer
    }


# NEW ENDPOINT
@app.get("/timeline")
def timeline():
    events = get_all_events()
    return events