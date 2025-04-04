import streamlit as st
import requests
import pandas as pd

# Backend API URLs
BASE_URL = "http://localhost:8080/api/files"
ROW_URL = "http://localhost:8080/api/data"
AI_URL = "http://localhost:8080/api/ai"
CHART_URL = "http://localhost:8080/api/charts"
BACKEND_URL = "http://localhost:8000"

st.set_page_config(layout = 'wide', page_title="Analyse Your File")
st.title("AI-Powered File Analysis App")

# to upload file 
st.header("Upload a CSV/Excel File")
uploaded_files = st.file_uploader(
    "Upload CSV or Excel files",
    accept_multiple_files=True,
    type=["csv", "xlsx", "xls"]
)

if uploaded_files:

    col1, col2 = st.columns([1,1])

    #to show the uploaded file as a table
    with col2:
        if uploaded_files:
            dataframes = []
            for uploaded_file in uploaded_files:
                st.write(f"Processing file: {uploaded_file.name}, Size: {uploaded_file.size}")
                try:
                    uploaded_file.seek(0)
                    if uploaded_file.name.endswith(".csv"):
                        dataframe = pd.read_csv(uploaded_file)
                    elif uploaded_file.name.endswith((".xls")):
                        dataframe = pd.read_excel(uploaded_file, engine="xlrd")
                    elif uploaded_file.name.endswith((".xlsx")):
                        dataframe = pd.read_excel(uploaded_file, engine="openpyxl")
                    else:
                        st.error("Unsupported file type!")
                        continue

                    dataframes.append(dataframe)
                except Exception as e:
                    st.error(f"Error reading {uploaded_file.name}: {e}")
            if dataframes:
                combined_dataframe = pd.concat(dataframes, ignore_index=True)
                st.dataframe(combined_dataframe)

    with col1:
        if uploaded_files:
            file_data = []
            for f in uploaded_files:
                # Prepare file for multipart/form-data
                f.seek(0)
                file_data.append(
                    ("files", (f.name, f.read(), f.type))
                )
            try:
                response = requests.post(f"{BACKEND_URL}/upload-files", files=file_data)
                if response.status_code == 200:
                    st.success("Files uploaded successfully.")
                else:
                    st.error(f"Error: {response.json()}")
            except Exception as e:
                st.error(f"Connection error: {e}")


        #to view top N rows
        st.header("View Top N Rows from File")
        filename = st.text_input("Enter exact filename (e.g. data.csv or data.xlsx)")
        n = st.number_input("Number of rows to display", min_value=1, value=5)

        if st.button("Fetch Data"):
            try:
                # We call /get-top-rows, which expects filename and n as query parameters
                params = {"filename": filename, "n": n}
                response = requests.get(f"{BACKEND_URL}/get-top-rows", params=params)
                if response.status_code == 200:
                    # Parse the list of dicts into a DataFrame for display
                    data = response.json()
                    df = pd.DataFrame(data)
                    st.dataframe(df)
                else:
                    detail = response.json().get("detail", "Unknown error")
                    st.error(f"Error from backend: {detail}")
            except Exception as e:
                st.error(f"Connection error: {e}")

        st.markdown("---")

#Ask AI a Question
st.header("Ask to AI about the Data")
filename_qa = st.text_input("Filename for Q&A (exact match)")
question = st.text_input("Enter your question")

if st.button("Ask AI"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        # Because your FastAPI /ask endpoint takes filename & question as query params,
        # we'll send them in the query string (params=...) rather than JSON.
        params = {"filename": filename_qa, "question": question}
        try:
            # POST with query params
            response = requests.post(f"{BACKEND_URL}/ask", params=params)
            if response.status_code == 200:
                answer = response.json().get("answer", "")
                st.write("**AI Answer:**", answer)
            else:
                detail = response.json().get("detail", "Unknown error")
                st.error(f"Error from backend: {detail}")
        except Exception as e:
            st.error(f"Connection error: {e}")

#generate chart
st.header("Generate AI-Powered Chart")
file_name = st.text_input("Enter exact file name for chart generation")
column_name = st.text_input("Enter column name for visualization")
chart_type = st.selectbox("Select Chart Type", ["Bar", "Pie"])

if st.button("Generate Chart"):
    if file_name and column_name:
        payload = {"fileName": file_name, "columnName": column_name, "chartType": chart_type}
        response = requests.post(f"{BACKEND_URL}/generate-chart", json=payload)

        if response.status_code == 200:
            chart_data = response.json()
            chart_url = chart_data.get("chart_url", "")
            if chart_url:
                st.image(f"{BACKEND_URL}/get-chart/{chart_url.split('/')[-1]}", caption="Generated Chart")
            else:
                st.error("No data available for chart generation.")
        else:
            st.error(f"Chart generation failed: {response.json().get('detail', 'Unknown error')}")
    else:
        st.warning("Please enter file name and column name.")