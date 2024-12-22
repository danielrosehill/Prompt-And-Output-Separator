import streamlit as st
import pandas as pd
import re
import time
import os
from io import StringIO
import pyperclip
from openai import OpenAI
import json

# Page Configuration
st.set_page_config(
    page_title="Prompt Output Separator",
    page_icon="✂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = None
if 'history' not in st.session_state:
    st.session_state.history = []
if 'prompt' not in st.session_state:
    st.session_state.prompt = ""
if 'output' not in st.session_state:
    st.session_state.output = ""
if 'title' not in st.session_state:
    st.session_state.title = ""
if 'mode' not in st.session_state:
    st.session_state.mode = 'light'

def count_text_stats(text):
    words = len(text.split())
    chars = len(text)
    return words, chars

def analyze_with_llm(text):
    if not st.session_state.openai_api_key:
        st.error("Please provide an OpenAI API key in the sidebar")
        return None, None
        
    try:
        client = OpenAI(api_key=st.session_state.openai_api_key)
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {
                    "role": "system",
                    "content": """You are a text analysis expert. Your task is to separate a conversation into the prompt/question and the response/answer. 
                    Return ONLY a JSON object with three fields:
                    - title: a short, descriptive title for the conversation (max 6 words)
                    - prompt: the user's question or prompt
                    - output: the response or answer
                    If you cannot clearly identify any part, set it to null."""
                },
                {
                    "role": "user",
                    "content": f"Please analyze this text and separate it into title, prompt and output: {text}"
                }
            ],
            temperature=0,
            response_format={ "type": "json_object" }
        )
        
        result = response.choices[0].message.content
        parsed = json.loads(result)
        return parsed.get("title"), parsed.get("prompt"), parsed.get("output")
        
    except Exception as e:
        st.error(f"Error analyzing text: {str(e)}")
        return None, None, None

def separate_prompt_output(text):
    if not text:
        return "", "", ""
    
    if st.session_state.openai_api_key:
        title, prompt, output = analyze_with_llm(text)
        if all(v is not None for v in [title, prompt, output]):
            return title, prompt, output
    
    parts = text.split('\n\n', 1)
    if len(parts) == 2:
        return "Untitled Conversation", parts[0].strip(), parts[1].strip()
    return "Untitled Conversation", text.strip(), ""

def process_column(column):
    processed_data = []
    for item in column:
        title, prompt, output = separate_prompt_output(str(item))
        processed_data.append({"Title": title, "Prompt": prompt, "Output": output})
    return pd.DataFrame(processed_data)

# Sidebar configuration
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/chat.png", width=50)
    st.markdown("## 🛠️ Configuration")
    api_key = st.text_input("Enter OpenAI API Key", type="password")
    if api_key:
        st.session_state.openai_api_key = api_key

    # Dark mode toggle
    st.markdown("---")
    st.markdown("## 🎨 Appearance")
    dark_mode = st.toggle("Dark Mode", value=st.session_state.mode == 'dark')
    st.session_state.mode = 'dark' if dark_mode else 'light'
    
    # Settings section
    st.markdown("---")
    st.markdown("## ⚙️ Settings")
    auto_copy = st.checkbox("Auto-copy results to clipboard", value=False)
    
    if st.session_state.openai_api_key:
        st.success("✓ API Key configured")
    else:
        st.warning("⚠ No API Key provided - using basic separation")

# Main interface
st.title("✂️ Prompt Output Separator")
st.markdown("Utility to assist with separating prompts and outputs when they are recorded in a unified block of text. For cost-optimisation, uses GPT 3.5.")

# Tabs with icons
tabs = st.tabs(["📝 Paste Text", "📁 File Processing", "📊 History"])

