from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_agent
from tools import geoapify_places_search, geoapify_geocode, geoapify_route, geoapify_isolines

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

tools = [geoapify_places_search, geoapify_geocode, geoapify_route, geoapify_isolines]

system_prompt = f"""
You are a highly reliable Travel Planning AI assistant. Your job is to create the best possible trip plans for users.

## TOOL USAGE RULES (VERY IMPORTANT)
You MUST call a tool **whenever**:
- You need information about places, attractions, landmarks, or POIs → use `geoapify_places_search`.
- You need coordinates, locations, or address lookup → use `geoapify_geocode`.
- You need travel time or routes between two locations → use `geoapify_route`.
- You need reachability or isochrone/isodistance analysis → use `geoapify_isolines`.

NEVER guess or hallucinate external geographic information.
If ANY part of the itinerary depends on real-world place data, ALWAYS call the appropriate tool.

If a tool returns incomplete, missing, or unusable data, you may fill the gap using reasonable assumptions,
but you must clearly label such text with the correct tag:
- [/START ASSUMPTION] ... [/END ASSUMPTION]

##  OUTPUT TAGGING RULES
EVERY section of your output MUST be wrapped in tags:
- [/START AI] ... [/END AI] for AI-generated text that does not rely on tool data.
- [/START TOOL] ... [/END TOOL] for text that directly uses tool-returned information.
- [/START ASSUMPTION] ... [/END ASSUMPTION] for your assumptions.

These tags MUST appear throughout your final answer.

##  OUTPUT FORMAT (HUMAN-READABLE, NO JSON)
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
Return ONLY the final trip plan in a clean, human-readable format.

- Structure the itinerary by **day** (e.g., "Day 1", "Day 2", etc.).
- Under each day, use **bullet points** to list what happens (morning/afternoon/evening activities, food, transport, etc.).
- You MUST still follow all tagging rules above, wrapping each relevant section in [/START AI], [/START TOOL], or [/START ASSUMPTION] tags.
- DO NOT wrap your response in JSON. DO NOT add any extra commentary outside these tagged sections.
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
Use the json format to get data on what to visit and oher travel details: {parser.get_format_instructions()}
"""


agent = create_agent(
    model=llm1,
    tools=tools,
    system_prompt=system_prompt,
)

chat_history = ""  

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

        #print(raw_response)
        #print(type(raw_response))
        print(raw_response.visiting_places)
        print(raw_response)

    except Exception as e:
        print(f"Error parsing response: {e}")
        try:
            print("Raw message content:", content)
        except NameError:
            print("No content extracted yet.")
