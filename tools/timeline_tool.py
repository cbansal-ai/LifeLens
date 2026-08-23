from langchain.tools import tool
import json
import logging
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

CHAT_API_URL = "http://127.0.0.1:8000/chat"


@tool
def search_timeline(question: str) -> str:
    """
    Search Gmail-derived LifeLens events that are already stored in the
    timeline database. The tool calls the existing FastAPI /chat endpoint,
    which reads the saved events and uses the LLM to answer the question.
    """
    logging.info("Timeline Tool selected")

    payload = json.dumps({
        "question": question
    }).encode("utf-8")

    req = urllib_request.Request(
        CHAT_API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("answer", "No answer was returned from the timeline.")

    except HTTPError as exc:
        logging.exception("Timeline /chat request returned an HTTP error")
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
            return error_body.get("detail", "Timeline search failed.")
        except Exception:
            return "Timeline search failed."

    except (URLError, TimeoutError):
        logging.exception("Timeline /chat request failed")
        return "Sorry, I couldn't search the saved Gmail events right now."

    except Exception:
        logging.exception("Unexpected timeline tool error")
        return "Sorry, I couldn't search the timeline right now."
