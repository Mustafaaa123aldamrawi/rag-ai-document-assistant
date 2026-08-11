import streamlit as st

# Page configuration
st.set_page_config(
    page_title="RAG AI Document Assistant",
    page_icon="🤖",
    layout="wide"
)

# Application title
st.title("🤖 RAG AI Document Assistant")

st.write(
    "Upload a PDF document and ask questions about its content "
    "using Retrieval-Augmented Generation (RAG)."
)

# Sidebar
with st.sidebar:
    st.header("📄 Document Upload")

    uploaded_file = st.file_uploader(
        "Upload a PDF file",
        type=["pdf"]
    )

# Main interface
st.subheader("💬 Ask Your Document")

question = st.text_input(
    "Enter your question:",
    placeholder="Example: What are the main topics discussed in this document?"
)

if st.button("Ask AI"):
    if uploaded_file is None:
        st.warning("Please upload a PDF document first.")
    elif not question:
        st.warning("Please enter a question.")
    else:
        st.info("Document processing and RAG functionality will be added next.")
