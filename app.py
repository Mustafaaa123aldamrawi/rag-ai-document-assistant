
import streamlit as st
import requests
import os
import re
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
def call_qwen_llm(prompt):
    url = "https://router.huggingface.co/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {st.secrets['HF_TOKEN']}",
        "Content-Type": "application/json"
    }
    models_url = "https://router.huggingface.co/v1/models"

    models_response = requests.get(
        models_url,
        headers=headers,
        timeout=30
    )
    
    if not models_response.ok:
        raise Exception(
            f"Hugging Face models API error "
            f"{models_response.status_code}: {models_response.text}"
        )
    
    models_data = models_response.json().get("data", [])
    
    preferred_models = [
        "google/gemma-2-2b-it",
        "Qwen/Qwen2.5-Coder-32B-Instruct",
        "openai/gpt-oss-20b",
    ]
    
    available_model_ids = {
        model.get("id")
        for model in models_data
        if model.get("id")
    }
    
    selected_model = next(
        (
            model_id
            for model_id in preferred_models
            if model_id in available_model_ids
        ),
        None
    )
    
    if selected_model is None:
        raise Exception(
            "No compatible non-thinking chat model is currently available."
        )
    payload = {
        "model": selected_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strictly document-grounded AV technical assistant. "
                    "Your answer must be based ONLY on facts explicitly stated in the provided context. "
                    "Do not use prior knowledge, product knowledge, assumptions, or inferred specifications. "
                    "Every technical claim in your answer must be directly supported by the context. "
                    "Do not invent a product category, purpose, capability, specification, application, or feature. "
                    "For 'What is' questions, identify the product only as specifically as the context allows, "
                    "then summarize only features or information explicitly stated in the context. "
                    "If the context identifies the product name but does not explicitly describe what type of device it is, "
                    "do not guess the device type. "
                    "If the product or subject is explicitly mentioned in the context, relevant information exists. "
                    "Use the facts located near that product or subject to construct a useful answer, even if the document does not contain a formal definition. "
                    "Do not return 'The information was not found in the document.' when the product or subject name appears in the context with related facts. "
                    "Only say 'The information was not found in the document.' when the context contains no relevant information at all. "
                    "Never add information from your training knowledge even if you know the product. "
                    "Product names and model numbers in extracted PDF text may contain accidental spaces or formatting artifacts. "
                    "Treat obvious spacing variations in the same alphanumeric model identifier as the same product, "
                    "for example '110f' and '1 10f', when the surrounding context clearly refers to the same model. "
                    "Do not transform a status field, displayed value, or monitored value into a product capability or feature. "
                    "Do not claim that a product supports, provides, updates, controls, or performs something unless the context explicitly states that capability. "
                    "Preserve the meaning of technical terms exactly; for example, a displayed firmware version does not mean firmware updates. "
                    "When paraphrasing technical information, use wording that does not introduce any new capability, behavior, or specification. "
                    "Do not generalize specific status or configuration fields into broader capabilities. "
                    "Describe configuration options exactly as stated in the context instead of summarizing them as general product support or capability. "
                    "Keep the answer concise, accurate, and technically clear."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "top_p": 0.8,
        "max_tokens": 2000,
    }
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=60
    )

    if not response.ok:
        raise Exception(
            f"Hugging Face API error {response.status_code}: {response.text}"
        )
    data = response.json()
   
    return data["choices"][0]["message"].get("content", "")
def get_source_trust_score(title, url, source_type):
    title_lower = title.lower()
    url_lower = url.lower()

    if source_type != "Official":
        return 10

    if (
        "manual" in title_lower
        or "user guide" in title_lower
        or "datasheet" in title_lower
        or "data sheet" in title_lower
        or "manual" in url_lower
        or "datasheet" in url_lower
    ):
        return 100

    if (
        "product" in title_lower
        or "/products/" in url_lower
        or "/product/" in url_lower
    ):
        return 90

    if (
        "support" in title_lower
        or "knowledge" in title_lower
        or "support" in url_lower
    ):
        return 80

    return 70
def rewrite_follow_up_query(previous_question, current_question):
    rewrite_prompt = f"""
Rewrite the current follow-up question as one standalone web search query.

Previous question:
{previous_question}

Current follow-up question:
{current_question}

Rules:
- Resolve references such as it, its, this, that, they, and their using the previous question.
- Preserve the exact product or model name from the previous question.
- Preserve the exact topic requested in the current follow-up.
- Do not answer the question.
- Do not add facts.
- Return only the standalone search query and nothing else.

Standalone search query:
"""

    rewritten_query = call_qwen_llm(rewrite_prompt)
    return rewritten_query.strip().strip('"')
def normalize_search_query(question):
    normalize_prompt = f"""
Convert the user's question into one clean standalone English web search query.

User question:
{question}

Rules:
- Understand Arabic, English, mixed Arabic-English, colloquial language, and spelling mistakes.
- Correct obvious spelling and grammar mistakes.
- Translate Arabic wording into natural English when needed.
- Preserve product names, manufacturer names, model numbers, acronyms, and technical terms exactly when possible.
- Do not answer the question.
- Do not add facts or specifications.
- Do not guess a product that the user did not mention.
- Keep the user's original intent.
- Return only the cleaned English search query and nothing else.

Clean search query:
"""

    try:
        normalized_query = call_qwen_llm(normalize_prompt)
        return normalized_query.strip().strip('"')
    except Exception:
        return question.strip()
def build_document_keyword_fallback(question, document_context, max_terms=8):
    if not document_context:
        return normalize_search_query(question)

    question_words = {
        word.lower()
        for word in re.findall(r"[A-Za-z0-9+#.-]+", question)
        if len(word) >= 3
    }

    lines = [
        line.strip()
        for line in document_context.splitlines()
        if line.strip()
    ]

    candidates = []

    for line in lines:
        line_lower = line.lower()

        relevance = sum(
            1 for word in question_words
            if word in line_lower
        )

        phrases = re.findall(
            r"\b[A-Z][A-Za-z0-9+#&.-]*(?:\s+[A-Z][A-Za-z0-9+#&.-]*){0,4}",
            line
        )

        for phrase in phrases:
            phrase = phrase.strip()

            if len(phrase) < 3:
                continue

            score = relevance

            if len(phrase.split()) > 1:
                score += 1

            if any(char.isdigit() for char in phrase):
                score += 1

            if "-" in phrase or phrase.isupper():
                score += 1

            candidates.append((score, phrase))

    candidates.sort(key=lambda item: item[0], reverse=True)

    selected_terms = []

    for _, phrase in candidates:
        if phrase.lower() not in {
            term.lower() for term in selected_terms
        }:
            selected_terms.append(phrase)

        if len(selected_terms) >= max_terms:
            break

    if not selected_terms:
        return normalize_search_query(question)

    base_query = normalize_search_query(question)

    return f"{base_query} {' '.join(selected_terms)}"


