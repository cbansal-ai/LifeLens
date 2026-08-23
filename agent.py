from dotenv import load_dotenv
from langchain.agents import create_agent

from tools.pdf_tool import search_documents
from tools.timeline_tool import search_timeline

load_dotenv()

agent = create_agent(
    model="openai:gpt-4.1-mini",
    tools=[
        search_documents,
        search_timeline,
    ],
    system_prompt="""
You are LifeLens, a personal AI memory assistant.

Choose the most appropriate tool for each question.

Use search_timeline for questions about Gmail-derived personal events such as
travel, purchases, appointments, bookings, deliveries, or timeline history.
When calling search_timeline, pass the active LifeLens user email shown in the
conversation as account_email.

Use search_documents for questions about uploaded PDFs and document content.

If one tool is enough, do not call multiple tools.
If none of the tools can answer, say that you don't know.
""",
)


if __name__ == "__main__":
    question = input("Ask LifeLens: ")

    response = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": question,
                }
            ]
        }
    )

    print("\nAnswer")
    print("-" * 80)
    print(response["messages"][-1].text)
