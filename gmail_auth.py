import base64
import json
from datetime import datetime

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from llm_extractor import extract_event, ask_llm
from supabase_client import save_event, get_events, get_all_events
from constants import icons

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]



def extract_body(payload):
    """Extract email body."""

    if "parts" in payload:
        data = payload["parts"][0]["body"].get("data")
    else:
        data = payload.get("body", {}).get("data")

    if not data:
        return ""

    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")


def authenticate_gmail(): # 11111 
    """Authenticate with Gmail."""

    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json",
        SCOPES,
    )

    creds = flow.run_local_server(port=0)

    return build("gmail", "v1", credentials=creds)


def fetch_emails(service):  # 2222 
    """Fetch Gmail messages."""

    profile = service.users().getProfile(userId="me").execute()
    account_email = profile["emailAddress"]

    results = (
        service.users()
        .messages()
        .list(
            userId="me",
            q="from:chhayaban@yahoo.com after:2026/07/21",
            maxResults=10,
        )
        .execute()
    )

    messages = results.get("messages", [])

    return account_email, messages


def process_emails(service, account_email, messages): # 3333 
    """Extract events and save them to Supabase."""

    if not messages:
        print("No emails found.")
        return

    print(f"Found {len(messages)} emails.\n")

    with open("emails.txt", "w", encoding="utf-8") as f:

        for message in messages:

            msg = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message["id"],
                    format="full",
                )
                .execute()
            )

            payload = msg["payload"]
            headers = payload["headers"]

            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"),
                "",
            )

            sender = next(
                (h["value"] for h in headers if h["name"] == "From"),
                "",
            )

            date = next(
                (h["value"] for h in headers if h["name"] == "Date"),
                "",
            )

            body = extract_body(payload)

            result = extract_event(subject, body)
            result = json.loads(result)

            success = save_event(account_email, result)

            if success:
                print("Saved successfully")
            else:
                print("Failed to save")

            f.write("=" * 60 + "\n")
            f.write(f"account_email: {account_email}\n")
            f.write(f"From: {sender}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Date: {date}\n\n")
            f.write(body)
            f.write(f"\n\nExtracted Event:\n{result}\n\n")

    print("\nDone! Emails saved to emails.txt")


def display_timeline():  # 4444
    """Display event timeline."""

    events = get_events()

    print("\nTimeline")
    print("-" * 40)

    for event in events:
        dt = datetime.fromisoformat(event["event_date"])
        formatted_date = dt.strftime("%b %d, %Y %I:%M %p")
        icon = icons.get(event["event_type"], "📅")

        print(f"{icon} {formatted_date} | {event['title']}")


def chat():  # 5555
    """Simple chat interface."""

    events = get_all_events()
    print(events)
    while True:
        question = input("\nAsk a question (type 'exit' to quit): ")

        if question.lower() == "exit":
            break

        answer = ask_llm(events, question)

        print(f"\nAI: {answer}")


if __name__ == "__main__":

    # Uncomment these when you want to process Gmail again.
    
    service = authenticate_gmail()
    account_email, messages = fetch_emails(service)
    process_emails(service, account_email, messages)

    display_timeline()

    chat()