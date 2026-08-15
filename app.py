
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
        
        is_summary_question = (
            any(
                phrase in question_lower
                for phrase in summary_phrases
            )
            or question_lower.startswith("summarize ")
            or question_lower.startswith("summarise ")
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
        if expanded_texts:
            context = "\n\n".join(expanded_texts)
        else:
            context = "\n\n".join(
                document.page_content for document in relevant_documents
            )
        if not relevant_documents and not is_summary_question:
            st.subheader("🤖 AI Answer")
            st.write("The information was not found in the document.")
            st.stop()
        
        if is_summary_question:
            full_document_text = "\n".join(
                page["text"] for page in document_pages
            )
        
            full_document_lower = full_document_text.lower()
            
            # For professional experience summaries, focus on the experience section
            if "professional experience" in question_lower:
                start = full_document_lower.find("professional experience")
        
                end_markers = [
                    "core skills",
                    "certifications & training",
                    "languages"
                ]
        
                end_positions = [
                    full_document_lower.find(marker, start)
                    for marker in end_markers
                    if full_document_lower.find(marker, start) != -1
                ]
        
                if start != -1:
                    if end_positions:
                        end = min(end_positions)
                        context = full_document_text[start:end].strip()
                    else:
                        context = full_document_text[start:].strip()
                else:
                    context = full_document_text
                # Clean professional experience context before summarization
                experience_lines = []
                
                for line in context.splitlines():
                    cleaned_line = line.strip(" •-\t")
                    cleaned_lower = cleaned_line.lower()
                
                    if (
                        "core skills" in cleaned_lower
                        or "certifications & training" in cleaned_lower
                        or cleaned_lower == "languages"
                    ):
                        break
                
                    if cleaned_line and len(cleaned_line.split()) >= 6:
                        experience_lines.append(cleaned_line)
                
                if experience_lines:
                    context = "\n".join(experience_lines)
            else:
                context = full_document_text
        else:
            context = "\n\n".join(expanded_texts)
            if "technolog" in question_lower:
                full_document_text = "\n".join(
                    page["text"] for page in document_pages
                )
            
                full_document_lower = full_document_text.lower()
            
                start = full_document_lower.find("core skills")
                end = full_document_lower.find("certifications & training", start)
            
                if start != -1:
                    if end != -1:
                        context = full_document_text[start:end]
                    else:
                        context = full_document_text[start:]
        direct_answer = None
        # Direct handling for job title questions
        job_title_phrases = [
            "job title",
            "current job title",
            "current title",
            "professional title",
            "what is mustafa's job",
            "what is mustafa’s job"
        ]

        if any(phrase in question_lower for phrase in job_title_phrases):
            full_document_text = "\n".join(
                page["text"] for page in document_pages
            )
        
            full_document_lower = full_document_text.lower()
        
            title_start = full_document_lower.find("project manager")
            title_end = full_document_lower.find("saudi arabia", title_start)
        
            if title_start != -1:
                if title_end != -1:
                    direct_answer = full_document_text[title_start:title_end].strip()
                else:
                    direct_answer = "Project Manager"
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
                # Direct extractive answer for technologies and technical skills
        if (
            "technolog" in question_lower
            or "technical skill" in question_lower
            or "tools" in question_lower
            or "platforms" in question_lower
            or "systems" in question_lower
        ):
            full_document_text = "\n".join(
                page["text"] for page in document_pages
            )
        
            full_document_lower = full_document_text.lower()
        
            start = full_document_lower.find("core skills")
            end = full_document_lower.find("certifications & training", start)
        
            if start != -1:
                if end != -1:
                    technology_text = full_document_text[start:end]
                else:
                    technology_text = full_document_text[start:]
        
                technology_text = technology_text.replace("Core Skills", "").strip()
                
                technology_items = [
                    item.strip()
                    for item in technology_text.split(",")
                    if item.strip()
                ]
                
                excluded_items = {
                    "project management",
                    "leadership",
                    "ai for project management",
                    "education technology",
                    "cybersecurity fundamentals"
                }
                
                technical_items = [
                    item
                    for item in technology_items
                    if item.lower() not in excluded_items
                ]
                
                direct_answer = ", ".join(technical_items)
                
                # Direct extractive answer for professional experience
            if "professional experience" in question_lower:
                full_document_text = "\n".join(
                    page["text"] for page in document_pages
                )
            
                full_document_lower = full_document_text.lower()
            
                start = full_document_lower.find("professional experience")
                end = full_document_lower.find("core skills", start)
            
                if start != -1:
                    if end != -1:
                        experience_text = full_document_text[start:end]
                    else:
                        experience_text = full_document_text[start:]
            
                    experience_lines = []
            
                    for line in experience_text.splitlines():
                        clean_line = line.strip(" •-\t")
            
                        if (
                            clean_line
                            and "professional experience" not in clean_line.lower()
                            and "email:" not in clean_line.lower()
                            and "phone:" not in clean_line.lower()
                            and len(clean_line.split()) >= 6
                            and clean_line.endswith((".", "!", "?"))
                        ):
                            experience_lines.append(clean_line)
            
                    if experience_lines:
                        direct_answer = " ".join(experience_lines[:6])
                        
        if is_summary_question:
            prompt = f"""
        Context:
        {context}
        
        Based only on the context above, answer the following question.
        
        Question: {question}
        
        Answer with 3 complete sentences describing Mustafa's professional experience.
        Do not repeat or rephrase the question.
        Do not write a question.
        Do not include certifications or languages.
        
        Answer:
        """
        else:
            prompt = f"""
            Use the context below to answer the user's question directly.
            
            Question:
            {question}
            
            Context:
            {context}
            
            Instructions:
            - Give a clear and concise answer in 1 to 3 complete sentences.
            - Answer only what the user asked.
            - Do not copy source names, file names, page numbers, or metadata into the answer.
            - Do not repeat the question.
            - Do not list unrelated information.
            - Use only information supported by the context.
            - If the context does not contain enough information, say: The information was not found in the document.
            
            Answer:
            """
        
        if direct_answer is not None:
            answer = direct_answer
        else:
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
                    max_new_tokens=200,
                    num_beams=1,
                    do_sample=False,
                    no_repeat_ngram_size=3,
                    early_stopping=True
                )
        
                answer = tokenizer.decode(
                    outputs[0],
                    skip_special_tokens=True
                )
        
        st.subheader("🤖 AI Answer")
        st.write(answer)
                   
