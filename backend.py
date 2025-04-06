# backend.py

import openai
import pandas as pd
from pydantic import BaseModel
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from io import BytesIO
import matplotlib.pyplot as plt
from typing import Dict, List
import os

# --- CONFIGURE OPENAI ---
openai.api_key = "enter-you-key"

app = FastAPI()

UPLOAD_DIR = "uploads"
CHART_DIR = "charts"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)

# In-memory storage: each filename -> one DataFrame
# Example: data_store["mydata.csv"] = pd.DataFrame(...)
data_store: Dict[str, pd.DataFrame] = {}

class ChartRequest(BaseModel):
    fileName: str
    columnName: str
    chartType: str

@app.post("/upload-files")
async def upload_files(files: List[UploadFile] = File(...)) -> Dict[str, str]:
    """
    Accepts multiple file uploads (CSV or Excel).
    Parses each file into one DataFrame, 
    stores the resulting DataFrame in memory.
    """
    for file in files:
        filename = file.filename
        file_bytes = await file.read()

        try:
            if filename.lower().endswith(".csv"):
                # Parse entire CSV into one DataFrame
                df = pd.read_csv(BytesIO(file_bytes))
                data_store[filename] = df
            elif filename.lower().endswith(".xls"):
                df = pd.read_excel(BytesIO(file_bytes), engine="xlrd")  # Use xlrd for .xls
                data_store[filename] = df
            elif filename.lower().endswith(".xlsx"):
                df = pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
                data_store[filename] = df
            else:
                # Parse entire Excel file (default sheet) into one DataFrame
                df = pd.read_excel(BytesIO(file_bytes))
                data_store[filename] = df

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error parsing {filename}: {str(e)}")

    return {"status": "Files uploaded successfully"}

@app.get("/get-top-rows")
async def get_top_rows(filename: str, n: int) -> List[dict]:
    """
    Returns the top N rows of the specified file
    as a list of dictionaries (JSON-serializable).
    """
    if filename not in data_store:
        raise HTTPException(status_code=404, detail="File not found")

    df = data_store[filename]
    top_rows = df.head(n).to_dict(orient="records")
    return top_rows

@app.post("/ask")
async def ask_question(filename: str, question: str) -> Dict[str, str]:
    """
    Takes up to 5 rows from the DataFrame, builds a prompt,
    and calls OpenAI's API for a naive answer.
    """
    if filename not in data_store:
        raise HTTPException(status_code=404, detail="File not found")

    df = data_store[filename]

    # Grab a small snippet (5 rows) to keep prompts smaller
    snippet = df.head(10).to_csv(index=False)

    prompt = f"""
    You are an expert data analyst. Below is a small snippet of the data (first 5 rows):
    {snippet}

    The user question is: {question}

    Please provide a concise, factual answer based on the snippet.
    If you cannot be certain, please say so.
    """

    try:
        MODEL = "gpt-4o-mini" # or "gpt-4o-mini"
        completion = openai.chat.completions.create(
        model=MODEL,
        messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
            ]
        )

# Print the response
        print(completion.choices[0].message.content)
        answer=completion.choices[0].message.content
        # response = openai.Completion.create(
        #     engine="gpt-4o-mini",
        #     prompt=prompt,
        #     max_tokens=150,
        #     temperature=0.2
        # )
        # answer = response.choices[0].text.strip()
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI API error: {str(e)}")


@app.post("/generate-chart")
async def generate_chart(request: ChartRequest):

    file_name = request.fileName
    column_name = request.columnName
    chart_type = request.chartType.lower()

    if file_name not in data_store:
        raise HTTPException(status_code=404, detail="File not found")

    df = data_store[file_name]

    if column_name not in df.columns:
        raise HTTPException(status_code=400, detail=f"Column '{column_name}' not found in {file_name}")

    try:
        chart_path = os.path.join(CHART_DIR, f"{file_name}_{column_name}_{chart_type}.png")

        # Count unique values for categorical data
        data_counts = df[column_name].value_counts()

        plt.figure(figsize=(8, 5))
        if chart_type.lower() == "bar":
            data_counts.plot(kind="bar", color="skyblue")
            plt.ylabel("Count")
        elif chart_type.lower() == "pie":
            data_counts.plot(kind="pie", autopct="%1.1f%%")
        else:
            raise HTTPException(status_code=400, detail="Invalid chart type. Use 'Bar' or 'Pie'.")

        plt.title(f"{chart_type.capitalize()} Chart for {column_name}")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(chart_path)
        plt.close()

        return {"chart_url": f"/get-chart/{os.path.basename(chart_path)}"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart generation error: {str(e)}")


@app.get("/get-chart/{chart_name}")
async def get_chart(chart_name: str):
    """
    Serves the generated chart image.
    """
    chart_path = os.path.join(CHART_DIR, chart_name)
    if os.path.exists(chart_path):
        return FileResponse(chart_path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Chart not found")