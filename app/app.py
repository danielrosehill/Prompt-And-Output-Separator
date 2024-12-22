import streamlit as st
import pandas as pd
import re
import time
import os
from io import StringIO
import pyperclip
import nltk
from openai import OpenAI
import json

# OpenAI configuration
if 'openai_api_key' not in st.session_state:
    st.session_state.openai_api_key = None

# Sidebar for API key configuration
with st.sidebar:
    st.markdown("## Configuration")
    api_key = st.text_input("Enter OpenAI API Key", type="password")
    if api_key:
        st.session_state.openai_api_key = api_key
        client = OpenAI(api_key=api_key)

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
                    Return ONLY a JSON object with two fields:
                    - prompt: the user's question or prompt
                    - output: the response or answer
                    If you cannot clearly identify both parts, set the unknown part to null."""
                },
                {
                    "role": "user",
                    "content": f"Please analyze this text and separate it into prompt and output: {text}"
                }
            ],
            temperature=0,
            response_format={ "type": "json_object" }
        )
        
        result = response.choices[0].message.content
        parsed = json.loads(result)
        return parsed.get("prompt"), parsed.get("output")
        
    except Exception as e:
        st.error(f"Error analyzing text: {str(e)}")
        return None, None

# Processing function
def separate_prompt_output(text):
    if not text:
        return "", ""
    
    # Use LLM if API key is available
    if st.session_state.openai_api_key:
        prompt, output = analyze_with_llm(text)
        if prompt is not None and output is not None:
            return prompt, output
    
    # Fallback to basic separation if LLM fails or no API key
    parts = text.split('\n\n', 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return text.strip(), ""

# Column processing function
def process_column(column):
    processed_data = []
    for item in column:
        prompt, output = separate_prompt_output(str(item))
        processed_data.append({"Prompt": prompt, "Output": output})
    return pd.DataFrame(processed_data)

# Download NLTK resources
nltk.download('punkt')

# Session state management
if 'history' not in st.session_state:
    st.session_state.history = []

if 'mode' not in st.session_state:
    st.session_state.mode = 'light'

# Styling
st.markdown("""
<style>
body {
    font-family: Arial, sans-serif;
    color: #333;
    background-color: #f4f4f9;
}
.stTextInput > div > div > input {
    font-size: 16px;
}
.stButton > button {
    font-size: 16px;
    padding: 0.5rem 1rem;
}
.stMarkdown {
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)

# Dark mode toggle
if st.sidebar.button("Toggle Dark Mode"):
    st.session_state.mode = 'dark' if st.session_state.mode == 'light' else 'light'

if st.session_state.mode == 'dark':
    st.markdown("""
    <style>
    body {
        color: #fff;
        background-color: #121212;
    }
    .stTextInput > div > div > input {
        color: #fff;
        background-color: #333;
    }
    .stButton > button {
        color: #fff;
        background-color: #6200ea;
    }
    .stMarkdown {
        color: #fff;
    }
    </style>
    """, unsafe_allow_html=True)

# Header
st.title("Prompt Output Separator")
st.markdown("A utility to separate user prompts from AI responses")

# Add API key status indicator
if st.session_state.openai_api_key:
    st.sidebar.success("✓ API Key configured")
else:
    st.sidebar.warning("⚠ No API Key provided - using basic separation")

# GitHub badge
st.sidebar.markdown("[![GitHub](https://img.shields.io/badge/GitHub-danielrosehill-blue?style=flat-square)](https://github.com/danielrosehill)")

# Tabs
tabs = st.tabs(["Manual Input", "File Processing"])

# Manual Input Tab
with tabs[0]:
    st.subheader("Manual Input")
    input_text = st.text_area("Enter text here", height=300)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Separate Now"):
            if input_text:
                st.session_state.history.append(input_text)
                prompt, output = separate_prompt_output(input_text)
                st.session_state.prompt = prompt
                st.session_state.output = output
            else:
                st.error("Please enter some text")

        if st.button("Clear"):
            st.session_state.prompt = ""
            st.session_state.output = ""
            input_text = ""

    with col2:
        st.text_area("Prompt", value=st.session_state.get('prompt', ""), height=150)
        st.text_area("Output", value=st.session_state.get('output', ""), height=150)

        if st.button("Copy Prompt to Clipboard"):
            pyperclip.copy(st.session_state.get('prompt', ""))
            st.success("Copied to clipboard")

        if st.button("Copy Output to Clipboard"):
            pyperclip.copy(st.session_state.get('output', ""))
            st.success("Copied to clipboard")

# File Processing Tab
with tabs[1]:
    st.subheader("File Processing")
    uploaded_files = st.file_uploader("Upload files", type=["txt", "md", "csv"], accept_multiple_files=True)

    if uploaded_files:
        for file in uploaded_files:
            file_content = file.read().decode("utf-8")
            if file.name.endswith(".csv"):
                df = pd.read_csv(StringIO(file_content))
                for col in df.columns:
                    processed_df = process_column(df[col])
                    st.write(f"Processed column: {col}")
                    st.write(processed_df)
            else:
                processed_text = separate_prompt_output(file_content)
                st.write("Processed text file:")
                st.write({"Prompt": processed_text[0], "Output": processed_text[1]})

# Footer
st.markdown("---")
st.write("Version 1.0.0")