# -*- coding: utf-8 -*-
"""
Created on Thu Mar 20 22:39:41 2025

@author: ssingh
"""

import streamlit as st
import pandas as pd
import pyodbc
import unicodedata

# Normalize column names (remove spaces, handle case differences, and remove hidden characters)
def normalize_column_name(col):
    return unicodedata.normalize("NFKC", col).strip().lower().replace(" ", "_")

# Map SQL Server data types for validation
sql_data_types = {'decimal', 'varchar', 'int', 'binary', 'datetime', 'float', 'date', 'char', 'bigint'}

# Function to establish SQL Server connection
def connect_to_sql_server(server, user_id, password):
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={server};"
            f"UID={user_id};"
            f"PWD={password};"
        )
        return conn
    except Exception as e:
        st.error("❌ Connection Failed: Invalid credentials or cannot connect to server.")
        return None

# Function to retrieve available databases
def get_databases(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sys.databases")
    databases = [db[0] for db in cursor.fetchall()]
    cursor.close()
    return databases

# Function to retrieve SQL Server table schema
def get_sql_table_schema(conn, schema, table):
    cursor = conn.cursor()
    query = f"""
        SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema}' AND TABLE_NAME = '{table}'
    """
    cursor.execute(query)
    schema_data = cursor.fetchall()
    cursor.close()

    if not schema_data:
        st.error(f"❌ No schema found for {schema}.{table}. Check if the table exists.")
        return None

    sql_schema_cleaned = [tuple(row) for row in schema_data]
    schema_df = pd.DataFrame(sql_schema_cleaned, columns=["Column", "Data Type", "Is Nullable", "Max Length", "Numeric Precision"])
    return schema_df

# Function to infer CSV schema
def infer_csv_schema(df):
    inferred_schema = []
    for col in df.columns:
        dtype = df[col].dtype
        if pd.api.types.is_integer_dtype(dtype):
            sql_type = "BIGINT" if df[col].max() > 2147483647 else "INT"
        elif pd.api.types.is_float_dtype(dtype):
            sql_type = "FLOAT"
        elif pd.api.types.is_bool_dtype(dtype):
            sql_type = "BIT"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            sql_type = "DATETIME"
        elif pd.api.types.is_string_dtype(dtype):
            max_length = df[col].astype(str).str.len().max()
            sql_type = f"VARCHAR({max_length})" if max_length and max_length > 0 else "VARCHAR(MAX)"
        else:
            sql_type = "NVARCHAR(MAX)"  # Default fallback
        inferred_schema.append((col, sql_type, "YES", max_length if "VARCHAR" in sql_type else None, None))

    csv_schema_df = pd.DataFrame(inferred_schema, columns=["Column", "Data Type", "Is Nullable", "Max Length", "Numeric Precision"])
    return csv_schema_df

# Function to validate CSV schema against SQL Server schema
def validate_schema(sql_schema_df, csv_schema_df):
    sql_columns = set(sql_schema_df["Column"].str.lower())
    csv_columns = set(csv_schema_df["Column"].str.lower())

    validation_issues = []

    # Normalize CSV column names
    df.columns = [col.strip() for col in df.columns]

    # Check missing columns in CSV
    for col in sql_columns - csv_columns:
        validation_issues.append(["Missing Column", f"Column '{col}' is in SQL Server but missing from CSV.", "-"])

    # Check extra columns in CSV
    for col in csv_columns - sql_columns:
        validation_issues.append(["Extra Column", f"Column '{col}' is in CSV but not in SQL Server.", "-"])

    # Iterate over matched columns
    for _, row in sql_schema_df.iterrows():
        column = row["Column"]
        is_nullable = row["Is Nullable"]
        max_length = row["Max Length"]
        data_type = str(row["Data Type"]).lower()

        if column not in df.columns:
            continue

        # 1. Null check
        if is_nullable == "NO":
            null_rows = df[df[column].isnull()]
            for idx in null_rows.index:
                validation_issues.append([
                    "Null Value",
                    f"Null found in non-nullable column '{column}'.",
                    f"Row {idx + 2}, Column '{column}'"
                ])

        # 2. Value length check for all types (your provided logic)
        for idx, val in df[column].items():
            if pd.isnull(val):
                continue

            val_str = str(val)

            # Text fields
            if "char" in data_type or "text" in data_type or "varchar" in data_type or "nvarchar" in data_type:
                if max_length and len(val_str) > int(max_length):
                    validation_issues.append([
                        "Length Exceeded",
                        f"Length of value in column '{column}' exceeds defined max ({max_length}).",
                        f"Row {idx + 2}, Length = {len(val_str)}"
                    ])

            # Numeric fields
            elif "int" in data_type or "decimal" in data_type or "float" in data_type or "numeric" in data_type:
                try:
                    _ = float(val)
                except ValueError:
                    validation_issues.append([
                        "Invalid Number",
                        f"Value '{val}' in column '{column}' is not a valid number.",
                        f"Row {idx + 2}, Column '{column}'"
                    ])

            # Date/Time fields
            elif "date" in data_type or "time" in data_type:
                try:
                    _ = pd.to_datetime(val)
                except Exception:
                    validation_issues.append([
                        "Invalid Date/Time",
                        f"Value '{val}' in column '{column}' is not a valid date/time.",
                        f"Row {idx + 2}, Column '{column}'"
                    ])

        # 3. Type mismatch detection
        
        for idx, val in df[column].items():
            if pd.isnull(val):
                continue
            val_str = str(val).strip()
        
            # INT column
            if "int" in data_type:
                try:
                    int(val)
                except:
                    validation_issues.append([
                        "Type Mismatch",
                        f"Expected INT in column '{column}', but found non-integer value: '{val_str}'",
                        f"Row {idx + 2}, Column '{column}'"
                    ])
        
            # FLOAT / DECIMAL column
            elif "float" in data_type or "decimal" in data_type or "numeric" in data_type:
                try:
                    float(val)
                except:
                    validation_issues.append([
                        "Type Mismatch",
                        f"Expected FLOAT/DECIMAL in column '{column}', but found: '{val_str}'",
                        f"Row {idx + 2}, Column '{column}'"
                    ])
        
            # DATE / TIME column
            elif "date" in data_type or "time" in data_type:
                try:
                    pd.to_datetime(val, errors='raise')
                except:
                    validation_issues.append([
                        "Type Mismatch",
                        f"Expected DATE/TIME in column '{column}', but found: '{val_str}'",
                        f"Row {idx + 2}, Column '{column}'"
                    ])
        
            # VARCHAR / NVARCHAR / CHAR column
            elif "char" in data_type or "varchar" in data_type or "nvarchar" in data_type:
                is_number = False
                is_date = False
        
                # Check for number-looking values
                try:
                    float(val_str)
                    is_number = True
                except:
                    pass
        
                # Check for date-looking values
                try:
                    pd.to_datetime(val_str, errors='raise')
                    is_date = True
                except:
                    pass
        
                if is_number:
                    validation_issues.append([
                        "Type Mismatch",
                        f"Expected VARCHAR in column '{column}', but value looks like a NUMBER: '{val_str}'",
                        f"Row {idx + 2}, Column '{column}'"
                    ])
                elif is_date:
                    validation_issues.append([
                        "Type Mismatch",
                        f"Expected VARCHAR in column '{column}', but value looks like a DATE: '{val_str}'",
                        f"Row {idx + 2}, Column '{column}'"
                    ])


    return validation_issues

# Streamlit UI

st.set_page_config(page_title="CSV vs SQL Server Schema Validator", layout="wide")


enhanced_sidebar_style = """
    <style>
    /* Hide top bar, footer, and menu */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Remove top padding from main content */
    .block-container {
        padding-top: 1rem !important;
    }

    /* Sidebar container background and vertical divider */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa !important;
        padding-top: 0 !important;
        border-right: 2px solid #e0e0e0 !important;
    }

    /* Sidebar content wrapper */
    section[data-testid="stSidebar"] > div {
        padding: 1.5rem;
        padding-top: 0 !important;
        margin-top: 0 !important;
        border-radius: 12px;
    }

    /* Adjust the first element inside the sidebar (your IngestIQ heading) */
    section[data-testid="stSidebar"] > div > div:first-child {
        margin-top: -75px !important;
    }

    /* Optional sidebar title styling */
    .sidebar-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #333;
    }

    /* ✨ Enhanced Table Styling ✨ */
    div[data-testid="stDataFrame"] {
        border: 1px solid #d3d3d3;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }

    div[data-testid="stDataFrame"] .css-1r6slb0,
    div[data-testid="stDataFrame"] .css-1v0mbdj {
        font-size: 0.9rem;
        padding: 0.75rem;
        background-color: #fafafa;
        border-bottom: 1px solid #e0e0e0;
    }

   div[data-testid="stDataFrame"] thead th {
    background-color: #f0f0f0 !important;
    font-weight: 700 !important;
    color: #333 !important;
    padding: 10px !important;
    text-align: left;
    border-bottom: 1px solid #d3d3d3;
    }

     
    </style>
"""
st.markdown(enhanced_sidebar_style, unsafe_allow_html=True)



# Layout: Sidebar for Settings, Main for Results
with st.sidebar:
    #st.image("app_logo.png", width = 250)
    st.markdown(
    "<div style='font-size: 3.5em; font-weight: bold; color: #666666;'>IngestIQ</div>",
    unsafe_allow_html=True
)
    # Add space
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    st.header("⚙️ Settings")
    # Add space
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # Step 1: SQL Server Connection
    st.subheader("Connect to SQL Server")
    host_options = ["preview-ps-rds-custom.sca.local", "ps-rds-custom.sca.local", "aws-dev-custom.sca.local"]
    server = st.selectbox("Select SQL Server Host:", options=host_options)
    user_id = st.text_input("Database User ID")
    password = st.text_input("Database Password", type="password")  # Hide input

    if st.button("🔗 Connect"):
        conn = connect_to_sql_server(server, user_id, password)
        if conn:
            st.success("✅ Connection Successful!")
            st.session_state.conn = conn
            st.session_state.databases = get_databases(conn)

    # Step 2: Select DB, schema, table + Apply/Reset
    if "conn" in st.session_state and "databases" in st.session_state:
        st.subheader("Select Database & Table")
        st.session_state.database = st.selectbox("Select Database:", options=st.session_state.databases)
        st.session_state.schema = "dbo"  # Automatically set schema to dbo
        st.session_state.table = st.text_input("Enter Table Name:")


        # Apply & Reset buttons side by side
        col_apply, col_reset = st.columns([1, 1])
        with col_apply:
            if st.button("✅ Apply"):
                st.session_state.applied = True
        with col_reset:
            if st.button("🔄 Reset"):
                st.session_state.clear()
                st.rerun()

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='position: fixed; bottom: 10px; left: 20px; font-size: 0.9em;'>🐍 Python-powered | Engineered with Passion </div>",
        unsafe_allow_html=True
    )

