from langchain.tools import tool
import logging 

@tool
def search_gmail(question: str) -> str:
    """Search Gmail for flights, bookings, reservations, and travel information."""
    logging.info("Gmail Tool selected")
    try:
        print("\n******** Gmail Tool Called ********\n")

        return "Flight found: United Airlines UA123 on Aug 10."
    except Exception:
        return "Sorry, I couldn't access your Gmail right now."

    
