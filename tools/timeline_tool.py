from langchain.tools import tool
import logging 

@tool
def search_timeline(question: str) -> str:
    """Search the LifeLens timeline and answer the user's question."""
    logging.info("Timeline Tool selected")
    try:
        return "Searching Timeline..."
    except Exception:
        return "Sorry, I couldn't display the timeline right now."
