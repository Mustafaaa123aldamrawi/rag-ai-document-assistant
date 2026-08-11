
import streamlit as st
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from transformers import pipeline

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


def create_vector_store(text_chunks):
    """Create a FAISS vector store from document chunks."""
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vector_store = FAISS.from_texts(
        text_chunks,
        embedding=embeddings
    )

    return vector_store
@st.cache_resource
def load_llm():
    """Load a lightweight local language model."""
    return pipeline(
        "text2text-generation",
        model="google/flan-t5-small",
        max_new_tokens=256
    )

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
vector_store = None

if uploaded_file is not None:
    try:
        document_text = extract_text_from_pdf(uploaded_file)

        if document_text.strip():
            text_chunks = split_text_into_chunks(document_text)

            st.success(
                f"Document processed successfully - "
                f"{len(document_text):,} characters extracted."
            )

            st.info(
                f"Document divided into {len(text_chunks)} text chunks."
            )

            vector_store = create_vector_store(text_chunks)

            st.success(
                "Vector embeddings created successfully using Hugging Face."
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

    elif vector_store is None:
        st.warning(
            "Vector database is not ready. Configure the OpenAI API key first."
        )

    else:
        relevant_documents = vector_store.similarity_search(
            question,
            k=4
        )

        st.success(
            f"Retrieved {len(relevant_documents)} relevant document chunks."
        )

        for index, document in enumerate(relevant_documents, start=1):
            with st.expander(f"Relevant Chunk {index}"):
                st.write(document.page_content)

   context = "\n\n".join(
            document.page_content for document in relevant_documents
        )

        prompt = f"""
Answer the question using only the document context below.

Context:
{context}

Question:
{question}

Answer:
"""

        with st.spinner("AI is analyzing the document..."):
            llm = load_llm()
            result = llm(prompt)

        st.subheader("🤖 AI Answer")
        st.write(result[0]["generated_text"])
