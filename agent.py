from dotenv import load_dotenv

from langchain.agents import create_agent

from tools.pdf_tool import search_documents
from tools.timeline_tool import search_timeline

load_dotenv()

# -------------------------
# Create Agent
# -------------------------

agent = create_agent(
    model="openai:gpt-4.1-mini",
    tools=[
        search_documents,
        search_timeline,
    ],
    system_prompt="""
You are LifeLens.

You are a personal AI assistant.

Always choose the most appropriate tool.

If one tool is enough,
do not call multiple tools.

If none of the tools can answer,
reply that you don't know.
""",
)

# -------------------------
# Test
# -------------------------

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

    # Print the final AI response
    print("\nAnswer")
    print("-" * 80)
    print(response["messages"][-1].text)
    
