import streamlit as st
import requests
import pandas as pd

# Backend API URLs
BASE_URL = "http://localhost:8080/api/files"
ROW_URL = "http://localhost:8080/api/data"
AI_URL = "http://localhost:8080/api/ai"
CHART_URL = "http://localhost:8080/api/charts"

st.title("AI-Powered File Analysis App")

# to upload file 
st.header("Upload a CSV/Excel File")
uploaded_file = st.file_uploader("Choose a file", type=["csv", "xlsx"])

if uploaded_file:
    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
    response = requests.post(f"{BASE_URL}/upload", files=files)

    if response.status_code == 200:
        st.success("File uploaded successfully!")
    else:
        st.error(f"Upload failed: {response.text}")

#to view top N rows
st.header("View Top N Rows from File")
file_name = st.text_input("Enter File Name:")
sheet_name = st.text_input("Enter Sheet Name (For Excel)")
n_rows = st.number_input("Enter Number of Rows:", min_value=1, step=1)

if st.button("Fetch Data"):
    if file_name and sheet_name and n_rows > 0:
        payload = {"fileName": file_name, "sheetName": sheet_name, "n": n_rows}
        response = requests.post(f"{ROW_URL}/top-rows", json=payload)

        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            st.dataframe(df)
        else:
            st.error(f"Failed to fetch data: {response.text}")
else: 
    st.warning("Please enter file name, sheet name, and number of rows.")


#Ask AI a Question
st.header("Ask to AI About Your Data")
ai_prompt = st.text_area("Enter your question:")
if st.button("Ask AI"):
    payload = {"fileName": file_name, "sheetName": sheet_name, "prompt": ai_prompt}
    response = requests.post(f"{AI_URL}/ask", json=payload)

    if response.status_code == 200:
        st.success(response.json())
    else:
        st.error("AI request failed.")

#generate chart
st.header("Generate AI-Powered Chart")
chart_type = st.selectbox("Select Chart Type", ["Bar", "Pie"])

if st.button("Generate Chart"):
    if file_name and sheet_name:
        payload = {"fileName": file_name, "sheetName": sheet_name, "chartType": chart_type.lower()}
        response = requests.post(f"{CHART_URL}/generate-chart", json=payload)

        if response.status_code == 200:
            chart_data = response.json().get("chart_url")
            if "chart_url" in chart_data and "Error" not in chart_data["chart_url"]:
                st.image(chart_data["chart_url"], caption="Generated Chart")
            else:
                st.error("No data available for chart generation.")
        else:
            st.error(f"Chart generation failed: {response.text}")

    else:
        st.warning("Please enter file name and sheet name.")