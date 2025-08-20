# QueryX: AI-Powered Text-to-SQL Conversion


QueryX is an AI-based tool that allows users to interact with CSV datasets using natural language queries. Built with **Gemini 1.5 Pro**, **Streamlit**, and **SQLite**, it translates plain English into executable SQL queries and displays accurate results—perfect for non-technical users or data analysts.

---

## 🚀 Features

* 🧠 **Natural Language to SQL**
  Translate user input into SQL using Gemini 1.5 Pro's LLM capabilities.

* 📊 **CSV Dataset Support**
  Upload and query your own CSV files directly from the UI.

* 🛠️ **Regex-Based Query Cleaning**
  Preprocess natural language queries for improved SQL accuracy.

* 🔄 **Error Handling**
  Robust handling of SQL errors and malformed queries.

* 🧾 **Lightweight Backend**
  SQLite database engine for seamless integration and quick data operations.

---

## 📸 Demo

<img width="2870" height="1519" alt="Screenshot 2025-07-29 212058" src="https://github.com/user-attachments/assets/6661c643-51ec-4019-8d16-43222b1be1b1" />
<img width="2879" height="1517" alt="Screenshot 2025-07-29 212125" src="https://github.com/user-attachments/assets/b68b7f23-e94d-4c3f-bebe-84c698eac675" />

---

## 🧰 Tech Stack

* **Frontend:** Streamlit
* **AI Model:** Gemini 1.5 Pro (via API)
* **Database:** SQLite
* **Backend:** Python
* **Others:** Pandas, Regex, Prompt Engineering

---

## 🔧 How to Run

```bash
# 1. Clone the repository
git clone https://github.com/abhinavyy/QueryX.git


# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

> 🔑 Ensure you have API access to Gemini 1.5 Pro and set the key in a `.env` file.

---

## 📁 Folder Structure

```
queryx-ai/
│
├── app.py               # Streamlit app
├── data/                # Uploaded CSVs
├── .env                 # API key (not tracked)
└── README.md
```

---

## ✨ Future Scope

* Voice-to-query support
* Integration with PostgreSQL and MySQL
* Result visualizations (bar chart, pie chart, etc.)
* Multi-table joins

---