def build_document_aware_web_query(question, document_context):
    current_web_cues = (
        "current",
        "currently",
        "latest",
        "today",
        "fee",
        "fees",
        "price",
        "pricing",
        "cost",
        "requirements",
        "requirement",
        "eligibility",
        "exam date",
        "exam dates",
        "registration",
        "deadline",
    )

    question_lower = question.lower()

    fee_web_cues = (
        "fee",
        "fees",
        "cost",
        "price",
        "pricing",
    )
    
    if any(cue in question_lower for cue in fee_web_cues):
        base_query = normalize_search_query(question)
    
        if "exam" in question_lower:
            return f"{base_query} official exam fee pricing"
    
        return f"{base_query} official pricing"
    
    if any(cue in question_lower for cue in current_web_cues):
        return normalize_search_query(question)
    query_prompt = f"""
Create a concise and effective web search query using both the user's question
and the relevant information extracted from the uploaded document.

USER QUESTION:
{question}

DOCUMENT CONTEXT:
{document_context}

Instructions:
- Understand what the user is asking before creating the search query.
- Use relevant facts from the document to resolve names, products, technologies,
  certifications, roles, organizations, or other references in the question.
- Include only document details that are useful for the web search.
- Do not search for the person's name unless the question specifically requires it.
- For recommendation questions, search for authoritative information that can
  support useful recommendations based on the document context.
- Preserve important technical terms, product names, standards, and certification names.
- Prefer queries that can find official or authoritative sources.
- Do not answer the user's question.
- Do not invent information that is not present in the question or document context.
- The search query must include at least two specific relevant terms taken from the DOCUMENT CONTEXT when such terms are available.
- Do not simply repeat or paraphrase the user's question when the document contains useful identifying details for the search.
- Return only one clean English web search query and nothing else.

Web search query:
"""

    try:
        generated_query = call_qwen_llm(query_prompt)
        generated_query = generated_query.strip().strip('"')

        if generated_query:
            normalized_generated = generated_query.strip().lower()
            normalized_question = question.strip().lower()
        
            if normalized_generated != normalized_question:
                return generated_query
            retry_prompt = f"""
The previous search query was too similar to the user's original question.

Create a better web search query using specific relevant information from the document.

USER QUESTION:
{question}

DOCUMENT CONTEXT:
{document_context}

Requirements:
- Include at least two specific relevant terms from the document.
- Focus on certifications, technologies, products, roles, or organizations relevant to the question.
- Do not repeat or paraphrase the user's question.
- Do not answer the question.
- Return only one clean English web search query.

Web search query:
"""
    
            retry_query = call_qwen_llm(retry_prompt)
            retry_query = retry_query.strip().strip('"')
            
            if retry_query:
                normalized_retry = retry_query.strip().lower()
            
                if normalized_retry != normalized_question:
                    return retry_query
    except Exception:
        pass

    return build_document_keyword_fallback(
        question,
        document_context
    )


def is_official_domain(url, official_domains):
    try:
        domain = url.lower().split("/")[2]
        domain = domain.split(":")[0]

        return any(
            domain == official_domain
            or domain.endswith("." + official_domain)
            for official_domain in official_domains
        )
    except Exception:
        return False


