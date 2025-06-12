import streamlit as st
import datetime
import json
import os
from pathlib import Path
import openai
import matplotlib.pyplot as plt

# Constants
DATA_PATH = Path("data/saved_entries.json")

# Load or initialize data
def load_data():
    if not DATA_PATH.exists():
        return []
    with open(DATA_PATH, "r") as f:
        return json.load(f)

def save_data(entries):
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA_PATH, "w") as f:
        json.dump(entries, f, indent=2)

# ChatGPT call
def get_feedback(book_title, writeup):
    prompt = f"""
    A child wrote a summary about the book '{book_title}'.
    Here is the write-up:
    {writeup}

    Please do the following:
    1. Provide a sample summary (about 500 words).
    2. Rate the write-up from 1 to 10 based on key point coverage.
    3. Explain the rating: what is good and what can be improved.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# UI
st.title("📚 Reading Tool for Kids")

mode = st.radio("What would you like to do?", ["Create new", "Review previous"], index=0)

entries = load_data()

if mode == "Create new":
    date = st.date_input("Date", value=datetime.date.today())
    book_title = st.text_input("Book Title")
    writeup = st.text_area("Your Write-up (max 1000 words)", height=300)

    if st.button("Submit for Feedback") and writeup.strip():
        with st.spinner("Contacting ChatGPT..."):
            feedback = get_feedback(book_title, writeup)
            st.success("Feedback received!")
            st.markdown("### ChatGPT Feedback")
            st.write(feedback)

            # Try to extract rating
            rating_line = next((line for line in feedback.splitlines() if any(str(i) in line for i in range(1, 11))), "")
            try:
                rating = int([int(s) for s in rating_line.split() if s.isdigit()][0])
            except:
                rating = None

            # Save entry
            new_entry = {
                "date": str(date),
                "book_title": book_title,
                "writeup": writeup,
                "feedback": feedback,
                "rating": rating
            }
            entries.append(new_entry)
            save_data(entries)

elif mode == "Review previous":
    if not entries:
        st.info("No previous entries yet.")
    else:
        selected = st.selectbox("Select entry", [f"{e['date']} - {e['book_title']}" for e in entries])
        entry = next(e for e in entries if f"{e['date']} - {e['book_title']}" == selected)
        st.markdown("### Your Write-up")
        st.write(entry["writeup"])
        st.markdown("### ChatGPT Feedback")
        st.write(entry["feedback"])

        # Plot rating trend
        st.markdown("### 📈 Rating Trend")
        dates = [e["date"] for e in entries if e.get("rating") is not None]
        ratings = [e["rating"] for e in entries if e.get("rating") is not None]

        if dates and ratings:
            st.line_chart(data={"Rating": ratings}, x=dates)
        else:
            st.write("No ratings available for trend analysis.")