# Right pane header
#st.title("📊 CSV Upload Readiness Validator")

col1, col2 = st.columns([8, 2])
with col1:
    st.markdown(
        "<h2 style='color: #666666;'>🛡️ Data Upload Readiness Validator</h2>",
        unsafe_allow_html=True
    )
with col2:
    st.image("cn_logo.png", width=200)

# Light gray thick horizontal line
st.markdown(
    "<hr style='border: 2px solid #999999; margin-top: 0.5rem; margin-bottom: 1.5rem;'>",
    unsafe_allow_html=True
)


# Show fetch button only after Apply
if st.session_state.get("applied") and all([
    st.session_state.get("database"),
    st.session_state.get("schema"),
    st.session_state.get("table")
]):
    if st.button("📜 Fetch SQL Server Table Schema"):
        conn = st.session_state.conn
        cursor = conn.cursor()
        cursor.execute(f"USE {st.session_state.database}")
        cursor.close()
        sql_schema_df = get_sql_table_schema(conn, st.session_state.schema, st.session_state.table)
        if sql_schema_df is not None:
            st.success(f"✅ Table schema for `{st.session_state.schema}.{st.session_state.table}` retrieved.")
            st.session_state.sql_schema_df = sql_schema_df
if "sql_schema_df" in st.session_state:
    st.subheader("Table Schema")
    #st.dataframe(st.session_state.sql_schema_df)
    st.dataframe(st.session_state.sql_schema_df, use_container_width=True)
    

    st.subheader("Upload File & Infer Schema")
    uploaded_file = st.file_uploader("📂 Upload your CSV, XLS, or TXT file", type=["csv", "xls", "xlsx", "txt"])

    if uploaded_file is not None:
        file_name = uploaded_file.name.lower()
        if file_name.endswith((".xls", ".xlsx")):
            df = pd.read_excel(uploaded_file)
        elif file_name.endswith(".txt"):
            df = pd.read_csv(uploaded_file, sep="|")
        else:  # Default to CSV
            df = pd.read_csv(uploaded_file)


        csv_schema_df = infer_csv_schema(df)
        st.success("✅ CSV Schema Inferred:")
        #st.dataframe(csv_schema_df)
        st.dataframe(csv_schema_df, use_container_width=True)
        st.session_state.csv_schema_df = csv_schema_df

if "csv_schema_df" in st.session_state:
    st.subheader("Validate File Data against SQL Server Table")

    if st.button("🚀 Run Validation Check"):
        validation_issues = validate_schema(st.session_state.sql_schema_df, st.session_state.csv_schema_df)

        if validation_issues:
            validation_df = pd.DataFrame(validation_issues, columns=["Issue Type", "Details", "Row & Column"])
            st.subheader("🔎 Validation Results")
            #st.dataframe(validation_df)
            st.dataframe(validation_df, use_container_width=True)
            st.error(f"❌ {len(validation_issues)} issues found.")
        else:
            st.success("✅ CSV schema matches SQL Server table schema. Ready for upload!")