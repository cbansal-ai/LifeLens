from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpcore import request
from pydantic import BaseModel

from llm_extractor import ask_llm
from supabase_client import get_all_events
from fastapi import HTTPException 
from guardrails import validate_input

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

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

    logging.info(f"Question received: {request.question}")

    valid, message = validate_input(request.question)

    if not valid:
        logging.warning(message)

        raise HTTPException(
            status_code=400,
            detail=message,
        )

    events = get_all_events()

    answer = ask_llm(events, request.question)

    logging.info("Answer returned successfully")

    return {
        "answer": answer
    }


# NEW ENDPOINT
@app.get("/timeline")
def timeline():
    events = get_all_events()
    return events


