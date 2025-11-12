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

#cleaning return output from model to extract valid SQL
def clean_sql_query(sql_query: str) -> str:
    """Extracts and cleans a valid SQL query from model output."""
    if not sql_query:
        return None

    sql_query = re.sub(r"```(?:sql)?|```", "", sql_query).strip()
    if re.search(r"(error|sorry|cannot|unknown|hi|hello|thanks|help)", sql_query, re.IGNORECASE):
        return None

    sql_match = re.search(
        r"(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|WITH)\s.+?(?=;|$)",
        sql_query,
        re.IGNORECASE | re.DOTALL
    )
    if not sql_match:
        return None

    sql_cleaned = re.sub(r"\s+", " ", sql_match.group(0)).strip()
    return sql_cleaned if len(sql_cleaned.split()) > 3 else None


def load_csv_files(uploaded_files):
    if not uploaded_files:
        return None, "No files uploaded."

    dataframes = {}
    messages = []
    
    for uploaded_file in uploaded_files:
        cache_key = f"df_{uploaded_file.name}"
        
        if cache_key in st.session_state:
            dataframes[uploaded_file.name] = st.session_state[cache_key]
            messages.append(f"'{uploaded_file.name}' loaded from session.")
            continue

        try:
            uploaded_file.seek(0)
            raw_data = uploaded_file.read()
            if not raw_data:
                messages.append(f"'{uploaded_file.name}' is empty or unreadable.")
                continue

            df = pd.read_csv(io.BytesIO(raw_data))
            if df.empty:
                messages.append(f"'{uploaded_file.name}' contains no data.")
                continue

            df.columns = [re.sub(r'[^a-zA-Z0-9_]', '_', col) for col in df.columns]
            
            dataframes[uploaded_file.name] = df
            st.session_state[cache_key] = df
            messages.append(f"'{uploaded_file.name}' uploaded successfully!")

        except UnicodeDecodeError:
            uploaded_file.seek(0)
            raw_data = uploaded_file.read()
            try:
                df = pd.read_csv(io.BytesIO(raw_data), encoding="latin-1")
                df.columns = [re.sub(r'[^a-zA-Z0-9_]', '_', col) for col in df.columns]
                dataframes[uploaded_file.name] = df
                st.session_state[cache_key] = df
                messages.append(f"'{uploaded_file.name}' uploaded successfully (latin-1 encoding).")
            except Exception as e:
                messages.append(f"Encoding error in '{uploaded_file.name}': {e}")

        except Exception as e:
            messages.append(f"Error reading '{uploaded_file.name}': {e}")

    return dataframes, messages


def get_database_schema(dataframes):
    """Generate comprehensive JSON schema for all tables for Gemini context."""
    schema = {}
    
    for filename, df in dataframes.items():
        table_name = os.path.splitext(filename)[0].replace(' ', '_')
        
        schema[table_name] = {
            "columns": {
                col: {
                    "dtype": str(df[col].dtype),
                    "sample": df[col].dropna().head(3).tolist()
                }
                for col in df.columns
            }
        }
    
    return json.dumps(schema, indent=2)


def setup_sqlite_database(dataframes):
    """Create SQLite in-memory database with all tables."""
    conn = sqlite3.connect(":memory:")
    
    for filename, df in dataframes.items():
        table_name = os.path.splitext(filename)[0].replace(' ', '_')
        df.to_sql(table_name, conn, index=False, if_exists="replace")
    
    return conn


def get_table_info(conn):
    """Get information about all tables in the database."""
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    table_info = {}
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        table_info[table_name] = [col[1] for col in columns] 
    
    return table_info


