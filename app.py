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
def get_feedback(book_title, writeup, feedback_type):
    client = get_openai_client()
    
    # Customize prompt based on feedback type
    feedback_focus = {
        "Writing Skill": """
        Focus on writing mechanics, structure, grammar, sentence flow, and overall writing technique.
        Provide specific tips on how to improve writing clarity, organization, and style.
        """,
        "Vocabulary": """
        Focus on word choice, vocabulary range, use of descriptive language, and expression.
        Suggest specific vocabulary improvements and more sophisticated word alternatives.
        """,
        "Depth of Thinking": """
        Focus on critical thinking, analysis, reasoning, and the depth of understanding shown.
        Evaluate how well the child demonstrates comprehension and personal insights about the book.
        """
    }
    
    prompt = f"""
    A child wrote a summary about the book '{book_title}'.
    Here is the write-up:
    {writeup}

    Please provide feedback focusing specifically on: {feedback_type}
    {feedback_focus[feedback_type]}

    Please do the following:
    1. Rate the write-up from 1 to 10 based on the chosen focus area ({feedback_type}).
    2. Explain what is done well in terms of {feedback_type.lower()}.
    3. Provide 3-5 specific, actionable suggestions for improvement in {feedback_type.lower()}.
    4. Give concrete examples of how to implement these suggestions.
    5. Provide a brief sample showing how a section could be improved.
    
    Please format your response clearly with section headers and be encouraging while providing constructive feedback.
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

# UI
st.title("📚 Reading Tool for Kids")

# Main navigation with better styling
st.subheader("What would you like to do today?")
col1, col2 = st.columns(2)

with col1:
    create_new = st.button("📝 Create New Entry", use_container_width=True, type="primary")

with col2:
    view_previous = st.button("📖 View Previous Entries", use_container_width=True)

# Initialize session state for navigation
if 'current_mode' not in st.session_state:
    st.session_state.current_mode = None
if 'show_feedback' not in st.session_state:
    st.session_state.show_feedback = False
if 'current_entry' not in st.session_state:
    st.session_state.current_entry = None

# Handle navigation
if create_new:
    st.session_state.current_mode = "create_new"
    st.session_state.show_feedback = False
    st.session_state.current_entry = None
    st.session_state.confirm_delete = False

if view_previous:
    st.session_state.current_mode = "view_previous"
    st.session_state.show_feedback = False
    st.session_state.confirm_delete = False

entries = load_data()

if st.session_state.current_mode == "create_new":
    st.markdown("---")
    st.header("✏️ Create New Entry")
    
    date = st.date_input("Date", value=datetime.date.today())
    book_title = st.text_input("📚 Book Title", placeholder="Enter the title of the book you read...")
    writeup = st.text_area("✍️ Your Write-up (max 1000 words)", 
                          height=300, 
                          max_chars=1000,
                          placeholder="Write about the book... What did you think? What happened? What did you learn?")
    
    # Show character count
    if writeup:
        st.caption(f"Characters: {len(writeup)}/1000")
    
    # Feedback type selection
    st.markdown("### 🎯 What kind of feedback are you looking for?")
    feedback_type = st.selectbox(
        "Choose focus area:",
        ["Writing Skill", "Vocabulary", "Depth of Thinking"],
        help="Select what aspect you'd like to improve"
    )
    
    feedback_descriptions = {
        "Writing Skill": "📝 Focus on grammar, sentence structure, organization, and writing flow",
        "Vocabulary": "📖 Focus on word choice, descriptive language, and expression",
        "Depth of Thinking": "🧠 Focus on analysis, reasoning, and understanding of the book"
    }
    
    st.info(feedback_descriptions[feedback_type])

    # Submit button with validation
    submit_clicked = st.button("🚀 Submit for Feedback", type="primary", use_container_width=True)
    
    if submit_clicked:
        if not book_title.strip():
            st.warning("📚 Please enter a book title.")
        elif not writeup.strip():
            st.warning("✍️ Please write something about the book.")
        else:
            with st.spinner("🤖 Getting personalized feedback from ChatGPT..."):
                feedback = get_feedback(book_title, writeup, feedback_type)
                
                if feedback:
                    st.session_state.show_feedback = True
                    st.session_state.current_entry = {
                        "date": str(date),
                        "book_title": book_title,
                        "writeup": writeup,
                        "feedback": feedback,
                        "feedback_type": feedback_type,
                        "rating": extract_rating(feedback)
                    }
                else:
                    st.error("❌ Failed to get feedback. Please try again.")

    # Show feedback if available
    if st.session_state.show_feedback and st.session_state.current_entry:
        st.markdown("---")
        st.success("✅ Feedback received!")
        
        entry = st.session_state.current_entry
        
        # Display feedback type
        st.markdown(f"### 🎯 Feedback Focus: {entry['feedback_type']}")
        
        # Display the feedback
        st.markdown("### 🤖 ChatGPT Feedback")
        st.write(entry["feedback"])

        # Show extracted rating if available
        if entry.get("rating"):
            st.info(f"📊 Rating: {entry['rating']}/10")
        else:
            st.warning("⚠️ Could not extract a numeric rating from the feedback.")
        
        # Exit and start new button
        st.markdown("---")
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if st.button("💾 Save & Start New", type="primary", use_container_width=True):
                # Save the entry
                entries.append(entry)
                save_data(entries)
                
                # Reset session state
                st.session_state.show_feedback = False
                st.session_state.current_entry = None
                st.session_state.current_mode = None
                
                st.success("📁 Entry saved successfully! Choose an option above to continue.")
                st.rerun()
        
        with col2:
            if st.button("🔄 Continue Editing", use_container_width=True):
                st.session_state.show_feedback = False
                st.session_state.current_entry = None

elif st.session_state.current_mode == "view_previous":
    st.markdown("---")
    st.header("📖 Review Previous Entries")
    
    if not entries:
        st.info("📝 No previous entries yet. Create your first entry!")
        if st.button("✏️ Create First Entry", type="primary"):
            st.session_state.current_mode = "create_new"
            st.rerun()
    else:
        # Display entries in reverse chronological order
        entry_options = [f"{e['date']} - {e['book_title']}" for e in reversed(entries)]
        selected = st.selectbox("📚 Select an entry to review:", entry_options)
        
        # Find the selected entry
        entry = None
        for e in entries:
            if f"{e['date']} - {e['book_title']}" == selected:
                entry = e
                break
        
        if entry:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("### ✍️ Your Write-up")
                with st.container():
                    st.write(entry["writeup"])
                
                st.markdown("### 🤖 ChatGPT Feedback")
                
                # Show feedback type if available (for newer entries)
                if entry.get("feedback_type"):
                    st.info(f"🎯 Feedback Focus: {entry['feedback_type']}")
                
                with st.container():
                    st.write(entry["feedback"])
            
            with col2:
                st.markdown("### 📊 Stats")
                if entry.get("rating"):
                    st.metric("Rating", f"{entry['rating']}/10")
                
                if entry.get("feedback_type"):
                    st.metric("Focus Area", entry['feedback_type'])
                
                st.metric("Date", entry['date'])
                
                # Delete entry button with confirmation
                st.markdown("---")
                if 'confirm_delete' not in st.session_state:
                    st.session_state.confirm_delete = False
                
                if not st.session_state.confirm_delete:
                    if st.button("🗑️ Delete This Entry", type="secondary", use_container_width=True):
                        st.session_state.confirm_delete = True
                        st.rerun()
                else:
                    st.warning("⚠️ Are you sure you want to delete this entry? This cannot be undone.")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Yes, Delete", type="primary", use_container_width=True):
                            # Find and remove the entry
                            entries_to_keep = [e for e in entries if not (e['date'] == entry['date'] and e['book_title'] == entry['book_title'])]
                            save_data(entries_to_keep)
                            st.session_state.confirm_delete = False
                            st.success("✅ Entry deleted successfully!")
                            st.session_state.current_mode = None
                            st.rerun()
                    with col2:
                        if st.button("❌ Cancel", use_container_width=True):
                            st.session_state.confirm_delete = False
                            st.rerun()

            # Plot rating trend
            st.markdown("---")
            st.markdown("### 📈 Your Progress Over Time")
            
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
                latest_rating = rated_entries[-1]["rating"]
                improvement = latest_rating - rated_entries[0]["rating"]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Average Rating", f"{avg_rating:.1f}/10")
                with col2:
                    st.metric("Latest Rating", f"{latest_rating}/10")
                with col3:
                    improvement_text = f"+{improvement:.1f}" if improvement > 0 else f"{improvement:.1f}"
                    st.metric("Overall Progress", improvement_text)
                
            elif len(rated_entries) == 1:
                st.info("📊 Write more entries to see your progress trend!")
            else:
                st.info("📊 No ratings available for progress tracking.")

# Navigation buttons at the bottom
if st.session_state.current_mode is not None:
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🏠 Back to Main Menu", use_container_width=True):
            st.session_state.current_mode = None
            st.session_state.show_feedback = False
            st.session_state.current_entry = None
            st.session_state.confirm_delete = False
            st.rerun()

# Add sidebar with summary stats
if entries:
    st.sidebar.header("📊 Your Reading Journey")
    st.sidebar.metric("Total Entries", len(entries))
    
    rated_entries = [e for e in entries if e.get("rating") is not None]
    if rated_entries:
        avg_rating = sum(e["rating"] for e in rated_entries) / len(rated_entries)
        st.sidebar.metric("Average Rating", f"{avg_rating:.1f}/10")
        st.sidebar.metric("Rated Entries", len(rated_entries))
    
    # Show feedback type distribution for newer entries
    feedback_types = [e.get("feedback_type", "General") for e in entries if e.get("feedback_type")]
    if feedback_types:
        st.sidebar.subheader("📝 Focus Areas")
        unique_types = list(set(feedback_types))
        for ftype in unique_types:
            count = feedback_types.count(ftype)
            st.sidebar.text(f"• {ftype}: {count}")
    
    # Recent books
    if len(entries) > 0:
        st.sidebar.subheader("📚 Recent Books")
        for entry in list(reversed(entries))[:5]:
            rating_text = f" ({entry['rating']}/10)" if entry.get('rating') else ""
            st.sidebar.text(f"• {entry['book_title']}{rating_text}")

# Show welcome message when no mode is selected
if st.session_state.current_mode is None:
    st.markdown("---")
    st.markdown("""
    ### 🌟 Welcome to Your Reading Tool!
    
    This tool helps you:
    - ✍️ **Write about books** you've read
    - 🤖 **Get AI feedback** to improve your writing
    - 📈 **Track your progress** over time
    - 📚 **Review past entries** and see how you've grown
    
    Choose an option above to get started!
    """)
    
    if entries:
        st.info(f"📖 You have {len(entries)} entries in your reading journal!")
    else:
        st.info("📝 Start your reading journey by creating your first entry!")