def search_web_tavily(query):
    url = "https://api.tavily.com/search"

    headers = {
        "Authorization": f"Bearer {st.secrets['TAVILY_API_KEY']}",
        "Content-Type": "application/json"
    }

    official_domains = [
        "qsys.com",
        "cisco.com",
        "shure.com",
        "extron.com",
        "crestron.com",
        "barco.com",
        "biamp.com",
        "lightware.com",
        "samsung.com",
        "lg.com",
        "avixa.org",
        "audinate.com",
        "microsoft.com",
        "zoom.us",
        "hp.com",
    ]
    query_lower = query.lower()

    targeted_domains = official_domains
    
    if "avixa" in query_lower or "cts" in query_lower:
        targeted_domains = ["avixa.org"]

    # STEP 1: Search official AV manufacturer websites first
    official_payload = {
        "query": query,
        "search_depth": "advanced",
        "max_results": 5,
        "include_domains": targeted_domains,
        "include_answer": False,
        "include_raw_content": True
    }

    response = requests.post(
        url,
        headers=headers,
        json=official_payload,
        timeout=60
    )

    response.raise_for_status()
    data = response.json()
    results = data.get("results", [])
    
    query_lower = query.lower()

    asks_base_cts = (
        "cts" in query_lower
        and "cts-i" not in query_lower
        and "cts i" not in query_lower
        and "cts-d" not in query_lower
        and "cts d" not in query_lower
    )

    if asks_base_cts:
        filtered_results = []

        for result in results:
            title_lower = result.get("title", "").lower()

            if (
                "cts-i" in title_lower
                or "cts i certification" in title_lower
                or "cts-d" in title_lower
                or "cts d certification" in title_lower
            ):
                continue

            filtered_results.append(result)

        results = filtered_results

    # Validate source domains before marking results as official
    for result in results:
        result_url = result.get("url", "")
    
        if is_official_domain(result_url, official_domains):
            result["source_type"] = "Official"
        else:
            result["source_type"] = "External"

    # STEP 2: If official search returns nothing, search the general web
    if not results:
        fallback_payload = {
            "query": query,
            "search_depth": "advanced",
            "max_results": 5,
            "include_answer": False,
            "include_raw_content": False
        }

        response = requests.post(
            url,
            headers=headers,
            json=fallback_payload,
            timeout=60
        )

        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])

        for result in results:
            result["source_type"] = "External"
    # Extract product/model tokens from the user's query
    query_tokens = set(query.lower().replace("-", " ").split())
    
    product_tokens = {
        token for token in query_tokens
        if any(char.isdigit() for char in token)
    }
    
    # Calculate trust and relevance score for every result
    for result in results:
        title = result.get("title", "")
        url = result.get("url", "")
        source_type = result.get("source_type", "External")
    
        result["trust_score"] = get_source_trust_score(
            title,
            url,
            source_type
        )
    
        raw_content = result.get("raw_content", "") or ""

        result_text = (
            f"{title} "
            f"{url} "
            f"{result.get('content', '')} "
            f"{raw_content}"
        ).lower()
    
        for product_token in product_tokens:
            if product_token in result_text:
                result["trust_score"] += 25
        # Boost results that directly match pricing, fees, and requirements intent
        fee_intent_terms = (
            "fee",
            "fees",
            "exam fee",
            "exam fees",
            "cost",
            "price",
            "pricing",
        )
        
        requirement_intent_terms = (
            "requirement",
            "requirements",
            "eligibility",
            "prerequisite",
            "prerequisites",
        )
        
        asks_about_fees = any(
            term in query_lower
            for term in fee_intent_terms
        )
        
        asks_about_requirements = any(
            term in query_lower
            for term in requirement_intent_terms
        )
        
        if asks_about_fees:
            for term in fee_intent_terms:
                if term in result_text:
                    result["trust_score"] += 40
                    break
        
        if asks_about_requirements:
            for term in requirement_intent_terms:
                if term in result_text:
                    result["trust_score"] += 30
                    break
    # Prefer primary English-language official sources
    english_url_markers = (
        "/en-us/",
        "/en-gb/",
        "/en-emea/",
        "/en-mea/",
        "/en/"
    )
    
    non_english_url_markers = (
        "/es/",
        "/es-",
        "/pt/",
        "/pt-",
        "/zh/",
        "/zh-",
        "/fr/",
        "/fr-",
        "/de/",
        "/de-",
        "/it/",
        "/it-",
        "/ja/",
        "/ja-",
        "/ko/",
        "/ko-"
    )
    
    url_lower = url.lower()
    
    if source_type == "Official":
        if any(marker in url_lower for marker in english_url_markers):
            result["trust_score"] += 15
        elif any(marker in url_lower for marker in non_english_url_markers):
            result["trust_score"] -= 10
    # Sort highest-trust sources first
    results.sort(
        key=lambda result: result.get("trust_score", 0),
        reverse=True
    )
    # Prefer exact product/model matches when available
    if product_tokens:
        exact_product_results = []
    
        for result in results:
            title = result.get("title", "")
            url = result.get("url", "")
            content = result.get("content", "")
    
            result_text = f"{title} {url} {content}".lower()
    
            if all(
                product_token in result_text
                for product_token in product_tokens
            ):
                exact_product_results.append(result)
    
        # Only apply the filter when exact matches actually exist
        if exact_product_results:
            results = exact_product_results
    # Remove duplicate web sources by URL and normalized title
    unique_results = []
    seen_urls = set()
    seen_titles = set()
    
    for result in results:
        url = result.get("url", "").strip()
        title = result.get("title", "").strip().lower()
    
        normalized_title = (
            title
            .split("|")[0]
            .split(" - shure")[0]
            .strip()
        )
    
        if (
            url
            and url not in seen_urls
            and normalized_title not in seen_titles
        ):
            unique_results.append(result)
            seen_urls.add(url)
    
            if normalized_title:
                seen_titles.add(normalized_title)
    
    results = unique_results
    return results
def get_manufacturer_name(url):
    domain_map = {
        "qsys.com": "Q-SYS",
        "cisco.com": "Cisco",
        "shure.com": "Shure",
        "extron.com": "Extron",
        "crestron.com": "Crestron",
        "barco.com": "Barco",
        "biamp.com": "Biamp",
        "lightware.com": "Lightware",
        "samsung.com": "Samsung",
        "lg.com": "LG"
    }

    url_lower = url.lower()

    for domain, manufacturer in domain_map.items():
        if domain in url_lower:
            return manufacturer

    return "Official Manufacturer"
    
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
        chunk_size=700,
        chunk_overlap=100,
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
# Initialize conversational memory
if "messages" not in st.session_state:
    st.session_state.messages = []
# Display conversation history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
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
    st.divider()
    
    st.header("🔎 Search Mode")

    search_mode = st.radio(
        "Choose where the AI should search:",
        [
            "Documents Only",
            "Documents + Web",
            "Web Only"
        ],
        index=0
    )
