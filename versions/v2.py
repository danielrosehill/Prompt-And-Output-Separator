import streamlit as st
import pandas as pd
from io import StringIO
import pyperclip
import openai

# Initialize session state variables
if 'history' not in st.session_state:
    st.session_state.history = []
if 'prompt' not in st.session_state:
    st.session_state.prompt = ""
if 'output' not in st.session_state:
    st.session_state.output = ""
if 'title' not in st.session_state:
    st.session_state.title = ""

# Custom CSS
st.markdown("""
    <style>
    .stats-text {
        font-size: 0.8rem;
        color: #666;
    }
    </style>
""", unsafe_allow_html=True)

def count_text_stats(text):
    words = len(text.split())
    chars = len(text)
    return words, chars

def separate_prompt_output(text):
    if not text:
        return "", "", ""
    
    if st.session_state.get('openai_api_key'):
        prompt, output = analyze_with_llm(text)
        if prompt is not None and output is not None:
            suggested_title = generate_title_with_llm(prompt, output)
            return suggested_title, prompt, output
    
    parts = text.split('\n\n', 1)
    if len(parts) == 2:
        return "Untitled Conversation", parts[0].strip(), parts[1].strip()
    return "Untitled Conversation", text.strip(), ""

def generate_title_with_llm(prompt, output):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Generate a short, concise title (max 6 words) that captures the main topic of this conversation."
                },
                {
                    "role": "user",
                    "content": f"Prompt: {prompt}\nOutput: {output}"
                }
            ],
            max_tokens=20,
            temperature=0.7
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return "Untitled Conversation"

def process_column(column):
    processed_data = []
    for item in column:
        title, prompt, output = separate_prompt_output(str(item))
        processed_data.append({"Title": title, "Prompt": prompt, "Output": output})
    return pd.DataFrame(processed_data)

# Main interface
st.title("✂️ Prompt Output Separator")
st.markdown("Utility to assist with separating prompts and outputs when they are recorded in a unified block of text. For cost-optimisation, uses GPT 3.5.")

# Tabs with icons
tabs = st.tabs(["📝 Paste Text", "📁 File Processing", "📊 History"])

# Paste Text Tab
with tabs[0]:
    st.subheader("Paste Prompt and Output")
    
    # Settings
    with st.expander("⚙️ Settings", expanded=False):
        auto_copy = st.checkbox("Automatically copy prompt to clipboard", value=False)
        st.text_input("OpenAI API Key (optional)", type="password", key="openai_api_key")
    
    # Input area with placeholder
    input_container = st.container()
    with input_container:
        input_text = st.text_area(
            "Paste your conversation here...",
            height=200,
            placeholder="Paste your conversation here. The tool will automatically separate the prompt from the output.",
            help="Enter the text you want to separate into prompt and output."
        )

    # Action buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Separate Now", use_container_width=True):
            if input_text:
                with st.spinner("Processing..."):
                    st.session_state.history.append(input_text)
                    title, prompt, output = separate_prompt_output(input_text)
                    st.session_state.title = title
                    st.session_state.prompt = prompt
                    st.session_state.output = output
                    if auto_copy:
                        pyperclip.copy(prompt)
            else:
                st.error("Please enter some text")
    
    with col2:
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.title = ""
            st.session_state.prompt = ""
            st.session_state.output = ""
            input_text = ""

    # Suggested Title Section
    st.markdown("### 📌 Suggested Title")
    title_area = st.text_area(
        "",
        value=st.session_state.get('title', ""),
        height=50,
        key="title_area",
        help="A suggested title based on the content"
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
        <p>Created by <a href="https://github.com/danielrosehill/Prompt-And-Output-Separator">Daniel Rosehill</a> and Claude Sonnet 3.5</p>
        <p><a href="https://github.com/danielrosehill/Prompt-And-Output-Separator" target="_blank">
            <img src="https://img.shields.io/github/stars/danielrosehill/Prompt-And-Output-Separator?style=social" alt="GitHub stars">
        </a></p>
    </div>
    """,
    unsafe_allow_html=True
)