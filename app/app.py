import streamlit as st
import pandas as pd
import re
import time
import os
from io import StringIO
import pyperclip
import json
import requests

st.set_page_config(page_title="Prompt Output Separator", page_icon="✂️", layout="wide", initial_sidebar_state="expanded")

if 'api_key' not in st.session_state:
    st.session_state.api_key = None
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
    if not st.session_state.api_key:
        st.error("Please provide an OpenAI API key in the sidebar")
        return None, None, None
    try:
        headers = {
            "Authorization": f"Bearer {st.session_state.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "system",
                    "content": """You are a text separator. Your ONLY job is to split the input text into its original prompt and response components. 
                    
CRITICAL RULES:
- DO NOT summarize or modify ANY text
- Return the EXACT original text split into two parts
- Make NO changes to the content
- Preserve ALL formatting and whitespace

Return ONLY a JSON object with these fields:
- title: brief descriptive title (max 6 words)
- prompt: the EXACT, COMPLETE first part of the conversation
- output: the EXACT, COMPLETE response/answer part"""
                },
                {
                    "role": "user",
                    "content": f"Split this text into its original parts with NO modifications: {text}"
                }
            ],
            "temperature": 0
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()['choices'][0]['message']['content']
            try:
                parsed = json.loads(result)
                # Verify no content was lost
                original_words = len(text.split())
                result_words = len((parsed.get("prompt", "") + parsed.get("output", "")).split())
                if result_words < original_words * 0.9:  # Allow for 10% difference due to splitting
                    st.error("Content was modified during processing. Using basic split instead.")
                    parts = text.split('\n\n', 1)
                    if len(parts) == 2:
                        return "Untitled Conversation", parts[0].strip(), parts[1].strip()
                    return "Untitled Conversation", text.strip(), ""
                return parsed.get("title"), parsed.get("prompt"), parsed.get("output")
            except json.JSONDecodeError:
                st.error("Failed to parse LLM response as JSON")
                return None, None, None
        else:
            st.error(f"API request failed with status code: {response.status_code}")
            st.error(f"Response: {response.text}")
            return None, None, None
            
    except Exception as e:
        st.error(f"Error analyzing text: {str(e)}")
        return None, None, None

def separate_prompt_output(text):
    if not text:
        return "", "", ""
    if st.session_state.api_key:
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

with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/chat.png", width=50)
    st.markdown("## 🛠️ Configuration")
    api_key = st.text_input("Enter OpenAI API Key", type="password", help="Get your API key from platform.openai.com")
    if api_key:
        st.session_state.api_key = api_key

    st.markdown("---")
    st.markdown("## 🎨 Appearance")
    dark_mode = st.checkbox("Dark Mode", value=st.session_state.mode == 'dark')
    st.session_state.mode = 'dark' if dark_mode else 'light'

st.title("✂️ Prompt Output Separator")
st.markdown("Utility to assist with separating prompts and outputs when they are recorded in a unified block of text.")

tabs = st.tabs(["📝 Paste Text", "📁 File Processing", "📊 History"])

with tabs[0]:
    st.subheader("Paste Prompt and Output")
    
    input_container = st.container()
    
    with input_container:
        input_text = st.text_area("Paste your conversation here...", height=200, placeholder="Paste your conversation here. The tool will automatically separate the prompt from the output.", help="Enter the text you want to separate into prompt and output.")
        
        if st.button("🔄 Process", use_container_width=True) and input_text:
            with st.spinner("Processing..."):
                title, prompt, output = separate_prompt_output(input_text)
                st.session_state.title = title
                st.session_state.prompt = prompt
                st.session_state.output = output
                st.session_state.history.append(input_text)
    
    st.markdown("### 📌 Suggested Title")
    title_area = st.text_area("", value=st.session_state.get('title', ""), height=70, key="title_area", help="AI-generated title based on the conversation content")

    st.markdown("### 📝 Prompt")
    prompt_area = st.text_area("", value=st.session_state.get('prompt', ""), height=200, key="prompt_area", help="The extracted prompt will appear here")
    prompt_words, prompt_chars = count_text_stats(st.session_state.get('prompt', ""))
    st.markdown(f"<p class='stats-text'>Words: {prompt_words} | Characters: {prompt_chars}</p>", unsafe_allow_html=True)
    
    if st.button("📋 Copy Prompt", use_container_width=True):
        pyperclip.copy(st.session_state.get('prompt', ""))
        st.success("Copied prompt to clipboard!")

    st.markdown("### 🤖 Output")
    output_area = st.text_area("", value=st.session_state.get('output', ""), height=200, key="output_area", help="The extracted output will appear here")
    output_words, output_chars = count_text_stats(st.session_state.get('output', ""))
    st.markdown(f"<p class='stats-text'>Words: {output_words} | Characters: {output_chars}</p>", unsafe_allow_html=True)
    
    if st.button("📋 Copy Output", use_container_width=True):
        pyperclip.copy(st.session_state.get('output', ""))
        st.success("Copied output to clipboard!")

