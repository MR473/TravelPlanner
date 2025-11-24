# TravelPilot.AI 
### *Your AI-powered travel planning assistant*

TravelPilot.AI is an intelligent travel-planning platform that uses **LLMs, LangChain, and Geoapify** to automatically design optimized itineraries, perform real-time tool-based place lookups, and produce structured travel plans with full transparency and traceability.

It includes:
- A **tool-aware LLM agent**
- A strict **tagging framework** (AI / TOOLS / ASSUMPTIONS)
- A validated **Pydantic travel schema**
- Integrated **Chat UI**

---

## 🚀 Features

### ✅ AI-Generated Itineraries
Automatically create customized multi-day travel plans based on destination, budget, preferences, and interests.

### ✅ Tool-Integrated Reasoning
The LLM **must** call Geoapify tools for:
- Geocoding  
- Place search  
- Routing  
- Isochrones

### ✅ Structured JSON Output
All final responses conform to a strict **Pydantic schema**.

### ✅ Tagging System
| Tag | Meaning |
|------|----------|
| **[AI]** | Pure model reasoning |
| **[TOOLS]** | Data retrieved via Geoapify |
| **[ASSUMPTION]** | Model-added data when information is missing |

---

## 🏗️ Project Structure

```
TravelPilot.AI/
│
├── main.py (main branch: GPT-5, ollama branch: gpt-oss & llama3.2:3b)
├── tools.py
├── mapping.py
├── .env (should be added)
├── requirements.txt
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## ⚙️ How It Works
1. User enters travel details  
2. System enforces tool rules  
3. Geoapify tools fetch real-world data  
4. LLM merges everything into JSON + narrative  
5. UI displays output with logs  

---

## 🛠️ Installation & Setup
### 🔧 1. Creating a Virtual Environment (non-`uv` users)

If you're **not using [`uv`](https://astral.sh/uv)**, you can still create a virtual environment using built-in Python tools.

#### 🖥️ For macOS/Linux:
```bash
python3 -m venv .venv
```

#### 🪟 For Windows:
```cmd
python -m venv .venv
```

This will create a `.venv/` directory in your project folder.

---

### ▶️ 1.1. Activating the Environment

Once created, activate the environment using the following command based on your OS and terminal:

#### 🖥️ On macOS/Linux:
```bash
source .venv/bin/activate
```

#### 🪟 On Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

#### 🪟 On Windows CMD:
```cmd
.venv\Scripts\activate
```

Once activated, you'll see `.venv` in your terminal prompt. You can then install dependencies using:

```bash
pip install -r requirements.txt
```

> Or, if you're using `uv`, simply run:
```bash
uv pip sync
```


### 2. Using uv
```
uv sync
uv venv
source .venv/bin/activate
```

### 3. Using pip without venv
```
pip install -r requirements.txt
```

---

## 🔑 Environment Variables

Create a `.env` file:

```
OPENAI_API_KEY=your_key
GEOAPIFY_API_KEY=your_key
```

---

## ▶️ Run the App

```
python main.py
```

---

## 📊 Tagging Example

```
[/START TOOLS] Found 12 museums near Asheville. [/END TOOL]
[/START AI] Here is your plan:[/END AI]
[/START ASSUMPTION] Assuming restaurants are open after 9 PM.[/END ASSUMPTION]
```

## 🙌 Acknowledgements
- Geoapify API  
- LangChain & OpenAI  & Ollama
