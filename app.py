import streamlit as st
import pandas as pd
import sqlite3
import google.generativeai as genai
import re

# Configure Gemini Pro API (⚠️ Don't expose this in production)
genai.configure(api_key="--------------------")

# Function to clean the SQL query
def clean_sql_query(sql_query):
    sql_query = re.sub(r'```sql|```', '', sql_query).strip()
    if ";" in sql_query:
        sql_query = sql_query.split(";")[0]  # Run only first statement
    return sql_query

# Page setup
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
    .stButton>button, .sidebar .stFileUploader>div>div>button {
        background-color: #3498db;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 16px;
    }
    .stButton>button:hover, .sidebar .stFileUploader>div>div>button:hover {
        background-color: #2980b9;
    }
    .stTextArea>textarea {
        border-radius: 5px;
        padding: 10px;
        border: 1px solid #bdc3c7;
        font-family: 'Georgia', serif;
    }
    .stDataFrame {
        border-radius: 10px;
        background-color: white;
    }
    .card {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        text-align: center;
        padding: 10px;
        background-color: #2c3e50;
        color: white;
        z-index: 1000;
    }
    .main-content {
        padding-bottom: 60px;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.title("📊 Text-to-SQL Dashboard with Gemini Pro")
st.markdown("""
    <div class="subtitle">
        Transform natural language queries into SQL and analyze your data effortlessly.
    </div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-content">', unsafe_allow_html=True)

# Sidebar for upload
with st.sidebar:
    st.header("📂 Upload Your Data")
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.sidebar.success("File uploaded successfully!")

    st.markdown("""<div class="card"><h3>Uploaded Data Preview</h3></div>""", unsafe_allow_html=True)
    st.dataframe(df.head(), height=200)

    # Create SQLite connection
    conn = sqlite3.connect(':memory:')
    df.to_sql('data', conn, index=False, if_exists='replace')

    # Optional: Schema display
    if st.checkbox("Show Table Schema"):
        schema = pd.DataFrame(df.dtypes, columns=["Type"])
        st.dataframe(schema)

    # Natural language input
    st.markdown("""<div class="card"><h3>Query Your Data</h3></div>""", unsafe_allow_html=True)
    query = st.text_area("Enter your query in English:", placeholder="e.g., Show total sales by product category", height=100)

    if st.button("Run Query"):
        if query:
            try:
                prompt = f"Convert the following English text to SQL: {query}. The table name is 'data'."
                model = genai.GenerativeModel('gemini-1.5-pro')
                response = model.generate_content(prompt)
                sql_query = clean_sql_query(response.text)

                st.markdown("""<div class="card"><h3>Generated SQL Query</h3></div>""", unsafe_allow_html=True)
                st.code(sql_query, language="sql")

                cursor = conn.cursor()
                cursor.execute(sql_query)
                result = cursor.fetchall()

                if result:
                    columns = [desc[0] for desc in cursor.description]
                    result_df = pd.DataFrame(result, columns=columns)
                    st.markdown("""<div class="card"><h3>Query Result</h3></div>""", unsafe_allow_html=True)
                    st.dataframe(result_df, height=300)
                else:
                    st.info("No results found.")
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please enter a query.")
else:
    st.info("Please upload a CSV file to get started.")

st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("""
    <div class="footer">
        Built with ❤️ using Streamlit and Gemini Pro
    </div>
""", unsafe_allow_html=True)
