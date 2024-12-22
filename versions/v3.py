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
        return None, None, None
    try:
        client = OpenAI(api_key=st.session_state.openai_api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {
                    "role": "system",
                    "content": """You are a text analysis expert. Your task is to separate a conversation into the prompt/question and the response/answer. Return ONLY a JSON object with three fields: - title: a short, descriptive title for the conversation (max 6 words) - prompt: the user's question or prompt - output: the response or answer If you cannot clearly identify any part, set it to null."""
                },
                {
                    "role": "user",
                    "content": f"Please analyze this text and separate it into title, prompt and output: {text}"
                }
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        result = response.choices[0].message.content
        parsed = json.loads(result)
        return parsed.get("title"), parsed.get("prompt"), parsed.get("output")
    except Exception as e:
      st.error(f"Error analyzing text: {str(e)}. The error was: {e}")
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

    # Dark mode toggle using checkbox
    st.markdown("---")
    st.markdown("## 🎨 Appearance")
    dark_mode = st.checkbox("Dark Mode", value=st.session_state.mode == 'dark')
    st.session_state.mode = 'dark' if dark_mode else 'light'

# Main interface
st.title("✂️ Prompt Output Separator")
st.markdown(
    "Utility to assist with separating prompts and outputs when they are recorded in a unified block of text. For cost-optimisation, uses GPT 3.5.")

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
    uploaded_file = st.file_uploader("Choose a file", type=['txt', 'csv'])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.type == "text/csv":
                df = pd.read_csv(uploaded_file)
                column = st.selectbox("Select column to process", df.columns)
                if st.button("Process CSV"):
                    with st.spinner("Processing..."):
                        processed_df = process_column(df[column])
                        st.write(processed_df)
                        st.download_button(
                            "Download Processed CSV",
                            processed_df.to_csv(index=False),
                            "processed_data.csv",
                            "text/csv"
                        )
            else:
                content = uploaded_file.getvalue().decode("utf-8")
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

# Custom CSS for stats text to prevent them from overlapping
st.markdown("""
<style>
.stats-text {
    text-align: left;
    font-size: 0.8em;
    color: #888; /* Darker gray to fit the style */
    margin-top: -10px; /* push the stats closer to the textarea */
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# Custom CSS to style dark mode
if st.session_state.mode == 'dark':
    st.markdown("""
    <style>
        body {
            color: #fff;
            background-color: #262730;
        }
        .stTextInput, .stTextArea, .stNumberInput, .stSelectbox, .stRadio, .stCheckbox, .stSlider, .stDateInput, .stTimeInput {
            background-color: #3d3d4d; /* Darker background for input widgets */
            color: #fff; /* White text for better contrast */
        }
       .stButton>button {
            background-color: #5c5c7a; /* Adjust button color */
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

        .st-ba {
            background-color: #3d3d4d; /* Makes the body background dark */
            color: #fff;
        }
        
        .css-10trblm {
            background-color: #3d3d4d;
             color: #fff;
        }
        
        .css-qbe2hs {
            color: #fff;
        }
        
        .css-1wtrr7o {
            color: #fff;
        }
        
        .css-103n16l {
            color: #fff;
        }
        
        .css-10pw50 {
             color: #fff;
        }
        
        .css-z5fcl4 {
           color: #fff;
        }
        .css-1d391kg {
            color: #fff;
        }
    </style>
    """, unsafe_allow_html=True)