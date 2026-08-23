import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import agent
from gmail_auth import authenticate_gmail
from guardrails import validate_input
from llm_extractor import ask_llm
from supabase_client import get_all_events

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

app = FastAPI()

# Allow the local React UI to communicate with FastAPI.
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
    """Authenticate the requested Gmail account and verify the selected user."""
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        logging.exception("Gmail OAuth failed")
        raise HTTPException(
            status_code=500,
            detail=f"Gmail authentication failed: {str(exc)}",
        ) from exc


@app.post("/chat")
def chat(request: ChatRequest):
    """Answer a question using Gmail-derived events for the active user."""
    logging.info("Timeline question received")

    valid, message = validate_input(request.question)
    if not valid:
        logging.warning(message)
        raise HTTPException(status_code=400, detail=message)

    if not request.account_email:
        raise HTTPException(
            status_code=400,
            detail="An active Gmail account is required to search the timeline.",
        )

    events = get_all_events(request.account_email)
    answer = ask_llm(events, request.question)

    logging.info("Timeline answer returned successfully")
    return {"answer": answer}


def _extract_tool_name(messages):
    """Return the most recently used LangChain tool name, when available."""
    for message in reversed(messages):
        if getattr(message, "type", None) == "tool":
            tool_name = getattr(message, "name", None)
            if tool_name:
                return tool_name

        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            last_call = tool_calls[-1]
            if isinstance(last_call, dict):
                return last_call.get("name")
            return getattr(last_call, "name", None)

    return None


@app.post("/agent")
def run_agent(request: ChatRequest):
    """Route the user's question through the LifeLens tool-calling agent."""
    logging.info("Agent question received")

    valid, message = validate_input(request.question)
    if not valid:
        logging.warning(message)
        raise HTTPException(status_code=400, detail=message)

    user_content = request.question
    if request.account_email:
        user_content = (
            f"Active LifeLens user: {request.account_email}\n"
            f"Question: {request.question}"
        )

    try:
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

        selected_tool = _extract_tool_name(messages)
        logging.info("Agent answer returned successfully")

        return {
            "answer": answer,
            "tool": selected_tool or "Agent",
        }

    except Exception as exc:
        logging.exception("Agent execution failed")
        raise HTTPException(
            status_code=500,
            detail=f"LifeLens agent failed: {str(exc)}",
        ) from exc


@app.get("/timeline")
def timeline(account_email: str = Query(..., min_length=1)):
    """Return Gmail-derived timeline events for the active user only."""
    return get_all_events(account_email)
