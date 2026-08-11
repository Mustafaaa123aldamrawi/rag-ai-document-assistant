import streamlit as st
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter


def extract_text_from_pdf(pdf_file):
    """Extract text from all pages of an uploaded PDF file."""
    reader = PdfReader(pdf_file)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


def split_text_into_chunks(text):
    """Split document text into smaller overlapping chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    return text_splitter.split_text(text)


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

    if uploaded_file is not None:
        st.success("PDF uploaded successfully!")

# Process uploaded PDF
document_text = ""
text_chunks = []

if uploaded_file is not None:
    try:
        document_text = extract_text_from_pdf(uploaded_file)

        if document_text.strip():
            text_chunks = split_text_into_chunks(document_text)

            st.success(
                f"Document processed successfully — "
                f"{len(document_text):,} characters extracted."
            )

            st.info(
                f"Document divided into {len(text_chunks)} text chunks."
            )

        else:
            st.warning(
                "No readable text was found in this PDF."
            )

    except Exception as error:
        st.error(f"Error processing PDF: {error}")

# Main interface
st.subheader("💬 Ask Your Document")

question = st.text_input(
    "Enter your question:",
    placeholder="Example: What are the main topics discussed in this document?"
)

if st.button("Ask AI"):
    if uploaded_file is None:
        st.warning("Please upload a PDF document first.")

    elif not document_text.strip():
        st.warning("The uploaded PDF does not contain readable text.")

    elif not question:
        st.warning("Please enter a question.")

    else:
        st.info(
            f"PDF processing and chunking are working. "
            f"{len(text_chunks)} chunks are ready for vector embeddings."
        )
