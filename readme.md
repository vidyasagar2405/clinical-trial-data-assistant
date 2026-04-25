# 🧠 Clinical Trial Data Assistant

An AI-powered assistant designed to analyze clinical trial data (SDTM domains) and retrieve supporting documents using MCP-based tool integration (Google Drive, Notion, Web Search).

---

## 🚀 Overview

This project builds an intelligent assistant that:

* Understands clinical queries
* Routes them to the correct tool using MCP (Model Context Protocol)
* Retrieves structured and unstructured clinical data
* Generates accurate, context-aware responses

---

## 🏗️ Architecture

```
User Query
    ↓
LLM (Tool Selection Logic)
    ↓
MCP Client
    ↓
Tools (Drive | Notion | SDTM | Web)
    ↓
Response Aggregation
    ↓
User Output
```

---

## 🧰 Features

* 🔍 SDTM Data Analysis (AE, DM, LB, CM, VS)
* 📄 Clinical document retrieval from Google Drive & Notion
* 🌐 Web search integration for external context
* ⚠️ Safety signal detection
* 🧠 Intelligent tool selection using LLM reasoning
* 📊 Patient-level summarization

---

## 📁 Project Structure

```
clinical-trial-data-assistant/
│
├── mcp_client/        # MCP client logic (tool calling interface)
├── mcp_servers/       # Tool implementations (Drive, Notion, etc.)
├── tools/             # Individual tool functions
├── trial_data/        # SDTM datasets (AE, DM, LB, CM, VS)
│
├── app.py             # Main Streamlit app
├── config.py          # Configuration settings
├── requirements.txt   # Dependencies
└── .gitignore
```

---

## ⚙️ Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-username/clinical-trial-data-assistant.git
cd clinical-trial-data-assistant
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file:

```
TRIAL_DATA_PATH=./trial_data
GROQ_API_KEY=your_key_here
GOOGLE_DRIVE_CREDENTIALS=path_to_json
NOTION_API_KEY=your_key_here
```

---

## ▶️ Run the Application

```bash
streamlit run app.py
```

---

## 🧠 MCP (Model Context Protocol)

This project uses MCP to:

* Standardize tool interfaces
* Enable dynamic tool selection
* Separate reasoning (LLM) from execution (tools)

---

## 📊 Example Queries

* "Show adverse events for patient 101"
* "Summarize patient history"
* "Fetch files from Drive"
* "Check safety signals in this trial"
* "Search latest diabetes trial guidelines"

---

## 🌍 Deployment

Deployed on **Streamlit Community Cloud**

👉 [Live Application](https://clinical-trial-data-assistant-75ws9gvdgbjzc5evbsfaub.streamlit.app)

---

## 🔮 Future Enhancements

* Multi-patient cohort analysis
* Visualization dashboards
* Advanced RAG with vector DB
* Real-time clinical alerts

---

## 🙌 Author

**Vidya Sagar**

---

## 📜 License

This project is for educational and demonstration purposes.
