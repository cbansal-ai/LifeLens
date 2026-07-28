import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Create a Supabase Client object and store it in the 'supabase' variable
supabase: Client = create_client(url, key)

def save_event(account_email, event):
    response = (
        supabase
        .table("events")
        .insert({

            "account_email": account_email,

            "company": event["company"],

            "event_type": event["event_type"],

            "title": event["title"],

            "event_date": event["event_date"],

            "summary": event["summary"],

            "raw_json": event

        })

        .execute()

    )

    return response

def get_events():
    response = (
        supabase
        .table("events")
        .select("event_date, title, event_type")
        .order("event_date")
        .execute()
    )

    return response.data

def get_all_events():
    response = (
        supabase
        .table("events")
        .select("*")
        .limit(2)  
        .execute()
    )

    return response.data



if __name__ == "__main__":

    events = get_all_events()
    for event in events:
        print(event)
