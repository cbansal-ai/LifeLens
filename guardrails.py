
from typer import prompt

from constants import SUSPICIOUS_PHRASES

from llm_extractor import classify_question
import logging

def validate_input(question: str):

    if question is None:
        return False, "Question cannot be empty."

    question = question.strip()

    if not question:

        logging.warning("Empty question")

        return False, "Question cannot be empty."

    if len(question) > 500:
        logging.warning("Question too long")
        return False, "Question cannot exceed 500 characters."

    if any(
        phrase in question.lower()
        for phrase in SUSPICIOUS_PHRASES
    ):
        logging.warning("Prompt injection detected")
        return False, "Prompt injection attempt detected."

    
    result = True 
    message = '' 
    result, message = is_out_of_scope(question)
    if not result:

        return False, message
    
    return True, ""

def is_out_of_scope(question: str):
    prompt = f"""

You are an intent classifier.

Return ONLY one word:

YES

or

NO

Return YES if the question is asking about the user's own:

- emails

- calendar

- timeline

- documents

- purchases

- travel

- flight

- personal events

- personal information stored in LifeLens

Return NO for:

- general knowledge

- programming

- weather

- news

- recipes

- math

- coding

- anything unrelated to the user's stored data.

Question: {question}

"""
    try:
        response = classify_question(prompt).strip().upper()

        if response.startswith("YES"):

            return True, ""

        return False, "I can only answer questions about your personal data stored in LifeLens."
    except Exception as e:

        print(e)

        return False, "Unable to validate your request at the moment."