# Paste Text Tab
with tabs[0]:
    st.subheader("Paste Prompt and Output")
    
    # Input area with placeholder
    input_container = st.container()
    with input_container:
        input_text = st.text_area(
            "Paste your conversation here...",
            height=200,
            placeholder="Paste your conversation here. The tool will automatically separate the prompt from the output.",
            help="Enter the text you want to separate into prompt and output."
        )

    # Process button
    if st.button("🔄 Process", use_container_width=True) and input_text:
        with st.spinner("Processing..."):
            title, prompt, output = separate_prompt_output(input_text)
            st.session_state.title = title
            st.session_state.prompt = prompt
            st.session_state.output = output
            st.session_state.history.append(input_text)

    # Suggested Title Section
    st.markdown("### 📌 Suggested Title")
    title_area = st.text_area(
        "",
        value=st.session_state.get('title', ""),
        height=70,
        key="title_area",
        help="AI-generated title based on the conversation content"
    )

    # Prompt Section
    st.markdown("### 📝 Prompt")
    prompt_area = st.text_area(
        "",
        value=st.session_state.get('prompt', ""),
        height=200,
        key="prompt_area",
        help="The extracted prompt will appear here"
    )
    # Display prompt stats
    prompt_words, prompt_chars = count_text_stats(st.session_state.get('prompt', ""))
    st.markdown(f"<p class='stats-text'>Words: {prompt_words} | Characters: {prompt_chars}</p>", unsafe_allow_html=True)
    
    if st.button("📋 Copy Prompt", use_container_width=True):
        pyperclip.copy(st.session_state.get('prompt', ""))
        st.success("Copied prompt to clipboard!")

    # Output Section
    st.markdown("### 🤖 Output")
    output_area = st.text_area(
        "",
        value=st.session_state.get('output', ""),
        height=200,
        key="output_area",
        help="The extracted output will appear here"
    )
    # Display output stats
    output_words, output_chars = count_text_stats(st.session_state.get('output', ""))
    st.markdown(f"<p class='stats-text'>Words: {output_words} | Characters: {output_chars}</p>", unsafe_allow_html=True)
    
    if st.button("📋 Copy Output", use_container_width=True):
        pyperclip.copy(st.session_state.get('output', ""))
        st.success("Copied output to clipboard!")

# File Processing Tab
with tabs[1]:
    st.subheader("File Processing")
    uploaded_files = st.file_uploader(
        "Upload files",
        type=["txt", "md", "csv"],
        accept_multiple_files=True,
        help="Upload text files to process multiple conversations at once"
    )

    if uploaded_files:
        for file in uploaded_files:
            with st.expander(f"📄 {file.name}", expanded=True):
                file_content = file.read().decode("utf-8")
                if file.name.endswith(".csv"):
                    df = pd.read_csv(StringIO(file_content))
                    for col in df.columns:
                        processed_df = process_column(df[col])
                        st.write(f"Processed column: {col}")
                        st.dataframe(
                            processed_df,
                            use_container_width=True,
                            hide_index=True
                        )
                else:
                    title, prompt, output = separate_prompt_output(file_content)
                    st.json({
                        "Title": title,
                        "Prompt": prompt,
                        "Output": output
                    })

# History Tab
with tabs[2]:
    st.subheader("Processing History")
    if st.session_state.history:
        if st.button("🗑️ Clear History", type="secondary"):
            st.session_state.history = []
            st.experimental_rerun()
            
        for idx, item in enumerate(reversed(st.session_state.history)):
            with st.expander(f"Entry {len(st.session_state.history) - idx}", expanded=False):
                st.text_area(
                    "Content",
                    value=item,
                    height=150,
                    key=f"history_{idx}",
                    disabled=True
                )
    else:
        st.info("💡 No processing history available yet. Process some text to see it here.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
        <p>Created by <a href="https://github.com/danielrosehill/Prompt-And-Output-Separator">Daniel Rosehill</a></p>
    </div>
    """,
    unsafe_allow_html=True
)

# Apply theme
if st.session_state.mode == 'dark':
    st.markdown("""
    <style>
    body {
        color: #fff;
        background-color: #0e1117;
    }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        color: #fff;
        background-color: #262730;
        border-radius: 8px;
        border: 1px solid #464646;
        padding: 15px;
        font-family: 'Courier New', monospace;
    }
    .stButton > button {
        color: #fff;
        background-color: #4c4cff;
        border-radius: 8px;
        padding: 10px 20px;
        transition: all 0.3s ease;
        border: none;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #6b6bff;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(76, 76, 255, 0.3);
    }
    .stMarkdown {
        color: #fff;
    }
    .stats-text {
        color: #999;
        font-size: 0.8em;
        margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <style>
    body {
        color: #333;
        background-color: #fff;
    }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        color: #333;
        background-color: #f8f9fa;
        border-radius: 8px;
        border: 1px solid #e0e0e0;
        padding: 15px;
        font-family: 'Courier New', monospace;
    }
    .stButton > button {
        color: #fff;
        background-color: #4c4cff;
        border-radius: 8px;
        padding: 10px 20px;
        transition: all 0.3s ease;
        border: none;
        width: 100%;
    }
    .stButton > button:hover {
        background-color: #6b6bff;
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(76, 76, 255, 0.3);
    }
    .stats-text {
        color: #666;
        font-size: 0.8em;
        margin-top: 5px;
    }
    </style>
    """, unsafe_allow_html=True)