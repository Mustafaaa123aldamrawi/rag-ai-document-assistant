
import streamlit as st
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

def extract_text_from_pdf(pdf_file):
    """Extract text page by page and preserve page numbers."""
    reader = PdfReader(pdf_file)
    pages = []
    source_name = getattr(pdf_file, "name", "Uploaded PDF")
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()

        if page_text:
            pages.append({
    "page_number": page_number,
    "source": source_name,
    "text": page_text
})

    return pages


def split_text_into_chunks(pages):
    """Split each PDF page into chunks while preserving page numbers."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )

    chunks = []

    for page in pages:
        page_chunks = text_splitter.split_text(page["text"])

        for chunk in page_chunks:
            chunks.append({
    "text": chunk,
    "page_number": page["page_number"],
    "source": page["source"]
})

    return chunks


def create_vector_store(text_chunks):
    """Create a FAISS vector store while preserving source metadata."""
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    texts = [
    f"Source: {chunk['source']}\nPage: {chunk['page_number']}\n{chunk['text']}"
    for chunk in text_chunks
]

    metadatas = [
        {
            "page_number": chunk["page_number"],
            "source": chunk["source"]
        }
        for chunk in text_chunks
    ]

    vector_store = FAISS.from_texts(
        texts,
        embedding=embeddings,
        metadatas=metadatas
    )

    return vector_store
@st.cache_resource
def load_llm():
    """Load the FLAN-T5 tokenizer and model."""
    model_name = "google/flan-t5-small"

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    return tokenizer, model

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

    uploaded_files = st.file_uploader(
    "Upload PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

    if uploaded_files:
        st.success(f"{len(uploaded_files)} PDF file(s) uploaded successfully!")

# Process uploaded PDF
document_pages = []
text_chunks = []
vector_store = None

if uploaded_files:
    try:
        for uploaded_file in uploaded_files:
            file_pages = extract_text_from_pdf(uploaded_file)
            document_pages.extend(file_pages)
        if document_pages:
            text_chunks = split_text_into_chunks(document_pages)

            st.success(
                f"Document processed successfully - "
                f"{sum(len(page['text']) for page in document_pages):,} characters extracted."
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
    if not uploaded_files:
        st.warning("Please upload at least one PDF document first.")

    elif not document_pages:
        st.warning("The uploaded PDF files do not contain readable text.")

    elif not question:
        st.warning("Please enter a question.")

    elif vector_store is None:
        st.warning("Vector database is not ready.")

    else:
        question_lower = question.lower()
        matched_source = None
        
        for uploaded_file in uploaded_files:
            source_name = uploaded_file.name
            source_words = (
                source_name
                .replace(".pdf", "")
                .replace("_", " ")
                .replace("-", " ")
                .lower()
                .split()
            )
        
            if any(
                len(word) > 2 and word in question_lower
                for word in source_words
            ):
                matched_source = source_name
                break
        
        if matched_source:
            relevant_documents = vector_store.similarity_search(
                question,
                k=12,
                filter={"source": matched_source}
            )
        else:
            relevant_documents = vector_store.similarity_search(
                question,
                k=4
            )
        question_keywords = [
                    word.lower().strip(".,?!:;\"'")
                    for word in question.split()
                    if len(word.strip(".,?!:;\"'")) > 5
                ]
        
        relevant_documents = sorted(
            relevant_documents,
            key=lambda doc: sum(
                keyword in doc.page_content.lower()
                for keyword in question_keywords
            ),
            reverse=True
        )
        st.success(
            f"Retrieved {len(relevant_documents)} relevant document chunks."
            )

    
        for index, document in enumerate(relevant_documents, start=1):
            source = document.metadata.get("source", "Unknown source")
            page_number = document.metadata.get("page_number", "Unknown page")

        with st.expander(f"Relevant Chunk {index}"):
            st.write(f"Source: {source} | Page: {page_number}")
            st.write(document.page_content)

        context = "\n\n".join(
            document.page_content for document in relevant_documents
        )

        prompt = f"""
You are a precise document question-answering assistant.

Use ONLY the information in the provided document context.

Rules:
- Carefully search the entire provided context before answering.
- Answer only what the user asked.
- Do not include unrelated skills, technologies, job titles, or experience.
- Do not guess or invent information.
- If the answer is not clearly present in the context, say:
  "The information was not found in the document."
- Keep the answer clear and concise.

Document context:
{context}

Question:
{question}

Answer:
"""

        with st.spinner("AI is analyzing the document..."):
            tokenizer, model = load_llm()

            inputs = tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=1024
            )

            outputs = model.generate(
                **inputs,
                max_new_tokens=256
            )

            answer = tokenizer.decode(
                outputs[0],
                skip_special_tokens=True
            )

        st.subheader("🤖 AI Answer")
        st.write(answer)
           
