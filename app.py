import streamlit as st
import datetime
import json
import os
from pathlib import Path
from openai import OpenAI
import matplotlib.pyplot as plt
import pandas as pd
import re

# Constants
DATA_PATH = Path("data/saved_entries.json")

# Initialize OpenAI client
@st.cache_resource
def get_openai_client():
    # You'll need to set your OpenAI API key as an environment variable
    # or use Streamlit secrets: st.secrets["OPENAI_API_KEY"]
    api_key = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        st.error("OpenAI API key not found. Please set OPENAI_API_KEY environment variable or add it to Streamlit secrets.")
        st.stop()
    return OpenAI(api_key=api_key)

# Load or initialize data
def load_data():
    if not DATA_PATH.exists():
        return []
    try:
        with open(DATA_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        st.error("Error loading data file. Starting with empty data.")
        return []

def save_data(entries):
    try:
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_PATH, "w") as f:
            json.dump(entries, f, indent=2, default=str)
    except Exception as e:
        st.error(f"Error saving data: {e}")

# ChatGPT call
def get_feedback(book_title, writeup):
    client = get_openai_client()
    prompt = f"""
    A child wrote a summary about the book '{book_title}'.
    Here is the write-up:
    {writeup}

    Please do the following:
    1. Provide a sample summary (about 500 words).
    2. Rate the write-up from 1 to 10 based on key point coverage.
    3. Explain the rating: what is good and what can be improved.
    
    Please format your response clearly with section headers.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",  # Changed from "gpt-4o" to "gpt-4" (more widely available)
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error getting feedback from OpenAI: {e}")
        return None

def extract_rating(feedback_text):
    """Extract rating from feedback text using regex"""
    if not feedback_text:
        return None
    
    # Look for patterns like "Rating: 8", "8/10", "Score: 8", etc.
    rating_patterns = [
        r'[Rr]ating:?\s*(\d+)',
        r'[Ss]core:?\s*(\d+)',
        r'(\d+)/10',
        r'(\d+)\s*out\s*of\s*10',
        r'[Ii]\s*(?:would\s*)?rate\s*(?:this\s*)?(?:at\s*)?(\d+)'
    ]
    
    for pattern in rating_patterns:
        match = re.search(pattern, feedback_text)
        if match:
            rating = int(match.group(1))
            if 1 <= rating <= 10:
                return rating
    
    return None

# UI
st.title("📚 Reading Tool for Kids")

mode = st.radio("What would you like to do?", ["Create new", "Review previous"], index=0)

entries = load_data()

if mode == "Create new":
    st.header("Create New Entry")
    
    date = st.date_input("Date", value=datetime.date.today())
    book_title = st.text_input("Book Title")
    writeup = st.text_area("Your Write-up (max 1000 words)", height=300, max_chars=1000)
    
    # Show character count
    if writeup:
        st.caption(f"Characters: {len(writeup)}/1000")

    if st.button("Submit for Feedback") and writeup.strip() and book_title.strip():
        with st.spinner("Getting feedback from ChatGPT..."):
            feedback = get_feedback(book_title, writeup)
            
            if feedback:
                st.success("Feedback received!")
                st.markdown("### ChatGPT Feedback")
                st.write(feedback)

                # Extract rating with improved logic
                rating = extract_rating(feedback)
                if rating:
                    st.info(f"Extracted rating: {rating}/10")
                else:
                    st.warning("Could not extract a rating from the feedback.")

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
                st.success("Entry saved successfully!")
            else:
                st.error("Failed to get feedback. Please try again.")
    
    elif st.button("Submit for Feedback"):
        st.warning("Please fill in both the book title and write-up before submitting.")

elif mode == "Review previous":
    st.header("Review Previous Entries")
    
    if not entries:
        st.info("No previous entries yet. Create your first entry!")
    else:
        # Display entries in reverse chronological order
        entry_options = [f"{e['date']} - {e['book_title']}" for e in reversed(entries)]
        selected = st.selectbox("Select entry", entry_options)
        
        # Find the selected entry
        entry = None
        for e in entries:
            if f"{e['date']} - {e['book_title']}" == selected:
                entry = e
                break
        
        if entry:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("### Your Write-up")
                st.write(entry["writeup"])
                
                st.markdown("### ChatGPT Feedback")
                st.write(entry["feedback"])
            
            with col2:
                if entry.get("rating"):
                    st.metric("Rating", f"{entry['rating']}/10")

            # Plot rating trend
            st.markdown("### 📈 Rating Trend")
            
            # Filter entries with ratings and sort by date
            rated_entries = [e for e in entries if e.get("rating") is not None]
            
            if len(rated_entries) >= 2:
                # Sort by date
                rated_entries.sort(key=lambda x: x["date"])
                
                # Create DataFrame for plotting
                df = pd.DataFrame({
                    "Date": pd.to_datetime([e["date"] for e in rated_entries]),
                    "Rating": [e["rating"] for e in rated_entries]
                })
                
                # Use Streamlit's line chart
                st.line_chart(df.set_index("Date")["Rating"], height=400)
                
                # Show some stats
                avg_rating = sum(e["rating"] for e in rated_entries) / len(rated_entries)
                st.info(f"Average rating: {avg_rating:.1f}/10 across {len(rated_entries)} entries")
                
            elif len(rated_entries) == 1:
                st.info("Need at least 2 rated entries to show a trend.")
            else:
                st.info("No ratings available for trend analysis.")

# Add sidebar with summary stats
if entries:
    st.sidebar.header("📊 Summary")
    st.sidebar.metric("Total Entries", len(entries))
    
    rated_entries = [e for e in entries if e.get("rating") is not None]
    if rated_entries:
        avg_rating = sum(e["rating"] for e in rated_entries) / len(rated_entries)
        st.sidebar.metric("Average Rating", f"{avg_rating:.1f}/10")
        st.sidebar.metric("Rated Entries", len(rated_entries))
    
    # Recent books
    if len(entries) > 0:
        st.sidebar.subheader("Recent Books")
        for entry in list(reversed(entries))[:3]:
            st.sidebar.text(f"• {entry['book_title']}")