# Process uploaded PDF
document_pages = []
text_chunks = []
vector_store = None
web_results = []
web_context = ""

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
    if question:
        st.session_state.messages.append({
            "role": "user",
            "content": question
        })
    if not question:
        st.warning("Please enter a question.")

    elif search_mode == "Web Only":
        try:
            with st.spinner("Searching the web..."):
                web_results = search_web_tavily(question)

            if not web_results:
                st.warning("No relevant web results were found.")

            else:
                web_context_parts = []

                for result in web_results:
                    title = result.get("title", "")
                    url = result.get("url", "")
                    source_type = result.get("source_type", "External")
                    content = result.get("content", "")
                    source_number = len(web_context_parts) + 1

                    web_context_parts.append(
                        f"Source [{source_number}]\n"
                        f"Title: {title}\n"
                        f"URL: {url}\n"
                        f"Content: {content}"
                    )
                web_context = "\n\n".join(web_context_parts)

                prompt = f"""
Question:
{question}

Web search context:
{web_context}

Answer using only the web search context above.
Do not invent information that is not supported by the web results.

For every factual claim, cite the supporting source using its number in square brackets,
for example [1] or [2].

Use only source numbers that actually appear in the Web search context.
Do not create or guess source numbers.
If multiple sources support the same claim, cite them like [1][2].
"""

            answer = call_qwen_llm(prompt)
            
            st.subheader("🤖 AI Answer")
            st.write(answer)
    
            st.markdown("### 🌐 Web Sources")
    
            for source_number, result in enumerate(web_results, start=1):
                title = result.get("title", "Web source")
                url = result.get("url", "")
                source_type = result.get("source_type", "External")
            
                if url:
                    if source_type == "Official":
                        manufacturer = get_manufacturer_name(url)
                        st.markdown(
                            f"- **[{source_number}]** ✅ **{manufacturer} Official** — [{title}]({url})"
                        )
                    else:
                        st.markdown(
                            f"- **[{source_number}]** 🌐 **External Source** — [{title}]({url})"
                        )
        except Exception as e:
            st.error(f"Web search error: {e}")

    elif not uploaded_files:
        st.warning("Please upload at least one PDF document first.")

    elif not document_pages:
        st.warning("The uploaded PDF files do not contain readable text.")

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
        search_query = question

        retrieval_follow_up_references = {
            "it",
            "its",
            "this",
            "that",
            "they",
            "their",
            "them",
        }
        
        retrieval_question_words = set(
            question_lower
            .replace("?", "")
            .replace(",", "")
            .replace(".", "")
            .split()
        )
        
        retrieval_is_follow_up = bool(
            retrieval_question_words & retrieval_follow_up_references
        )
        
        if retrieval_is_follow_up:
            previous_user_questions = [
                message["content"]
                for message in st.session_state.messages[:-1]
                if message["role"] == "user"
            ]
        
            if previous_user_questions:
                previous_question = previous_user_questions[-1]
        
                search_query = rewrite_follow_up_query(
                    previous_question,
                    question
                )

        if matched_source:
            search_results = vector_store.similarity_search_with_score(
                search_query,
                k=4,
                filter={"source": matched_source}
            )
        else:
            search_results = vector_store.similarity_search_with_score(
                search_query,
                k=4
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
        product_keywords = [
            keyword
            for keyword in question_keywords
            if any(char.isdigit() for char in keyword)
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
                product_matches = sum(
                    1 for keyword in product_keywords
                    if keyword in document_text
                )
                evidence_documents.append(
                    (document, score, keyword_matches, product_matches)
                )
        
        # Prefer chunks that contain question evidence,
        # then use semantic distance as the secondary ranking.
        evidence_documents.sort(
            key=lambda item: (-item[3], -item[2], item[1])
        )
        
        relevant_documents = [
            document
            for document, score, keyword_matches, product_matches in evidence_documents
            if (
                (
                    is_verification_question
                    and len(question_keywords) > 0
                    and keyword_matches == len(evidence_keywords)
                )
                or
                (
                    not is_verification_question
                    and (
                        product_matches > 0
                        or keyword_matches > 0
                        or score <= 1.10
                    )
                )
            )
        ]
        # Neighbor Expansion
        # Add the previous and next chunk from the same source/page
        # so information split across chunk boundaries is not lost.
        
        expanded_texts = []
        seen_chunks = set()
        used_sources = set()
        # Build stable document citation numbers from the full uploaded document
        doc_source_numbers = {}
        
        for page in document_pages:
            doc_key = (
                page.get("source"),
                page.get("page_number")
            )
        
            if doc_key not in doc_source_numbers:
                doc_source_numbers[doc_key] = len(doc_source_numbers) + 1
        
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
                            doc_key = (
                                chunk["source"],
                                chunk["page_number"]
                            )
                            
                        doc_number = doc_source_numbers.get(doc_key)

                        if doc_number is None:
                            doc_number = len(doc_source_numbers) + 1
                            doc_source_numbers[doc_key] = doc_number
                        
                        expanded_texts.append(
                            f"[DOC {doc_number}]\n"
                            f"Source: {chunk['source']} | "
                            f"Page: {chunk['page_number']}\n"
                            f"{chunk['text']}"
                        )
                        
                        seen_chunks.add(chunk_key)
                        
                        used_sources.add(
                            (chunk["source"], chunk["page_number"])
                        )
        
                        break
        if expanded_texts:
            context = "\n\n".join(expanded_texts)
        else:
            context = "\n\n".join(
                document.page_content for document in relevant_documents
            )
        
            for document in relevant_documents:
                used_sources.add(
                    (
                        document.metadata.get("source"),
                        document.metadata.get("page_number")
                    )
                )
        
        if (
            not relevant_documents
            and not is_summary_question
            and search_mode == "Documents Only"
        ):
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
        if search_mode == "Documents + Web":
            document_only_phrases = (
                "what does the document say",
                "according to the document",
                "in this document",
                "in this pdf",
                "based on the document",
                "based only on the document",
                "according to this document",
                "what does this document say",
            )
        
            is_document_focused_question = any(
                phrase in question_lower
                for phrase in document_only_phrases
            )
    
        if "document_scope_active" not in st.session_state:
            st.session_state.document_scope_active = False
        
        if is_document_focused_question:
            st.session_state.document_scope_active = True
            web_search_query = None
        elif st.session_state.document_scope_active:
            web_search_query = None
        else:
            web_search_query = build_document_aware_web_query(
                question,
                context
            )
            
            # Detect whether this is a web follow-up question
            web_follow_up_starters = (
                "what about",
                "how about",
                "and what",
                "and how",
                "and does",
                "and is",
                "and can",
            )

            web_follow_up_references = {
                "it",
                "its",
                "this",
                "that",
                "they",
                "their",
                "them",
            }

            web_question_words = set(
                question_lower
                .replace("?", "")
                .replace(",", "")
                .replace(".", "")
                .split()
            )

            document_reference_phrases = (
                "this profile",
                "this document",
                "this file",
                "this cv",
                "this resume",
                "this pdf",
            )
            
            is_document_reference = any(
                phrase in question_lower
                for phrase in document_reference_phrases
            )
            
            is_web_follow_up = (
                not is_document_reference
                and (
                    question_lower.startswith(web_follow_up_starters)
                    or bool(web_question_words & web_follow_up_references)
                )
            )
            # Reset document-only scope when the user clearly starts a new topic
            if (
                st.session_state.document_scope_active
                and not is_document_focused_question
                and not is_web_follow_up
            ):
                st.session_state.document_scope_active = False
            
                web_search_query = build_document_aware_web_query(
                    question,
                    context
                )
            # Rewrite the query only when this is a follow-up
            if is_web_follow_up:
                previous_user_questions = [
                    message["content"]
                    for message in st.session_state.messages[:-1]
                    if message["role"] == "user"
                ]

                if previous_user_questions:
                    previous_question = previous_user_questions[-1]
                
                    if st.session_state.document_scope_active:
                        web_search_query = None
                    else:
                        web_search_query = rewrite_follow_up_query(
                            previous_question,
                            question
                        )

            # Search the web for BOTH new questions and follow-up questions
            def extract_relevant_web_evidence(raw_content, query, max_chars=3500):
                if not raw_content:
                    return ""
            
                # Normalize the query into useful search terms
                query_terms = {
                    word.lower().strip(".,!?()[]{}:;\"'")
                    for word in query.split()
                    if len(word) >= 3
                }
            
                # Split the page into manageable text blocks
                blocks = re.split(r"\n\s*\n|\n", raw_content)
            
                scored_blocks = []
            
                for index, block in enumerate(blocks):
                    cleaned_block = " ".join(block.split())
            
                    if len(cleaned_block) < 30:
                        continue
            
                    block_lower = cleaned_block.lower()
            
                    score = sum(
                        1 for term in query_terms
                        if term in block_lower
                    )

                    fee_query_terms = (
                        "fee",
                        "fees",
                        "cost",
                        "price",
                        "pricing",
                    )
                    
                    asks_about_fees = any(
                        term in query.lower()
                        for term in fee_query_terms
                    )
                    
                    if asks_about_fees:
                        pricing_markers = (
                            "$",
                            "usd",
                            "sar",
                            "eur",
                            "gbp",
                            "aud",
                            "fee",
                            "fees",
                            "cost",
                            "price",
                            "pricing",
                        )
                    
                        if any(marker in block_lower for marker in pricing_markers):
                            score += 5
            
                    if score > 0:
                        scored_blocks.append(
                            (score, index, cleaned_block)
                        )
            
                if not scored_blocks:
                    return raw_content[:max_chars]
            
                # Highest relevance first
                scored_blocks.sort(
                    key=lambda item: (-item[0], item[1])
                )
            
                selected_blocks = []
                total_chars = 0
            
                for score, index, block in scored_blocks:
                    if total_chars + len(block) > max_chars:
                        continue
            
                    selected_blocks.append(block)
                    total_chars += len(block)
            
                    if total_chars >= max_chars:
                        break
            
                return "\n".join(selected_blocks)
            web_results = []

            try:
                if web_search_query:
                    with st.spinner("Searching the web..."):
                        web_results = search_web_tavily(web_search_query)
                          
                if web_results:
                    web_context_parts = []
    
                    for source_number, result in enumerate(web_results, start=1):
                        title = result.get("title", "")
                        url = result.get("url", "")
                        raw_content = result.get("raw_content") or result.get("content", "")
    
                        content = extract_relevant_web_evidence(
                            raw_content,
                            web_search_query
                        )
                        source_type = result.get("source_type", "External")

                        web_context_parts.append(
                            f"[WEB {source_number}]\n"
                            f"Title: {title}\n"
                            f"URL: {url}\n"
                            f"Source Type: {source_type}\n"
                            f"Content: {content}"
                        )
    
                        web_context = "\n\n".join(web_context_parts)
    
                        context = f"""
    DOCUMENT CONTEXT:
    {context}
    
    WEB CONTEXT:
    {web_context}
    """

            except Exception as e:
                st.warning(f"Web search could not be completed: {e}")
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
        if (
            search_mode == "Documents Only"
            and "certification" in question_lower
            and not is_verification_question
        ):
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
            subject = question.strip().rstrip("?")
        
            if question_lower.startswith("what is "):
                subject = question[8:].strip().rstrip("?")
            elif "features of the " in question_lower:
                subject = question_lower.split("features of the ", 1)[1].strip().rstrip("?")
        
            normalized_subject = "".join(
                char.lower() for char in subject
                if char.isalnum()
            )
        
            normalized_context = "".join(
                char.lower() for char in context
                if char.isalnum()
            )
        
            subject_tokens = [
                "".join(
                    char.lower() for char in token
                    if char.isalnum()
                )
                for token in subject.split()
            ]
            
            subject_tokens = [
                token for token in subject_tokens
                if len(token) >= 2
                and token not in {"the", "a", "an"}
            ]
            
            subject_found = all(
                token in normalized_context
                for token in subject_tokens
            )
        # Detect whether the current question is likely a conversational follow-up
        follow_up_starters = (
            "what about",
            "how about",
            "and what",
            "and how",
            "and does",
            "and is",
            "and can",
            "what else",
            "how many",
            "how much",
        )
        
        follow_up_references = {
            "it",
            "its",
            "this",
            "that",
            "they",
            "their",
            "them",
        }
        
        question_words = set(
            question_lower
            .replace("?", "")
            .replace(",", "")
            .replace(".", "")
            .split()
        )
        
        is_follow_up = (
            question_lower.startswith(follow_up_starters)
            or bool(question_words & follow_up_references)
        )
        # Build recent conversation history for contextual follow-up questions
        conversation_history = ""
        if is_follow_up:
            for message in st.session_state.messages[:-1][-6:]:
                role = "User" if message["role"] == "user" else "Assistant"
                conversation_history += f"{role}: {message['content']}\n"    
        prompt = f"""
        Recent conversation:
        {conversation_history}    
        Question:
        {question}
        Follow-up question detected: {is_follow_up}
        If Follow-up question detected is False, treat the current question as a new topic and do not carry over entities or assumptions from previous conversation turns.
        If it is True, use the recent conversation only to resolve references such as it, its, this, that, or omitted product names.
        Combined context:
        {context}
        
        Subject detected in document: {subject_found}
        Answer using only the information provided in the context above.
        Current factual information questions:
        - If the user explicitly asks for current fees, prices, costs, requirements, eligibility, registration details, exam dates, or deadlines, answer those requested facts directly first.
        - Do not turn a factual current-information question into a career recommendation.
        - Do not use personal profile or CV details unless they are necessary to answer the user's question.
        - Do not substitute training-course pricing or preparation costs when the user asks for an exam fee.
        - If the exact requested fee, price, requirement, or deadline is not present in the available context, clearly say that the exact information was not found in the retrieved sources.
        - Do not add unrelated next-step recommendations unless the user explicitly asks for advice or a recommendation.
        Recommendation and decision questions:
        - If the user asks for a recommendation, comparison, best option, next step, career path, or professional judgment, you MAY synthesize a recommendation from the supported facts in the document and web context.
        - Do not require the recommendation itself to appear explicitly in the source.
        - Base the recommendation only on supported evidence from the context.
        - Clearly distinguish between sourced facts and your recommendation.
        - Give a direct recommendation first, then briefly explain why it is the best fit.
        - Do not invent certifications, products, requirements, or credentials that are not supported by the available context.
        Answer quality rules:
        - Never describe CTS, CTS-D, and CTS-I as levels of the same certification. Describe CTS as the foundational credential, and CTS-D / CTS-I as specialized certifications that may follow CTS when supported by the context.
        - Be concise and decision-oriented.
        - For a recommendation question, give ONE primary recommendation and at most ONE alternative.
        - Start with the recommendation directly.
        - Explain the recommendation using only the most relevant facts from the user's document and supporting web evidence.
        - Do not enumerate certifications, products, or credentials merely because they are absent from the user's profile.
        - Do not include long lists of unrelated alternatives.
        - Keep recommendation answers focused on the user's actual question and career direction.
        - Use precise credential names exactly as supported by the context.
        - Do not describe CTS, CTS-D, and CTS-I as three "levels". Treat CTS as the foundational credential and CTS-D / CTS-I as specialized certification paths when supported by the context.
        - Never recommend CTS-D or CTS-I as the immediate next certification unless the context explicitly confirms that the user already holds an active CTS credential.
        - If the context shows CTS Preparation but does not confirm an active CTS credential, recommend completing CTS first.
        - If a logical progression is supported, explain it clearly, for example: current preparation → recommended credential → possible specialized next step.
        - Avoid repeating the recommendation or conclusion.
        - Prefer roughly 100–180 words for a straightforward recommendation unless the user asks for more detail.
        - When describing a person's skills, experience, or capabilities, use document evidence about that person as the primary source.
        - Do not infer that the person has a specific technical capability merely because a product or platform listed in their profile supports that capability.
        - Web sources may explain a technology, but must not be used to upgrade or infer the user's personal skill level unless the document explicitly supports it.
        Use the recent conversation only to understand the user's follow-up question and conversational context.
        Do not treat the recent conversation as a factual source.
        All factual claims must still be supported by the Combined context and its citations.
        
        
        Citation rules:
        - Every factual claim in the answer MUST include a citation immediately after the claim.
        - If the information comes from an uploaded document, use the exact [DOC X] label attached to that information in the context.
        - If the information comes from a web source, use the exact [WEB X] label attached to that information in the context.
        - If both a document and a web source support the same claim, cite both, for example [DOC 1][WEB 1].
        - Never write a factual claim without a citation when a supporting citation is available.
        - Use only citation labels that actually appear in the context.
        - Never invent, renumber, or guess citation labels.
        - For bullet-point answers, place the citation at the end of EACH bullet point it supports.
        - Do not add new facts, recommendations, products, certifications, or alternatives.
        
        If "Subject detected in document" is True, the requested subject exists in the document.
        Use the related facts in the context to answer the question.
        Do not say the information was not found when the subject is detected.
        """
        
        if direct_answer is not None:
            answer = direct_answer
        else:
            with st.spinner("AI is analyzing the document..."):
                try:
                    answer = call_qwen_llm(prompt)
                except Exception as e:
                    answer = f"AI model error: {e}"
        # Validate citation coverage before displaying the answer
        if direct_answer is None and not answer.startswith("AI model error:"):
            answer_lines = answer.splitlines()
        
            uncited_bullets = [
                line for line in answer_lines
                if line.strip().startswith(("-", "*", "•"))
                and "[DOC " not in line
                and "[WEB " not in line
            ]
        
            if uncited_bullets:
                citation_review_prompt = f"""
        Review the answer below using the provided context.
        
        CONTEXT:
        {context}
        
        ANSWER:
        {answer}
        
        Citation requirements:
        - Preserve the meaning of the answer.
        - Every factual bullet point must end with the correct citation.
        - Use only [DOC X] and [WEB X] labels that actually appear in the context.
        - Never invent or guess a citation.
        - If a factual statement cannot be supported by the context, remove it.
        - A citation must support the exact claim immediately before it, not merely a related topic.
        - If a claim contains multiple facts, every fact must be supported by the cited source or the claim must be shortened to only the supported portion.
        - Do not add new facts, recommendations, products, certifications, or alternatives.
        - Do not expand the answer beyond what is already written.
        - Only fix citation placement or remove unsupported claims.
        - Preserve the original answer's brevity, structure, recommendation, and wording as much as possible.
        - Return only the corrected answer.
        
        Corrected answer:
        """
        
                try:
                    answer = call_qwen_llm(citation_review_prompt)
                except Exception:
                    pass
        # Deterministic guard for high-risk factual claims
        def get_cited_source_text(source_type, source_number, full_context):
            label = f"[{source_type} {source_number}]"
        
            pattern = (
                rf"{re.escape(label)}[\s\S]*?"
                rf"(?=\n\[DOC \d+\]|\n\[WEB \d+\]|\Z)"
            )
        
            match = re.search(pattern, full_context, re.IGNORECASE)
        
            if match:
                return match.group(0).lower()
        
            return ""
        
        
        high_risk_phrases = (
            "leading professional credential",
            "globally recognized",
            "highly valued",
            "most recognized",
            "industry standard",
            "worldwide",
        )
        
        verified_sentences = []
        
        for sentence in re.split(r"(?<=[.!?])\s+", answer):
            sentence_lower = sentence.lower()
        
            citations = re.findall(
                r"\[(DOC|WEB) (\d+)\]",
                sentence
            )
        
            high_risk_found = [
                phrase
                for phrase in high_risk_phrases
                if phrase in sentence_lower
            ]
        
            numbers = re.findall(
                r"\b\d+(?:\.\d+)?%?\b",
                re.sub(r"\[(?:DOC|WEB) \d+\]", "", sentence)
            )
        
            if (high_risk_found or numbers) and citations:
                cited_source_texts = [
                    get_cited_source_text(
                        source_type,
                        source_number,
                        context
                    )
                    for source_type, source_number in citations
                ]
        
                combined_cited_text = " ".join(cited_source_texts)
        
                phrase_aliases = {
                    "leading professional credential": (
                        "leading professional credential",
                        "leading credential",
                        "professional credential",
                    ),
                    "globally recognized": (
                        "globally recognized",
                        "recognized worldwide",
                        "internationally recognized",
                    ),
                    "highly valued": (
                        "highly valued",
                        "highly regarded",
                        "valued by employers",
                    ),
                    "most recognized": (
                        "most recognized",
                        "widely recognized",
                        "well recognized",
                    ),
                    "industry standard": (
                        "industry standard",
                        "industry-standard",
                        "standard in the industry",
                    ),
                    "worldwide": (
                        "worldwide",
                        "globally",
                        "internationally",
                    ),
                }
                
                phrase_supported = all(
                    any(
                        alias in combined_cited_text
                        for alias in phrase_aliases.get(phrase, (phrase,))
                    )
                    for phrase in high_risk_found
                )
        
                numbers_supported = all(
                    number in combined_cited_text
                    for number in numbers
                )
        
                if not phrase_supported or not numbers_supported:
                    continue
        
            verified_sentences.append(sentence)
        
        answer = " ".join(verified_sentences).strip()
        # Restore bullet formatting after claim filtering
        answer = re.sub(
            r"\.\s+-\s+",
            ".\n\n- ",
            answer
        )
        # Prevent web sources from inventing or upgrading personal skills
        profile_skill_cues = (
            "skills",
            "strongest technical",
            "experience",
            "capabilities",
            "what can this person",
        )
        
        is_profile_skill_question = any(
            cue in question_lower
            for cue in profile_skill_cues
        )
        
        if is_profile_skill_question:
            filtered_lines = []
        
            for line in answer.splitlines():
                stripped = line.strip()
        
                if not stripped:
                    filtered_lines.append(line)
                    continue
        
                has_web_citation = bool(
                    re.search(r"\[WEB \d+\]", line)
                )
        
                has_doc_citation = bool(
                    re.search(r"\[DOC \d+\]", line)
                )
        
                personal_skill_language = bool(
                    re.search(
                        r"\b("
                        r"working with|"
                        r"managing|"
                        r"skilled in|"
                        r"experienced in|"
                        r"expertise in|"
                        r"strong in|"
                        r"proficient in|"
                        r"knowledge of|"
                        r"familiar with|"
                        r"hands-on with|"
                        r"capable of"
                        r")\b",
                        line,
                        re.IGNORECASE
                    )
                )
        
                if (
                    personal_skill_language
                    and has_web_citation
                    and not has_doc_citation
                ):
                    continue
        
                filtered_lines.append(line)
        
            answer = "\n".join(filtered_lines).strip()
        # Validate that citation labels reference real available sources
        import re
        
        if direct_answer is None and not answer.startswith("AI model error:"):
            cited_docs = {
                int(x) for x in re.findall(r"\[DOC (\d+)\]", answer)
            }
        
            cited_web = {
                int(x) for x in re.findall(r"\[WEB (\d+)\]", answer)
            }
        
            valid_docs = set(doc_source_numbers.values())
        
            valid_web = set(
                range(1, len(web_results) + 1)
            ) if search_mode == "Documents + Web" and web_results else set()
        
            invalid_docs = cited_docs - valid_docs
            invalid_web = cited_web - valid_web
        
            if invalid_docs or invalid_web:
                invalid_labels = (
                    [f"[DOC {x}]" for x in sorted(invalid_docs)]
                    + [f"[WEB {x}]" for x in sorted(invalid_web)]
                )
            
                # Remove invalid citation labels before claim verification
                for invalid_label in invalid_labels:
                    answer = answer.replace(invalid_label, "")
            
        # Build document source content map for claim verification
        doc_source_content = {}
        
        for page in document_pages:
            source_name = page.get("source")
            page_number = page.get("page_number")
            page_text = page.get("text", "")
        
            doc_key = (source_name, page_number)
        
            if doc_key in doc_source_numbers:
                doc_number = doc_source_numbers[doc_key]
                doc_source_content[doc_number] = page_text
        # Build web source content map for claim verification
        web_source_content = {}
        
        if search_mode == "Documents + Web" and web_results:
            for web_number, result in enumerate(web_results, start=1):
                web_source_content[web_number] = (
                    result.get("raw_content")
                    or result.get("content", "")
                )
        # Verify each cited claim against the actual cited source content
        claim_verification_passed = False
        if direct_answer is None and not answer.startswith("AI model error:"):
            verification_context_parts = []
        
            for doc_number, source_text in doc_source_content.items():
                verification_context_parts.append(
                    f"[DOC {doc_number}]\n{source_text}"
                )
        
            for web_number, source_text in web_source_content.items():
                verification_context_parts.append(
                    f"[WEB {web_number}]\n{source_text}"
                )
        
            verification_context = "\n\n".join(verification_context_parts)
        
            if verification_context:
                claim_verification_prompt = f"""
        Review the answer against the exact cited source content below.
        
        ANSWER:
        {answer}
        
        SOURCE CONTENT:
        {verification_context}
        
        Verification rules:
        - Check every factual claim against the source cited immediately after that claim.
        - A [DOC X] claim must be directly supported by the matching [DOC X] content.
        - A [WEB X] claim must be directly supported by the matching [WEB X] content.
        - Do not assume that a citation supports a claim merely because the citation exists.
        - If a claim is not supported by its cited source, DELETE that claim silently.
        - Do NOT explain that information was missing, unsupported, unavailable, or not found.
        - Do NOT add notes, warnings, explanations, verification comments, or summaries.
        - Preserve only supported claims and their correct citations.
        - Never invent, change, renumber, or guess citation numbers.
        - Preserve the original answer format whenever possible.
        - Preserve the language of the ANSWER exactly. Do not translate the answer into the language of the source content.
        - If the ANSWER is Arabic, return Arabic. If the ANSWER is English, return English.
        - Citation format must be exactly [DOC X] or [WEB X].
        - Never output citation wrappers such as [CITE: ...], CITE:, Source:, or similar citation formats.
        - Return ONLY the cleaned verified answer and nothing else.
        
        Verified answer:
        """
        
                try:
                    answer = call_qwen_llm(claim_verification_prompt)
                    claim_verification_passed = True
                except Exception as e:
                    st.warning(f"Claim verification error: {e}")
        # Final answer cleanup: preserve user language and normalize citation format

        # Remove malformed citation wrappers such as:
        # [CITE: [WEB 1], [WEB 3]]
        answer = re.sub(
            r"\[CITE:\s*((?:\[(?:WEB|DOC) \d+\](?:\s*,\s*)?)+)\s*\]",
            lambda match: match.group(1).replace(", ", ""),
            answer
        )
        
        # Detect whether the user asked in Arabic
        user_used_arabic = bool(
            re.search(r"[\u0600-\u06FF]", question)
        )
        
        arabic_chars_in_answer = len(
            re.findall(r"[\u0600-\u06FF]", answer)
        )
        
        chinese_chars_in_answer = len(
            re.findall(r"[\u4e00-\u9fff]", answer)
        )
        
        # If an Arabic question accidentally produced a non-Arabic answer,
        # translate only the verified answer while preserving facts and citations.
        if (
            user_used_arabic
            and (
                arabic_chars_in_answer < 10
                or chinese_chars_in_answer > arabic_chars_in_answer
            )
        ):
            language_fix_prompt = f"""
        Translate the VERIFIED ANSWER below into natural Arabic.
        
        VERIFIED ANSWER:
        {answer}
        
        Rules:
        - Translate only the wording.
        - Do not add, remove, infer, or change any factual information.
        - Preserve product names, model numbers, acronyms, numbers, and technical terms accurately.
        - Preserve every citation exactly as [DOC X] or [WEB X].
        - Do not create new citations.
        - Do not use citation wrappers such as [CITE: ...].
        - Return only the translated answer.
        
        Arabic answer:
        """
        
            try:
                answer = call_qwen_llm(language_fix_prompt)
            except Exception as e:
                st.warning(f"Answer language correction error: {e}")
        
        # Run citation-wrapper cleanup again in case the language pass changed formatting
        answer = re.sub(
            r"\[CITE:\s*((?:\[(?:WEB|DOC) \d+\](?:\s*,\s*)?)+)\s*\]",
            lambda match: match.group(1).replace(", ", ""),
            answer
        )
        # Final answer quality guard for recommendation questions
        recommendation_cues = (
            "recommend",
            "recommendation",
            "best option",
            "next step",
            "career path",
            "should pursue",
        )
        
        is_recommendation_question = any(
            cue in question_lower
            for cue in recommendation_cues
        )
        
        if is_recommendation_question:
            # Remove inaccurate "three levels" wording about CTS / CTS-D / CTS-I
            answer = re.sub(
                r"(?im)^.*CTS.*three levels.*$",
                "",
                answer
            )
        
            # Remove unnecessary lists describing credentials only because
            # they are not present in the user's document/profile
            answer = re.sub(
                r"(?im)^.*(?:context|document|profile).*does not list.*$",
                "",
                answer
            )
            # Enforce CTS prerequisite before recommending CTS-I or CTS-D
            cts_preparation_match = re.search(
                r"\[DOC (\d+)\][\s\S]{0,1500}?CTS Preparation",
                context,
                re.IGNORECASE
            )
        
            active_cts_confirmed = bool(
                re.search(
                    r"\b(?:holds?|earned|obtained|certified in|active)\s+(?:an?\s+)?(?:AVIXA\s+)?CTS\b",
                    context,
                    re.IGNORECASE
                )
            )
        
            advanced_cts_recommended = bool(
                re.search(
                    r"\bCTS-(?:I|D)\b",
                    answer,
                    re.IGNORECASE
                )
            )
        
            if (
                cts_preparation_match
                and not active_cts_confirmed
                and advanced_cts_recommended
            ):
                doc_number = cts_preparation_match.group(1)
        
                answer = (
                    "Based on the provided profile, the most appropriate next certification "
                    "is the AVIXA CTS (Certified Technology Specialist) credential.\n\n"
                    f"The profile lists AVIXA CTS Preparation, but does not confirm that an "
                    f"active CTS credential has already been earned [DOC {doc_number}]. "
                    "Therefore, CTS should be completed first before considering a specialized "
                    "CTS-I or CTS-D path."
                )
            # Clean extra blank lines created by removals
            answer = re.sub(r"\n{3,}", "\n\n", answer).strip()
        # Show only sources actually cited in the final verified answer
        final_cited_docs = {
            int(x) for x in re.findall(r"\[DOC (\d+)\]", answer)
        }
        
        final_cited_web = {
            int(x) for x in re.findall(r"\[WEB (\d+)\]", answer)
        }
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer
        })
        st.subheader("🤖 AI Answer")
        st.write(answer)
        
        if claim_verification_passed and (final_cited_docs or final_cited_web):
            st.success("✅ Verified against cited sources")
        if final_cited_docs:
            st.markdown("### 📄 Document Sources")
        
            for (source_name, page_number), doc_number in sorted(
                doc_source_numbers.items(),
                key=lambda item: item[1]
            ):
                if doc_number in final_cited_docs:
                    st.write(
                        f"[DOC {doc_number}] {source_name} – Page {page_number}"
                    )
        if search_mode == "Documents + Web" and web_results and final_cited_web:
            st.markdown("### 🌐 Web Sources")
        
            for web_number, result in enumerate(web_results, start=1):
                if web_number not in final_cited_web:
                    continue
        
                title = result.get("title", "Web source")
                url = result.get("url", "")
                source_type = result.get("source_type", "External")
                manufacturer = get_manufacturer_name(url) if source_type == "Official" else None
        
                if url:
                    if source_type == "Official":
                        st.markdown(
                            f"- **[WEB {web_number}]** ✅ **Official Source · {manufacturer}** – [{title}]({url})"
                        )
                    else:
                        st.markdown(
                            f"- **[WEB {web_number}]** 🌐 **External Source** – [{title}]({url})"
                        )
