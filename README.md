
# 📄 Data Upload Readiness Validator (Streamlit App)

This Streamlit-based application helps users **validate CSV, Excel, or TXT files** against a **SQL Server table schema** before uploading them into the Performance Suite application. It ensures early detection of file structure issues, saving time and improving data ingestion success.

---

## 🚀 Key Features

- **SQL Server Database Connection** (Windows Authentication only).
- **Dynamic Schema Comparison**:
  - Fetch the SQL Server table schema.
  - Infer file schema automatically.
  - Compare and identify discrepancies.
- **Validation Capabilities**:
  - Missing columns
  - Extra columns
  - Nulls in non-nullable fields
  - Data type mismatches
  - Format inconsistencies
  - Length violations
- **File Type Support**:
  - `.csv`, `.xls`, `.xlsx`, `.txt` (pipe-delimited)
- **Professional, User-friendly UI** with styled alerts and reset functionality.
- **No actual data ingestion** into SQL Server — purely validation.

---

## 🛠️ How It Works

### Step 1: Connect to SQL Server
- Select a server (`rds-custom.local`, `rds-custom12.local`, `aws-dev-custom.local`).
- Authenticate via Windows Authentication.
- Click **Connect** and get confirmation.

### Step 2: Select Database and Table
- Choose a database from your accessible list.
- Manually input the target table name.
- Click **Apply** to confirm selections.

### Step 3: Fetch SQL Server Table Schema
- Click **Fetch SQL Server Table Schema**.
- View details like Column Names, Data Types, Nullability, etc.

### Step 4: Upload and Infer File Schema
- Upload your data file.
- The app automatically infers and displays the file’s schema.

### Step 5: Run Validation
- Click **Run Validation Check**.
- Review validation results showing:
  - Issue Type
  - Detailed Description
  - Row and Column location

### Step 6: Reset for New Validation
- Click **Reset** to start fresh without reloading the app.

---

## 📋 Requirements

- Python 3.9+
- Streamlit
- Pandas
- pyodbc

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 🚀 Running the App

Start the app locally:

```bash
streamlit run app.py
```

Or using Docker (if Dockerfile is provided):

```bash
docker build -t csv-validator .
docker run -p 8501:8501 csv-validator
```

---

## 💬 Contribution

Feel free to open issues or submit pull requests for enhancements, new features, or UI improvements.


---

# ✨
**Designed to make data validation seamless, reliable, and user-friendly!**
