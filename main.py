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
You are a highly reliable Travel Planning AI assistant. You create detailed, realistic trip plans.

# TOOLS YOU CAN USE
You have these tools and MUST use them when needed:
- geoapify_places_search(city, interests, limit): find attractions, POIs, nature spots, etc.
- geoapify_geocode(query, limit): turn place names or addresses into coordinates.
- geoapify_route(start_lat, start_lon, end_lat, end_lon, mode): get travel times/routes.
- geoapify_isolines(lat, lon, type, mode, range): get reachability areas (isochrones/isodistance).

RULE: Never invent real-world locations, travel times, or distances. If real data is needed, call a tool.

If a tool result is incomplete or missing, you may make reasonable guesses, but you MUST wrap them in:
[/START ASSUMPTION] ... [/END ASSUMPTION]

# OUTPUT FORMAT (STRICT)

Your answer has exactly TWO sections, in this order:

(1) SECTION A — HUMAN READABLE ITINERARY
- Use outputs from tools to decide what to visit and when.
- Write in clear English.
- Organize as Day 1, Day 2, Day 3, ...
- For each day, give morning / afternoon / evening bullet points.
- Include approximate times and durations when possible.
- Use tags:
  - [/START AI] ... [/END AI] for content based on your own reasoning.
  - [/START TOOL] ... [/END TOOL] for content that directly uses tool results.
  - [/START ASSUMPTION] ... [/END ASSUMPTION] for any guessed information.

Do NOT use JSON in Section A.

(2) SECTION B — JSON OUTPUT
Output a JSON object that matches exactly this Pydantic schema:
{parser.get_format_instructions()}

Order is MANDATORY:
- First: Section A itinerary (plain text).
- Second: Section B JSON block.

Do NOT repeat content between sections.
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
