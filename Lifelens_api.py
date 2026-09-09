import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from gmail_auth import authenticate_gmail
from guardrails import validate_input
from llm_extractor import ask_llm
from orchestrator import ask_lifelens
from rag.ingest import index_pdf
from supabase_client import get_all_events

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = BASE_DIR / "rag" / "documents"
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024

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


@app.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    account_email: str = Query(..., min_length=1),
):
    """Validate, save, and index a PDF for the active LifeLens user."""
    filename = Path(file.filename or "").name
    user_id = account_email.strip().lower()

    if not filename or not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    if not user_id:
        raise HTTPException(status_code=400, detail="An active Gmail account is required.")

    contents = await file.read()

    if not contents.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid PDF.",
        )

    if len(contents) > MAX_PDF_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="PDF must be 10 MB or smaller.",
        )

    destination = DOCUMENTS_DIR / filename

    try:
        destination.write_bytes(contents)

        result = index_pdf(
            destination,
            user_id=user_id,
        )

        return {
            **result,
            "message": result.get("message", "PDF processed successfully."),
        }

    except Exception as exc:
        logging.exception("PDF upload/indexing failed")

        if destination.exists():
            destination.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail=f"Could not index the uploaded PDF: {str(exc)}",
        ) from exc

    finally:
        await file.close()


@app.post("/chat")
def chat(request: ChatRequest):
    """
    Legacy/direct endpoint for Gmail-derived timeline questions only.
    Kept so existing timeline behavior continues to work.
    """
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

    account_email = request.account_email.strip().lower()
    events = get_all_events(account_email)
    answer = ask_llm(events, request.question)

    logging.info("Timeline answer returned successfully")
    return {"answer": answer}


@app.post("/agent")
def run_agent(request: ChatRequest):
    """
    Main LifeLens orchestrator endpoint.

    Routes among:
    - Gmail-derived timeline data
    - PDF RAG
    - Business Text-to-SQL
    - combinations of those sources
    """
    logging.info("Orchestrator question received")

    valid, message = validate_input(request.question)
    if not valid:
        logging.warning(message)
        raise HTTPException(status_code=400, detail=message)

    if not request.account_email:
        raise HTTPException(
            status_code=400,
            detail="An active Gmail account is required.",
        )

    account_email = request.account_email.strip().lower()

    try:
        result = ask_lifelens(
            account_email=account_email,
            question=request.question,
        )

        logging.info(
            "Orchestrator answer returned successfully | sources=%s",
            result["sources"],
        )

        return result

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        logging.exception("LifeLens orchestration failed")
        raise HTTPException(
            status_code=500,
            detail=f"LifeLens orchestration failed: {str(exc)}",
        ) from exc


@app.get("/timeline")
def timeline(account_email: str = Query(..., min_length=1)):
    """Return Gmail-derived timeline events for the active user only."""
    return get_all_events(account_email.strip().lower())
