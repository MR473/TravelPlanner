from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_agent
from tools import opentripmap_search_tool

from langchain_core.callbacks import BaseCallbackHandler

load_dotenv()

class TravelPlanner(BaseModel):
    destination: str
    duration_days: int
    budget_usd: float
    visiting_places: list[str]
    comments: str

class ToolLoggingHandler(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, **kwargs):
        name = serialized.get("name", "unknown_tool")
        print(f"\n[TOOL START] {name} | args={input_str}")

    def on_tool_end(self, output, **kwargs):
        out = str(output)
        if len(out) > 300:
            out = out[:300] + " ...[truncated]"
        print(f"[TOOL END] output={out}\n")

llm1 = ChatOpenAI(model="gpt-5", temperature=0)
parser = PydanticOutputParser(pydantic_object=TravelPlanner)

tools = [opentripmap_search_tool]

system_prompt = f"""
You are a travel planning assistant. You have 10 years of experience planning the best trips for any tourist. You can plan trips anywhere in the world.
Your goal is to help tourists find the best places to visit based on their preferences, constraints and time of year.
You MAY call tools like `opentripmap_search_tool` to look up attractions and POIs.
If any information is missing, make valid assumptions and let the user know about your assumptions.
Return ONLY the following JSON object, no extra commentary, and no backticks:
{parser.get_format_instructions()}
"""

agent = create_agent(
    model=llm1,
    tools=tools,
    system_prompt=system_prompt,
)

chat_history = ""  # kept just so your structure is similar, though not used here

print("Travel planner (create_agent) ready. Type your question, or 'exit' to quit.\n")

while True:
    user_query = input(">>> ").strip()
    if user_query.lower() in {"exit", "quit", "q"}:
        print("Goodbye!")
        break

    try:
        # create_agent expects "messages" as input
        handler = ToolLoggingHandler()
        msg = agent.invoke(
            {
                "messages": [
                    {"role": "user", "content": user_query}
                ]
            },
            config={"callbacks": [handler], "run_name": "TravelPlannerAgent"}
        )

        # msg can be a dict with "messages" or a single message; handle both
        if isinstance(msg, dict) and "messages" in msg:
            content = msg["messages"][-1].content
        else:
            content = msg.content

        raw_response = parser.parse(content)

        print(raw_response)
        print(type(raw_response))
        print(raw_response.visiting_places)

    except Exception as e:
        print(f"Error parsing response: {e}")
        try:
            print("Raw message content:", content)
        except NameError:
            print("No content extracted yet.")
