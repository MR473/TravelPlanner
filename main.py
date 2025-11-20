from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_ollama import ChatOllama
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
    days_per_place: dict[str, int]
    travel_mode: list[str]
    travel_time: list[str]
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


llm1 = ChatOllama(model="llama3.2:3b", temperature=0)
parser = PydanticOutputParser(pydantic_object=TravelPlanner)

tools = [geoapify_places_search, geoapify_geocode, geoapify_route, geoapify_isolines]

system_prompt = f"""
You are a highly reliable Travel Planning AI assistant. Your job is to create the best possible trip plans for users.

#  TOOL USAGE RULES (CRITICAL)
You MUST call a tool **whenever**:
- You need information about places, attractions, landmarks, or POIs → use `geoapify_places_search`.
- You need coordinates, geocoding, or address lookup → use `geoapify_geocode`.
- You need travel times or routing between two locations → use `geoapify_route`.
- You need reachability, isochrone, or isodistance analysis → use `geoapify_isolines`.

Absolutely NEVER hallucinate geographic or location-specific information.
If ANY part of the plan requires real-world place data, you MUST call the appropriate tool.

If a tool returns incomplete or missing data, you may fill gaps with reasonable assumptions,
but you must wrap such assumptions inside:
[/START ASSUMPTION] ... [/END ASSUMPTION]

#  OUTPUT TAGGING RULES AND FORMAT
Your final answer MUST contain only TWO sections:

(1) **SECTION A — HUMAN READABLE ITINERARY**
Use the json format to get data on what to visit and other travel details.
This section must:
- Be written in clear, readable English.
- Structure the trip by **Day 1, Day 2, Day 3, …**
- Include bullet points for morning / afternoon / evening.
- Include specific times: when to arrive, how long to stay, travel duration.
- Use these tags inside the text:
  - [/START AI] ... [/END AI] for general reasoning or text NOT relying on tools.
  - [/START TOOL] ... [/END TOOL] for text that uses tool-returned information.
  - [/START ASSUMPTION] ... [/END ASSUMPTION] when making assumptions.

**Do NOT use JSON inside section A.**
**Do NOT break format.**
**Do NOT REPEAT CONTENT.**

(2) **SECTION B — JSON OUTPUT**
WRAP the information in a JSON object containing **ONLY** the fields required by the Pydantic model: {parser.get_format_instructions()}

!!! MANDATORY ORDER (STRICT) !!!
You MUST output the itinerary FIRST.
After the full itinerary, output a JSON block SECOND.

If you reverse the order, the response will be rejected and you must correct it.
"""

agent = create_agent(
    model=llm1,
    tools=tools,
    system_prompt=system_prompt,
)

# ---- NEW: in-memory chat history (list of message dicts) ----
chat_history: list[dict] = []  # each item: {"role": "user" | "assistant", "content": str}

print("Travel planner (create_agent) ready. Type your question, or 'exit' to quit.\n")

while True:
    user_query = input(">>> ").strip()
    if user_query.lower() in {"exit", "quit", "q"}:
        print("Goodbye!")
        break

    # Build messages = previous history + current user message
    messages = chat_history + [
        {"role": "user", "content": user_query}
    ]

    try:
        # create_agent expects "messages" as input
        handler = ToolLoggingHandler()
        msg = agent.invoke(
            {
                "messages": messages
            },
            config={"callbacks": [handler], "run_name": "TravelPlannerAgent"}
        )

        # msg can be a dict with "messages" or a single message; handle both
        if isinstance(msg, dict) and "messages" in msg:
            content = msg["messages"][-1].content
        else:
            content = msg.content

        # ---- NEW: update chat history with this turn ----
        chat_history.append({"role": "user", "content": user_query})
        chat_history.append({"role": "assistant", "content": content})

        raw_response = parser.parse(content)

        print("RAW RESPONSE:", raw_response) 
        # print(raw_response.visiting_places)
        # print(raw_response.travel_mode)
        # print(raw_response.travel_time)
        print("CONTENT: ", content)

    except Exception as e:
        print(f"Error parsing response: {e}")
        try:
            print("Raw message content:", content)
        except NameError:
            print("No content extracted yet.")
