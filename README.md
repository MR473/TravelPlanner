# TravelPilot.AI 🚀🌍
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
├── app.py
├── travel_agent.py
├── tools/
├── models/
├── logs/
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

## 🛠️ Installation

### Using uv
```
uv sync
uv venv
source .venv/bin/activate
```

### Using pip
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
python app.py
```

or

```
streamlit run app.py
```

---

## 📊 Tagging Example

```
[TOOLS] Found 12 museums near Asheville.
[AI] Here is your plan:
[ASSUMPTION] Assuming restaurants are open after 9 PM.
```

---

## 🧪 Research Mode
Supports:
- Multi-model comparison  
- Prompt evaluation  
- Temperature sweeps  
- JSON/human output separation  

---

## 🚀 Roadmap
- [ ] Add caching  
- [ ] Support more models  
- [ ] Add visual maps  
- [ ] Conversation memory  
- [ ] Cloud deployment  

---

## 🤝 Contributing
Pull requests are welcome.

---

## 📄 License
MIT License (optional - edit as needed)

---

## 🙌 Acknowledgements
- Geoapify API  
- LangChain & OpenAI  
