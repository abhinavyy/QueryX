import os
import io
import re
import json
import sqlite3
import pandas as pd
import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)

def clean_sql_query(sql_query: str) -> str:
    """Extracts and cleans a valid SQL query from model output."""
    if not sql_query:
        return None

    # Remove code block markers
    sql_query = re.sub(r"```(?:sql)?|```", "", sql_query).strip()

    # Common error 
    if re.search(r"(error|sorry|cannot|unknown|hi|hello|thanks|help)", sql_query, re.IGNORECASE):
        return None

    # Extract only the first SQL statement
    sql_match = re.search(
        r"(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|WITH)\s.+?(?=;|$)",
        sql_query,
        re.IGNORECASE | re.DOTALL
    )
    if not sql_match:
        return None

    sql_cleaned = re.sub(r"\s+", " ", sql_match.group(0)).strip()
    return sql_cleaned if len(sql_cleaned.split()) > 3 else None


def load_csv_once(uploaded_file):
    """Load and cache uploaded CSV file in Streamlit session."""
    if uploaded_file is None:
        return None, "No file uploaded."

    if "df" in st.session_state and st.session_state.get("uploaded_name") == uploaded_file.name:
        return st.session_state["df"], "File loaded from session."

    try:
        uploaded_file.seek(0)
        raw_data = uploaded_file.read()
        if not raw_data:
            return None, "CSV file is empty or unreadable."

        df = pd.read_csv(io.BytesIO(raw_data))
        if df.empty:
            return None, "CSV file contains no data."

        st.session_state["df"] = df
        st.session_state["uploaded_name"] = uploaded_file.name
        return df, "File uploaded successfully!"

    except UnicodeDecodeError:
        uploaded_file.seek(0)
        raw_data = uploaded_file.read()
        try:
            df = pd.read_csv(io.BytesIO(raw_data), encoding="latin-1")
            st.session_state["df"] = df
            st.session_state["uploaded_name"] = uploaded_file.name
            return df, "File uploaded successfully (latin-1 encoding)."
        except Exception as e:
            return None, f"Encoding error: {e}"

    except Exception as e:
        return None, f"Error reading CSV: {e}"


def get_table_schema(df: pd.DataFrame) -> str:
    """Generate JSON table schema for Gemini context."""
    schema = {
        "table_name": "data",
        "columns": {
            col: {
                "dtype": str(df[col].dtype),
                "sample": df[col].dropna().head(3).tolist()
            }
            for col in df.columns
        },
    }
    return json.dumps(schema, indent=2)

# design
st.set_page_config(page_title="QueryAI - Text-to-SQL", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    body {background-color: #f8f9fa; font-family: 'Georgia', serif;}
    h1 {color: #2c3e50; text-align: center; margin-bottom: 20px;}
    .subtitle {color: #7f8c8d; text-align: center; margin-bottom: 30px;}
    .success-box {background: #55efc4; padding: 10px; border-left: 5px solid #00b894; border-radius: 10px;}
    .error-box {background: #ffeaa7; padding: 10px; border-left: 5px solid #e17055; border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

st.title("📊 QueryAI — Natural Language to SQL")
st.markdown("""
    <div class="subtitle">
        Upload your CSV, ask questions in plain English, and get instant SQL queries.
    </div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📂 Upload Your CSV File")
    uploaded_file = st.file_uploader("Select a CSV file", type=["csv"])

if uploaded_file is not None:
    df, message = load_csv_once(uploaded_file)

    if df is None:
        st.markdown(f"<div class='error-box'>❌ <b>{message}</b></div>", unsafe_allow_html=True)
        st.stop()
    else:
        st.sidebar.success(message)

    st.subheader("📄 Data Preview")
    st.dataframe(df.head(), height=250)
    conn = sqlite3.connect(":memory:")
    df.to_sql("data", conn, index=False, if_exists="replace")
    if st.checkbox("Show Table Schema"):
        st.subheader("📋 Table Schema")
        schema_json = get_table_schema(df)
        st.dataframe(pd.DataFrame({
            "Column": df.columns,
            "Type": df.dtypes.astype(str),
            "Non-Null": df.count().values
        }))
        st.code(schema_json, language="json")

    st.subheader("💬 Ask Your Query")
    query = st.text_area("Enter your query in English:", placeholder="e.g., Show total sales by category", height=100)

    if st.button("Run Query"):
        if not query.strip():
            st.warning("Please enter a query.")
        else:
            try:
                schema_info = get_table_schema(df)
                prompt = f"""
                Convert the following English query into valid SQL for the given table.
                TABLE SCHEMA:
                {schema_info}

                ENGLISH QUERY: "{query}"

                Requirements:
                - Use exact column names.
                - Generate SQLite-compatible SQL only.
                - Output only the SQL query.
                """

                model = genai.GenerativeModel("models/gemini-2.5-flash")
                response = model.generate_content(prompt)
                sql_query = clean_sql_query(response.text)

                if not sql_query:
                    st.markdown("<div class='error-box'>❌ Invalid SQL generated.</div>", unsafe_allow_html=True)
                    st.write(response.text)
                else:
                    st.markdown("<div class='success-box'>✅ SQL Generated Successfully!</div>", unsafe_allow_html=True)
                    st.code(sql_query, language="sql")

                    # Execute SQL
                    cursor = conn.cursor()
                    cursor.execute(sql_query)
                    result = cursor.fetchall()

                    if result:
                        result_df = pd.DataFrame(result, columns=[desc[0] for desc in cursor.description])
                        st.subheader("📈 Query Results")
                        st.dataframe(result_df, height=300)
                    else:
                        st.info("No results found.")

            except Exception as e:
                st.markdown(f"<div class='error-box'>❌ Error: {e}</div>", unsafe_allow_html=True)

else:
    st.info(" Upload a CSV file to begin.")
    st.markdown("""
    ### Example Queries
    - Show me all records  
    - Count total number of rows  
    - Find unique values in [column name]  
    - Calculate average of [numeric column]  
    """)

st.markdown("<hr><center> QueryAI </center>", unsafe_allow_html=True)
