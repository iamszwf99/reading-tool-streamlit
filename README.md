# 📚 Reading Tool for Kids

This is a Streamlit app to help children improve their reading comprehension through AI-assisted feedback.

## Features

- Input a book title, date, and your own summary.
- Get a 500-word sample summary, a rating (1–10), and an explanation from ChatGPT.
- Save both summaries.
- View past entries and see a chart of your rating trend.

## Setup

1. Clone this repo.
2. Create `.streamlit/secrets.toml` with your OpenAI API key:

```toml
OPENAI_API_KEY = "your-api-key-here"
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the app:

```bash
streamlit run app.py
```