with tabs[1]:
    st.subheader("Process File")
    uploaded_file = st.file_uploader("Choose a file", type=['txt', 'csv'])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.type == "text/csv":
                df = pd.read_csv(uploaded_file)
                st.write("Select the column containing the conversations:")
                column = st.selectbox("Column", df.columns.tolist())
                if st.button("Process CSV"):
                    with st.spinner("Processing..."):
                        result_df = process_column(df[column])
                        st.write(result_df)
                        st.download_button(
                            "Download Processed CSV",
                            result_df.to_csv(index=False).encode('utf-8'),
                            "processed_conversations.csv",
                            "text/csv",
                            key='download-csv'
                        )
            else:
                content = StringIO(uploaded_file.getvalue().decode("utf-8")).read()
                if st.button("Process Text File"):
                    with st.spinner("Processing..."):
                        title, prompt, output = separate_prompt_output(content)
                        st.session_state.title = title
                        st.session_state.prompt = prompt
                        st.session_state.output = output
                        st.session_state.history.append(content)
                        st.experimental_rerun()
                        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

with tabs[2]:
    st.subheader("Processing History")
    if st.session_state.history:
        if st.button("🗑️ Clear History", type="secondary"):
            st.session_state.history = []
            st.experimental_rerun()
            
        for idx, item in enumerate(reversed(st.session_state.history)):
            with st.expander(f"Entry {len(st.session_state.history) - idx}", expanded=False):
                st.text_area("Content", value=item, height=150, key=f"history_{idx}", disabled=True)
    else:
        st.info("💡 No processing history available yet. Process some text to see it here.")

st.markdown("---")
st.markdown("<div style='text-align: center'><p>Created by <a href='https://github.com/danielrosehill/Prompt-And-Output-Separator'>Daniel Rosehill</a></p></div>", unsafe_allow_html=True)

if st.session_state.mode == 'dark':
    st.markdown("""
    <style>
        body {
            color: #fff;
            background-color: #262730;
        }
        .stTextInput, .stTextArea, .stNumberInput, .stSelectbox, .stRadio, .stCheckbox, .stSlider, .stDateInput, .stTimeInput {
            background-color: #3d3d4d;
            color: #fff;
        }
       .stButton>button {
            background-color: #5c5c7a;
            color: white;
        }
         .stButton>button:hover {
            background-color: #6e6e8a;
            color: white;
        }
        
        .streamlit-expanderHeader {
            background-color: #3d3d4d !important;
            color: #fff !important;
        }
        
         .streamlit-expanderContent {
             background-color: #3d3d4d !important;
        }
        
        .streamlit-container {
             background-color: #262730;
         }
        
        .stAlert {
            background-color: #3d3d4d !important;
            color: #fff !important;
        }
        
        .stats-text {
            color: #aaa !important;
        }
        
        .css-10trblm {
            color: #fff !important;
        }
        
        .css-16idsys {
            color: #fff !important;
        }
        
        .css-1vq4p4l {
            color: #fff !important;
        }
    </style>
    """, unsafe_allow_html=True)