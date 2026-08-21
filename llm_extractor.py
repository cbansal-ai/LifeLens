import json
import os
from urllib import response

from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Create OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def classify_question(prompt):
    response = client.responses.create(
        model="gpt-5",
        input=prompt
    )
    return response.output_text

def ask_llm(events, question):
    prompt = f"""
You are a helpful personal assistant.
Use ONLY the events below to answer the user's question.
If the answer is not in the events, say you don't know.
Events: {events}
Question: {question}
""" 
    response = client.responses.create(
        model="gpt-5",
        input=prompt
    )
    return response.output_text

# Extract event information from email
def extract_event(subject, body):
    prompt = f"""
You are an AI assistant that extracts structured event information from emails.
Return ONLY a valid JSON object.
Email Subject:
{subject}
Email Body:
{body}
Return the following required fields:
{{
    "company": "",
    "event_type": "",
    "title": "",
    "event_date": "",
    "summary": ""
}}

If the email contains additional useful information, add it as additional JSON fields.
Examples include:
- tracking_number
- confirmation_number
- airline
- hotel_name
- reservation_id
- status
- destination
- gate
- seat
- doctor_name

Do not invent information. Only include additional fields that are present in the email.
"""     
    response = client.responses.create(
        model="gpt-5",
        input=prompt
    )
    return response.output_text

if __name__ == "__main__":

    subject = "Expedia flight purchase confirmation - Munich, Germany - Fri, May 23"

    body = """
Thank you for your reservation.
Your flight to Munich is confirmed.
Confirmation Number: 73077161731095
"""
    result = extract_event(subject, body)
    print(result)

