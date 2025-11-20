from dotenv import load_dotenv
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.output_parsers import PydanticOutputParser
from langchain.agents import create_agent
from tools import geoapify_places_search, geoapify_geocode, geoapify_route, geoapify_isolines

import time
from langchain_core.callbacks import BaseCallbackHandler

load_dotenv()


class TravelPlanner(BaseModel):
    destination: str
    duration_days: int
    budget_set: float
    budget_needed: float
    visiting_places: list[str]
    travel_mode: list[str]
    travel_time: list[int]
    travel_distance: list[int]
    comments: str


class ToolLoggingHandler(BaseCallbackHandler):
    def __init__(self):
        # How many tools are currently running in this agent invocation
        self.active_tools = 0

        # For tracking cumulative tool time (sum of all tool calls)
        self.cumulative_tool_time = 0.0

        # Stack of start times for tools (in case calls overlap / nest)
        self._tool_start_times: list[float] = []

        # Optional: for wall-clock phase timing (first start → last end)
        self.tools_phase_start = None
        self.tools_phase_end = None

    def on_tool_start(self, serialized, input_str, **kwargs):
        name = serialized.get("name", "unknown_tool")
        now = time.perf_counter()

        if self.active_tools == 0:
            # first tool in this run → mark phase start
            self.tools_phase_start = now

        self.active_tools += 1
        self._tool_start_times.append(now)

        print(f"\n[TOOL START] {name} | args={input_str}")

    def on_tool_end(self, output, **kwargs):
        now = time.perf_counter()

        # Pop matching start time and compute this tool's duration
        if self._tool_start_times:
            start_time = self._tool_start_times.pop()
            duration = now - start_time
            self.cumulative_tool_time += duration
            print(f"[TOOLS] This tool call took: {duration:.3f} seconds")
        else:
            print("[TOOLS] Warning: on_tool_end called without matching start time")

        out = str(output)
        if len(out) > 300:
            out = out[:300] + " ...[truncated]"
        print(f"[TOOL END] output={out}\n")

        self.active_tools -= 1

        # If this was the last active tool, close the phase and print totals
        if self.active_tools == 0 and self.tools_phase_start is not None:
            self.tools_phase_end = now
            phase_wall_clock = self.tools_phase_end - self.tools_phase_start

            print(f"[TOOLS] CUMULATIVE tool time (sum of all tool calls): "
                  f"{self.cumulative_tool_time:.3f} seconds")
            print(f"[TOOLS] Wall-clock tool phase (first start → last end): "
                  f"{phase_wall_clock:.3f} seconds")

    # Optional: see when LLM starts after tools
    def on_llm_start(self, *args, **kwargs):
        llm_start = time.perf_counter()
        if self.tools_phase_end is not None:
            gap = llm_start - self.tools_phase_end
            print(f"[TIMING] Gap between last tool finish and LLM start: {gap:.3f} seconds")




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
What to visit and other travel details.
This section must:
- The budget set vs the budget that would be needed (it can go over the budget)
- Be written in clear, readable English.
- Structure the trip by **Day 1, Day 2, Day 3, …**
- Include bullet points for morning / afternoon / evening.
- Include specific times: when to arrive, how long to stay, travel duration.
- Use these tags inside the text:
  - [/START AI] ... [/END AI] for general reasoning or text NOT relying on tools.
  - [/START TOOL] ... [/END TOOL] for text that uses tool-returned information.
  - [/START ASSUMPTION] ... [/END ASSUMPTION] when making assumptions.

**Do NOT use JSON inside section A.**

(2) **SECTION B — JSON OUTPUT**
WRAP the information in a JSON object containing **ONLY** the fields required by the Pydantic model: {parser.get_format_instructions()}
specific instructions when following the json format:
- budget_set: user input of budget
- budget_needed: the models final expectation of budget. It can be higher
- travel_time: time taken to travel between the places 
- travel_distance: the distance travelled between places
Rest are basic information you should fill.
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
        overall_start = time.perf_counter()
        msg = agent.invoke(
            {
                "messages": messages
            },
            config={"callbacks": [handler], "run_name": "TravelPlannerAgent"}
        )
        overall_end = time.perf_counter()
        total_latency = overall_end - overall_start

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
        print(f"[LATENCY] Total time from invoke() to final response: {total_latency:.3f} seconds\n")

    except Exception as e:
        overall_end = time.perf_counter()
        print(f"Error parsing response: {e}")
        try:
            print("Raw message content:", content)
        except NameError:
            print("No content extracted yet.")
        finally:
            # still useful to log total time even on error
            total_latency = overall_end - overall_start
            print(f"[LATENCY] Total time from invoke(): {total_latency:.3f} seconds\n")
