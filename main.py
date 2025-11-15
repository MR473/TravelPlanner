from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser


load_dotenv()

class TravelPlanner(BaseModel):
    destination: str
    duration_days: int
    budget_usd: float
    visiting_places: list[str]
    comments: str

llm1 = ChatOpenAI(model='gpt-5')
parser = PydanticOutputParser(pydantic_object=TravelPlanner)

prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system", 
            """
            You are a travel planning assistant. You have 10 years of experience planning the best trips for any tourist. You can plan trips anywhere in the world.
            Your goal is to help tourists find the best places to visit based on their preferences, constraints and time of year.
            If any information is missing, make valid assumptions and let the user know about your assumptions.
            Wrap the output in this format and provide no other text:{format_instructions}
            """
        ),
        ("placeholder", "{chat_history}"),
        ("human", "{query}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
).partial(format_instructions=parser.get_format_instructions())

agent_chain = prompt | llm1 | parser

chat_history = ""

print("Travel planner ready. Type your question, or 'exit' to quit.\n")

while True:
    user_query = input(">>> ").strip()
    if user_query.lower() in {"exit", "quit", "q"}:
        print("Goodbye!")
        break

    try:
        raw_response = agent_chain.invoke(
            {
                "query": user_query,
                "chat_history": chat_history,
                "agent_scratchpad": "",
            }
        )

        print(raw_response)
        print(type(raw_response))
        print(raw_response.visiting_places)

    except Exception as e:
        print(f"Error parsing response: {e}, raw response: {raw_response}")