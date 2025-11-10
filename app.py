# ===============================================
# Update: Google API Key Handling (Security Patch)
# -----------------------------------------------
# Previously, the Google Gemini API key was hardcoded
# directly inside the script, which exposed the key
# publicly and risked unauthorized usage.
#
# This update removes the hardcoded key and loads it
# securely from a local `.env` file using python-dotenv.
#
# Key improvements:
#   • API key is now stored in `.env` and excluded via .gitignore
#   • Prevents accidental exposure in GitHub or deployments
#   • Enables safer and scalable deployment on Streamlit Cloud
#
# Environment variable used:
#   GEMINI_API_KEY=<your_api_key>
# ===============================================
import streamlit as st
import pandas as pd
import sqlite3
import google.generativeai as genai
import re
from dotenv import load_dotenv
import os

# Load API key from .env
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=API_KEY)

def clean_sql_query(sql_query):
    sql_query = re.sub(r'```sql|```', '', sql_query).strip()
    if ";" in sql_query:
        sql_query = sql_query.split(";")[0]
    return sql_query

st.set_page_config(page_title="Text-to-SQL Dashboard", page_icon="📊", layout="wide")
st.markdown("""
    <style>
    body {
        background-color: #f8f9fa;
        font-family: 'Georgia', serif;
    }
    h1 {
        color: #2c3e50;
        font-size: 3rem;
        text-align: center;
        margin-bottom: 20px;
        font-weight: bold;
    }
    .subtitle {
        color: #7f8c8d;
        font-size: 1.2rem;
        text-align: center;
        margin-bottom: 40px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Text-to-SQL Dashboard with Gemini Pro")
st.markdown("""
    <div class="subtitle">
        Transform natural language queries into SQL and analyze your data effortlessly.
    </div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📂 Upload Your Data")
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.sidebar.success("File uploaded successfully!")

    st.subheader("Uploaded Data Preview")
    st.dataframe(df.head(), height=200)

    conn = sqlite3.connect(':memory:')
    df.to_sql('data', conn, index=False, if_exists='replace')

    if st.checkbox("Show Table Schema"):
        st.subheader("Schema")
        schema = pd.DataFrame(df.dtypes, columns=["Type"])
        st.dataframe(schema)

    st.subheader("Query Your Data")
    query = st.text_area("Enter your query in English:", placeholder="e.g., Show total sales by product category", height=100)

    if st.button("Run Query"):
        if query:
            try:
                prompt = f"Convert the following English text to SQL: {query}. The table name is 'data'."
                model = genai.GenerativeModel("models/gemini-2.5-flash")
                response = model.generate_content(prompt)

                sql_query = clean_sql_query(response.text)

                st.code(sql_query, language="sql")

                cursor = conn.cursor()
                cursor.execute(sql_query)
                result = cursor.fetchall()

                if result:
                    columns = [desc[0] for desc in cursor.description]
                    result_df = pd.DataFrame(result, columns=columns)
                    st.subheader("Query Result")
                    st.dataframe(result_df, height=300)
                else:
                    st.info("No results found.")

            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please enter a query.")
else:
    st.info("Please upload a CSV file to get started.")

st.markdown("""
    <div class="footer">
        Built with ❤️ using Streamlit and Gemini Pro
    </div>
""", unsafe_allow_html=True)
