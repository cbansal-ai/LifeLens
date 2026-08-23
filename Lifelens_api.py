from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpcore import request
from pydantic import BaseModel
from typing import Optional

from llm_extractor import ask_llm
from supabase_client import get_all_events
from fastapi import HTTPException 
from guardrails import validate_input
from agent import agent
from gmail_auth import authenticate_gmail

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
    account_email: Optional[str] = None


class ChangeUserRequest(BaseModel):
    email: str


@app.get("/")
def home():
    return {"message": "LifeLens API is running!"}


@app.post("/auth/change-user")
def change_user(request: ChangeUserRequest):
    """
    Validate the requested Gmail address, launch Google OAuth, and make sure
    the Google account selected by the user matches the email entered in LifeLens.
    """

    email = request.email.strip().lower()

    if not email:
        raise HTTPException(status_code=400, detail="Please enter a Gmail address.")

    if not email.endswith("@gmail.com"):
        raise HTTPException(
            status_code=400,
            detail="LifeLens currently supports Gmail accounts only.",
        )

    try:
        service = authenticate_gmail(
            expected_email=email,
            force_consent=True,
        )

        profile = service.users().getProfile(userId="me").execute()
        authenticated_email = profile["emailAddress"].strip().lower()

        return {
            "email": authenticated_email,
            "message": "Gmail account authenticated successfully.",
        }

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        logging.exception("Gmail OAuth failed")
        raise HTTPException(
            status_code=500,
            detail=f"Gmail authentication failed: {str(exc)}",
        )


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


@app.post("/agent")
def run_agent(request: ChatRequest):
    """Route the user's question through the LifeLens tool-calling agent."""

    logging.info(f"Agent question received: {request.question}")

    valid, message = validate_input(request.question)
    if not valid:
        logging.warning(message)
        raise HTTPException(
            status_code=400,
            detail=message,
        )

    # Include the active UI user in the agent context.
    user_content = request.question
    if request.account_email:
        user_content = (
            f"Active LifeLens user: {request.account_email}\n"
            f"Question: {request.question}"
        )

    try:
        logging.info(f"Invoking agent with user content: {user_content}")

        response = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": user_content,
                    }
                ]
            }
        )

        messages = response.get("messages", [])
        if not messages:
            raise RuntimeError("Agent returned no messages.")

        final_message = messages[-1]

        answer = getattr(final_message, "text", None)
        if callable(answer):
            answer = answer()

        if not answer:
            answer = getattr(final_message, "content", None)

        if isinstance(answer, list):
            answer = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in answer
            ).strip()

        if not answer:
            answer = str(final_message)

        logging.info("Agent answer returned successfully")

        return {
            "answer": answer,
            "tool": "Agent",
        }

    except Exception as exc:
        logging.exception("Agent execution failed")
        raise HTTPException(
            status_code=500,
            detail=f"LifeLens agent failed: {str(exc)}",
        )


# NEW ENDPOINT
@app.get("/timeline")
def timeline():
    events = get_all_events()
    return events


