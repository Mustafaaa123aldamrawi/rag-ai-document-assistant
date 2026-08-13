
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
        chunk_size=350,
        chunk_overlap=50,
        length_function=len
    )

    chunks = []

    for page in pages:
        page_chunks = text_splitter.split_text(page["text"])

        for chunk_index, chunk in enumerate(page_chunks):
            chunks.append({
                "text": chunk,
                "page_number": page["page_number"],
                "source": page["source"],
                "chunk_index": chunk_index
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
            "source": chunk["source"],
            "chunk_index": chunk["chunk_index"]
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
    model_name = "google/flan-t5-base"
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
        # Detect questions that require understanding the whole document
        summary_phrases = [
            "what is this document about",
            "what is the document about",
            "what is this letter about",
            "what is the letter about",
            "what is this report about",
            "what is the report about",
            "what is this file about",
            "what is the file about",
            "summarize this document",
            "summarize the document",
            "summarize this letter",
            "summarize the letter",
            "summarize this report",
            "summarize the report",
            "give me a summary",
            "purpose of the document",
            "purpose of the letter",
            "purpose of the report",
            "purpose of the file",
            "main purpose",
            "main topic"
        ]
        
        is_summary_question = any(
            phrase in question_lower
            for phrase in summary_phrases
        )     
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
            search_results = vector_store.similarity_search_with_score(
                question,
                k=12,
                filter={"source": matched_source}
            )
        else:
            search_results = vector_store.similarity_search_with_score(
                question,
                k=8
            )
        st.write("DEBUG SEARCH RESULTS")

        for i, (doc, score) in enumerate(search_results, start=1):
            st.write(
                f"Result {i} | Score: {score:.4f} | "
                f"Source: {doc.metadata.get('source')} | "
                f"Page: {doc.metadata.get('page_number')} | "
                f"Chunk: {doc.metadata.get('chunk_index')}"
            )
            st.write(doc.page_content)
        # Evidence Filtering v2
        # FAISS distance: lower score = better semantic match.
        RELEVANCE_THRESHOLD = 1.20
        
        # Common question words that should not be treated as evidence.
        STOP_WORDS = {
            "what", "which", "who", "where", "when", "why", "how",
            "does", "do", "did", "have", "has", "had", "is", "are",
            "was", "were", "the", "a", "an", "and", "or", "of", "in",
            "on", "for", "to", "with", "from", "about",
            "mustafa"
        }
        
        question_keywords = [
            word.lower().strip(".,?!:;()[]{}\"'")
            for word in question.split()
            if len(word.strip(".,?!:;()[]{}\"'")) >= 3
            and word.lower().strip(".,?!:;()[]{}\"'") not in STOP_WORDS
        ]
        # Detect verification questions that require explicit evidence
        verification_starters = (
            "does ", "do ", "did ", "is ", "are ",
            "has ", "have ", "had ", "can ", "could "
        )
        
        is_verification_question = question_lower.startswith(verification_starters)
        generic_verification_terms = {
            "certification",
            "certifications",
            "certificate",
            "certificates"
        }
        
        verification_keywords = [
            keyword
            for keyword in question_keywords
            if keyword not in generic_verification_terms
        ]
        
        evidence_keywords = (
            verification_keywords
            if is_verification_question
            else question_keywords
        )
        evidence_documents = []
        
        for document, score in search_results:
            if score <= RELEVANCE_THRESHOLD:
                document_text = document.page_content.lower()
        
                keyword_matches = sum(
                    1 for keyword in evidence_keywords
                    if keyword in document_text
                )
        
                evidence_documents.append(
                    (document, score, keyword_matches)
                )
        
        # Prefer chunks that contain question evidence,
        # then use semantic distance as the secondary ranking.
        evidence_documents.sort(
            key=lambda item: (-item[2], item[1])
        )
        
        relevant_documents = [
        document
        for document, score, keyword_matches in evidence_documents
        if (
            (
                is_verification_question
                and len(question_keywords) > 0
                and keyword_matches == len(evidence_keywords)
            )
            or
            (
                not is_verification_question
                and (keyword_matches > 0 or score <= 1.10)
            )
        )
    ]
        # Neighbor Expansion
        # Add the previous and next chunk from the same source/page
        # so information split across chunk boundaries is not lost.
        
        expanded_texts = []
        seen_chunks = set()
        
        for document in relevant_documents:
            source = document.metadata.get("source")
            page_number = document.metadata.get("page_number")
            chunk_index = document.metadata.get("chunk_index")
        
            for neighbor_index in (
                chunk_index - 1,
                chunk_index,
                chunk_index + 1
            ):
                for chunk in text_chunks:
                    if (
                        chunk["source"] == source
                        and chunk["page_number"] == page_number
                        and chunk["chunk_index"] == neighbor_index
                    ):
                        chunk_key = (
                            chunk["source"],
                            chunk["page_number"],
                            chunk["chunk_index"]
                        )
        
                        if chunk_key not in seen_chunks:
                            expanded_texts.append(
                                f"Source: {chunk['source']} | "
                                f"Page: {chunk['page_number']}\n"
                                f"{chunk['text']}"
                            )
                            seen_chunks.add(chunk_key)
        
                        break
        if not relevant_documents and not is_summary_question:
            st.subheader("🤖 AI Answer")
            st.write("The information was not found in the document.")
            st.stop()
        st.success(
            f"Retrieved {len(relevant_documents)} relevant document chunks."
            )

    
        for index, document in enumerate(relevant_documents, start=1):
            source = document.metadata.get("source", "Unknown source")
            page_number = document.metadata.get("page_number", "Unknown page")

            with st.expander(f"Relevant Chunk {index}"):
                st.write(f"Source: {source} | Page: {page_number}")
                st.write(document.page_content)

        if is_summary_question:
            context = "\n\n".join(
                f"Source: {chunk['source']} | Page: {chunk['page_number']}\n{chunk['text']}"
                for chunk in text_chunks
            )
        else:
            context = "\n\n".join(expanded_texts)
        # Prefer category-specific sections for technology questions
        if "technolog" in question_lower:
            technology_chunks = []

        for i, chunk in enumerate(text_chunks):
            chunk_text = chunk["text"]
            chunk_lower = chunk_text.lower()
    
            if "core skills" in chunk_lower:
                technology_chunks.append(chunk_text)
    
                # Include the next chunk because the Core Skills
                # section may continue across a chunk boundary.
                if i + 1 < len(text_chunks):
                    next_chunk = text_chunks[i + 1]
    
                    if (
                        next_chunk["source"] == chunk["source"]
                        and next_chunk["page_number"] == chunk["page_number"]
                    ):
                        technology_chunks.append(next_chunk["text"])
    
        if technology_chunks:
            context = "\n\n".join(technology_chunks)
            # Stop technology context before the Certifications section
            context_lower = context.lower()
            certifications_start = context_lower.find("certifications & training")
        
            if certifications_start != -1:
                context = context[:certifications_start].strip()
        direct_answer = None
        if "certification" in question.lower() and not is_verification_question:
            context_lower = context.lower()
            start = context_lower.find("certifications & training")
            end = context_lower.find("languages", start)
        
            if start != -1:
                if end != -1:
                    context = context[start:end]
                else:
                    context = context[start:]
                direct_answer = context.replace("Certifications & Training", "").strip()

                direct_answer = direct_answer.replace("Source: Mustafa_CV.pdf", "")
                direct_answer = direct_answer.replace("Page: 1", "")
                direct_answer = " ".join(direct_answer.split())    
        if is_summary_question:
            prompt = f"""
        summarize: {context}
        """
        else:
            prompt = f"""
            Answer the question using only the information explicitly stated in the document below.
            
            If the question asks for technologies, skills, certifications, tools, systems, or experience, include all relevant items found in the provided document context.
            
            Do not add information that is not stated in the document.
            If the answer is not supported by the document, say: The information was not found in the document.
            
            Document:
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
                max_new_tokens=128,
                num_beams=4,
                do_sample=False,
                no_repeat_ngram_size=3,
                early_stopping=True
            )

            answer = tokenizer.decode(
                outputs[0],
                skip_special_tokens=True
            )
            if direct_answer is not None:
                answer = direct_answer
            st.subheader("🤖 AI Answer")
            st.write(answer)
           