st.set_page_config(page_title="QueryAI - Multi-Table SQL", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    body {background-color: #f8f9fa; font-family: 'Georgia', serif;}
    h1 {color: #2c3e50; text-align: center; margin-bottom: 20px;}
    .subtitle {color: #7f8c8d; text-align: center; margin-bottom: 30px;}
    .success-box {background: #55efc4; padding: 10px; border-left: 5px solid #00b894; border-radius: 10px;}
    .error-box {background: #ffeaa7; padding: 10px; border-left: 5px solid #e17055; border-radius: 10px;}
    .info-box {background: #74b9ff; padding: 10px; border-left: 5px solid #0984e3; border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

st.title("📊 QueryAI — Multi-Table Natural Language to SQL")
st.markdown("""
    <div class="subtitle">
        Upload multiple CSVs, ask complex questions with joins, and get instant SQL queries.
    </div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📂 Upload Your CSV Files")
    uploaded_files = st.file_uploader("Select CSV files", type=["csv"], accept_multiple_files=True)
    
    if uploaded_files:
        st.markdown(f"<div class='info-box'>📁 {len(uploaded_files)} file(s) selected</div>", unsafe_allow_html=True)

if uploaded_files:
    dataframes, messages = load_csv_files(uploaded_files)

    if not dataframes:
        st.markdown(f"<div class='error-box'>❌ No valid CSV files could be loaded.</div>", unsafe_allow_html=True)
        for msg in messages:
            st.error(msg)
        st.stop()
    else:
        # Show upload messages
        for msg in messages:
            if "successfully" in msg.lower():
                st.sidebar.success(msg)
            else:
                st.sidebar.warning(msg)

    # Setup database
    conn = setup_sqlite_database(dataframes)
    table_info = get_table_info(conn)

    # Display data previews
    st.subheader("📄 Data Previews")
    tabs = st.tabs([f"📊 {os.path.splitext(name)[0]}" for name in dataframes.keys()])
    
    for tab, (filename, df) in zip(tabs, dataframes.items()):
        with tab:
            table_name = os.path.splitext(filename)[0].replace(' ', '_')
            st.write(f"**Table:** `{table_name}`")
            st.dataframe(df.head(), height=250)

    if st.checkbox("Show Database Schema"):
        st.subheader("📋 Complete Database Schema")
        schema_json = get_database_schema(dataframes)
        
        st.write("**Available Tables & Columns:**")
        for table_name, columns in table_info.items():
            st.write(f"**{table_name}**: {', '.join(columns)}")
        
        st.code(schema_json, language="json")

    st.subheader("💬 Ask Your Complex Query")
    query = st.text_area(
        "Enter your query in English:", 
        placeholder="e.g., Show total sales by category joining orders and products tables",
        height=100
    )

    with st.expander("💡 Example Multi-Table Queries"):
        st.markdown("""
        **Complex Query Examples:**
        - `Join customers and orders tables to show customer names with their order totals`
        - `Find the top 5 products by sales volume across all regions`
        - `Show monthly sales trends with product categories`
        """)

    if st.button("Run Query"):
        if not query.strip():
            st.warning("Please enter a query.")
        else:
            try:
                schema_info = get_database_schema(dataframes)
                table_names = ", ".join([os.path.splitext(name)[0].replace(' ', '_') for name in dataframes.keys()])
                
                prompt = f"""
                Convert the following English query into valid SQLite SQL for the given database schema.
                
                DATABASE SCHEMA:
                {schema_info}
                
                AVAILABLE TABLES: {table_names}
                
                ENGLISH QUERY: "{query}"
                
                Requirements:
                - Use exact table and column names from the schema
                - Generate SQLite-compatible SQL only
                - Support complex operations: JOINs, aggregations, nested queries, filtering
                - Use appropriate JOIN conditions based on common column names
                - Output only the SQL query, no explanations
                - For joins, use INNER JOIN by default unless specified otherwise
                """

                model = genai.GenerativeModel("models/gemini-2.5-flash")
                response = model.generate_content(prompt)
                sql_query = clean_sql_query(response.text)

                if not sql_query:
                    st.markdown("<div class='error-box'>❌ Invalid SQL generated.</div>", unsafe_allow_html=True)
                    st.write("Model response:", response.text)
                else:
                    st.markdown("<div class='success-box'>✅ SQL Generated Successfully!</div>", unsafe_allow_html=True)
                    st.code(sql_query, language="sql")

                    # Execute SQL
                    cursor = conn.cursor()
                    try:
                        cursor.execute(sql_query)
                        result = cursor.fetchall()

                        if result:
                            result_df = pd.DataFrame(result, columns=[desc[0] for desc in cursor.description])
                            st.subheader("📈 Query Results")
                            st.dataframe(result_df, height=300)
                            
                            # Show some basic stats
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Rows Returned", len(result_df))
                            with col2:
                                st.metric("Columns", len(result_df.columns))
                            with col3:
                                st.metric("Query Type", sql_query.split()[0].upper())
                        else:
                            st.info("No results found for the query.")

                    except sqlite3.Error as e:
                        st.markdown(f"<div class='error-box'>❌ SQL Execution Error: {e}</div>", unsafe_allow_html=True)
                        st.write("Generated SQL:", sql_query)

            except Exception as e:
                st.markdown(f"<div class='error-box'>❌ Error: {e}</div>", unsafe_allow_html=True)

else:
    st.info("📁 Upload multiple CSV files to begin analyzing relationships between tables.")
    
    st.markdown("""
    ### Multi-Table Capabilities
    
    **Supported Operations:**
    - ✅ **JOINs** (INNER, LEFT, RIGHT, FULL)
    - ✅ **Aggregations** (SUM, COUNT, AVG, MAX, MIN)
    - ✅ **Nested Queries** (Subqueries)
    - ✅ **Complex Filtering** (WHERE, HAVING)
    - ✅ **Grouping and Sorting** (GROUP BY, ORDER BY)
    - ✅ **Multiple Table Operations**
    """)

st.markdown("<hr><center>QueryAI - Multi-Table SQL Analytics</center>", unsafe_allow_html=True)

