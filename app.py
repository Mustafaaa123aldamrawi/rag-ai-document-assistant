
import streamlit as st
import requests
import re
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
def call_qwen_llm(prompt, preferred_models_override=None):
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
    
    preferred_models = preferred_models_override or [
        "Qwen/Qwen2.5-Coder-32B-Instruct",
        "openai/gpt-oss-20b",
        "google/gemma-2-2b-it",
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
def call_conversation_llm(
    prompt=None,
    temperature=0.85,
    preferred_models_override=None,
    messages=None
):
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
    
    conversation_models = preferred_models_override or [
        "Qwen/Qwen2.5-72B-Instruct",
        "Qwen/Qwen2.5-32B-Instruct",
        "Qwen/Qwen2.5-14B-Instruct",
        "openai/gpt-oss-20b",
        "Qwen/Qwen2.5-Coder-32B-Instruct",
        "google/gemma-2-9b-it",
        "google/gemma-2-2b-it",
    ]
    
    available_model_ids = {
        model.get("id")
        for model in models_data
        if model.get("id")
    }
    
    selected_model = next(
        (
            model_id
            for model_id in conversation_models
            if model_id in available_model_ids
        ),
        None
    )
    
    if selected_model is None:
        raise Exception(
            "No compatible conversation model is currently available."
        )
    
    if messages is None:
        conversation_messages = [
            {
                "role": "system",
                "content": (
                    "You are AV Intelligence Assistant. "
                    "For normal conversation, behave as a warm, natural, "
                    "context-aware conversational assistant. "
                    "Follow the user's language, dialect, tone, and level of formality. "
                    "When the user speaks colloquial Arabic, reply naturally in the same dialect. "
                    "Do not mix Arabic dialects unnecessarily. "
                    "Do not default to Modern Standard Arabic when the user is speaking colloquially. "
                    "Be relaxed, expressive, and conversational rather than formal or robotic. "
                    "Use emojis naturally when appropriate. "
                    "Maintain conversation context. "
                    "If directly asked whether you are human, answer truthfully that you are an AI assistant."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    else:
        conversation_messages = messages
    payload = {
        "model": selected_model,
        "messages": conversation_messages,
        "temperature": temperature,
        "top_p": 0.9,
        "max_tokens": 1200,
    }
    
    response = requests.post(
        url,
        headers=headers,
        json=payload,
        timeout=60
    )
    
    if not response.ok:
        raise Exception(
            f"Hugging Face conversation API error "
            f"{response.status_code}: {response.text}"
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
    current_lower = current_question.lower()

    broad_capability_cues = (
        "capabilities",
        "features",
        "functions",
        "specifications",
        "overview",
        "شو أهم capabilities",
        "شو capabilities",
        "شو اهم capabilities",
    )
    
    if any(cue in current_lower for cue in broad_capability_cues):
        previous_product_terms = re.findall(
            r"\b(?:Q-SYS|Core\s*\d+[A-Za-z0-9-]*|MXA\d+|NV-\d+[A-Za-z0-9-]*)\b",
            previous_question,
            re.IGNORECASE
        )
    
        if previous_product_terms:
            product_name = " ".join(previous_product_terms)
            return f"{product_name} main capabilities features specifications"
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
- If the current follow-up asks broadly for capabilities, features, functions, specifications, or an overview, preserve only the product/model identity from the previous question and do not carry over the previous question's narrow feature or subtopic.
- For broad follow-ups such as "what are its main capabilities?" rewrite the query as a broad product capabilities query, not as a continuation of the previous feature-specific question.
- Do not answer the question.
- Do not add facts.
- Return only the standalone search query and nothing else.

Standalone search query:
"""

    rewritten_query = call_qwen_llm(rewrite_prompt)
    return rewritten_query.strip().strip('"')
def normalize_model_names(text):
    if not text:
        return text

    normalized_text = text

    replacements = (
        (r"Core\s+1\s+10f\s+v2", "Core 110f v2"),
        (r"Core\s+1\s+10F\s+v2", "Core 110F v2"),
        (r"Core\s+1\s+10\s+Series", "Core 110 Series"),
        (r"Core\s+1\s+10f", "Core 110f"),
        (r"Core\s+1\s+10F", "Core 110F"),
        (r"Core\s+1\s+10", "Core 110"),
    )

    for pattern, correct in replacements:
        normalized_text = re.sub(
            pattern,
            correct,
            normalized_text
        )

    return normalized_text
def polish_arabic_answer(answer):
    if not answer:
        return answer

    # Only polish answers that actually contain Arabic
    if not re.search(r"[\u0600-\u06FF]", answer):
        return answer

    original_citations = re.findall(
        r"\[(?:DOC|WEB) \d+\]",
        answer
    )

    polish_prompt = f"""
Perform minimal Arabic correction on the answer below. Do not rewrite the answer unless necessary to fix clear grammar, malformed wording, or unnatural literal translation.

Rules:
- Make the smallest possible changes needed to produce clear, natural Arabic.
- Do not paraphrase sentences that are already understandable and technically correct.
- Never replace a correct AV/IT term with a broader, different, or less precise meaning.
- Preserve the exact factual meaning.
- Do not add, remove, infer, or change any facts.
- Preserve every citation exactly as written, including all [DOC X] and [WEB X] labels.
- Preserve all product names, model numbers, standards, acronyms, and technical terms exactly.
- Preserve all numeric values exactly as written, including prices, quantities, dates, and percentages.
- Preserve currency codes and symbols exactly and keep them attached to the correct numeric value.
- Do not merge, reorder, duplicate, or split currency amounts.
- Prefer clear price formatting such as "USD 390", "EUR 375", "GBP 315", and "AUD 620" when the source contains those exact values.
- Never translate or transliterate certification and organization names such as AVIXA CTS.
- Keep established AV/IT terms in English when that is more natural.
- Do not translate "Core" as "النواة" when referring to Q-SYS Core.
- Remove awkward literal translations, mixed-script artifacts, malformed words, and unnatural Arabic.
- Rewrite awkward literal translations into natural professional Arabic while preserving the exact factual meaning.
- Prefer standard AV/IT terminology commonly used by Arabic-speaking engineers.
- Keep established technical terms such as Q-SYS, Core, SIP, SNMP, AV, DSP, Dante, AES67, API, UI, and scripting in English when translating them would sound unnatural or inaccurate.
- Do not translate product architecture terms into invented Arabic expressions; preserve the original English technical term when necessary.
- Avoid unnatural phrases produced by literal machine translation. Use fluent Modern Standard Arabic suitable for technical documentation.
- If an Arabic translation sounds uncommon, ambiguous, or unnatural to an AV/IT engineer, keep the original English technical term instead.
- Never create hybrid or invented Arabic technical expressions; use either a standard Arabic term or the established English term.
- Prefer simple, commonly understood technical Arabic over literal translations of marketing or architectural terminology.
- Do not use a more senior, stronger, or broader experience description than the source explicitly supports.
- Use clear, professional Arabic suitable for AV/IT engineers.
- Correct obvious Arabic grammar, agreement, and sentence-structure errors while preserving the exact meaning.
- Prefer natural Arabic phrasing such as "لتطبيقات مختلفة" instead of malformed constructions like "لأ التطبيقات المختلفة".
- When the answer contains multiple requirements, fees, steps, or categories, format them as clear bullet points instead of one dense paragraph.
- For pricing, keep each membership category and its fees together on one bullet or one clearly separated line.
- Preserve the original level of detail, but improve the structure when bullets make the answer clearer.
- Return only the polished answer.

ANSWER:
{answer}
"""

    try:
        polished_answer = call_qwen_llm(
            polish_prompt,
            preferred_models_override=[
                "openai/gpt-oss-20b",
                "Qwen/Qwen2.5-Coder-32B-Instruct",
            ]
        ).strip()
        
    except Exception:
        return answer

    polished_citations = re.findall(
        r"\[(?:DOC|WEB) \d+\]",
        polished_answer
    )
    # Safety guard: reject malformed mixed-script output
    if re.search(
        r"[\u0400-\u052F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]",
        polished_answer
    ):
        return answer
    # Safety guard: reject newly introduced Latin words
    original_latin_words = {
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", answer)
    }
    
    polished_latin_words = {
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]*", polished_answer)
    }
    
    if polished_latin_words - original_latin_words:
        return answer
    # Safety guard: reject critical AV meaning drift
    semantic_drift_rules = (
        (r"\bالصوت\w*", r"\bالموسيقى\w*"),
        (r"\bصوتي\w*", r"\bموسيقي\w*"),
    )
    
    for original_pattern, wrong_pattern in semantic_drift_rules:
        if (
            re.search(original_pattern, answer, re.IGNORECASE)
            and re.search(wrong_pattern, polished_answer, re.IGNORECASE)
        ):
            return answer
    # Safety guard: reject polishing if citations changed
    if original_citations != polished_citations:
        return answer

    return polished_answer
def clean_arabic_av_phrasing(text):
    if not text:
        return text

    replacements = {
        "إفروزتها بواسطة QSC": "تقديمها بواسطة QSC",
        "تجربة تحكم مستخدمية": "تجربة تحكم للمستخدم",
        "تمكين آلية": "الأتمتة",
        "يتضمن الحلول الخاصة بـ Q-SYS": "تتضمن حلول Q-SYS",
        "الاستاديات": "الملاعب",
        "واجهات تحكم مستخدمين": "واجهات تحكم للمستخدمين",
        "أدوات لإدارة وإدارة": "أدوات لإدارة",
        "دانت": "Dante",
        "الأوتوماتيك فيون (AV)": "AV",
        "ميكروفون عصبي": "ميكروفون مصفوفة",
        "الصوت والفيديو والإدارة": "الصوت والفيديو والتحكم",
        "الإشارات الصوتية والإدارية": "إشارات الصوت والتحكم",
    }

    cleaned_text = text

    for wrong, correct in replacements.items():
        cleaned_text = cleaned_text.replace(wrong, correct)

    return cleaned_text
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

    cts_exam_intent_terms = (
        "exam",
        "requirement",
        "requirements",
        "fee",
        "fees",
        "price",
        "pricing",
        "registration",
        "register",
        "eligibility",
    )
    
    if (
        ("avixa" in query_lower or "cts" in query_lower)
        and any(term in query_lower for term in cts_exam_intent_terms)
    ):
        query = (
            f"{query} official CTS exam requirements "
            "registration eligibility fees site:avixa.org"
        )

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

# Page configuration
st.set_page_config(
    page_title="AV Intelligence Assistant",
    page_icon="🤖",
    layout="wide"
)
# Initialize conversational memory
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_resolved_query" not in st.session_state:
    st.session_state.last_resolved_query = None

st.markdown(
"""
<div style="padding:28px 30px; border-radius:20px; border:1px solid rgba(120,120,120,0.18); background:linear-gradient(135deg, rgba(255,255,255,0.96), rgba(245,247,250,0.96)); box-shadow:0 8px 30px rgba(0,0,0,0.05); margin-bottom:24px;">

<div style="font-size:14px; font-weight:600; letter-spacing:0.08em; opacity:0.65; margin-bottom:8px;">
AV • UC • DOCUMENT INTELLIGENCE
</div>

<div style="font-size:38px; font-weight:800; line-height:1.15; margin-bottom:10px;">
🤖 AV Intelligence Assistant
</div>

<div style="font-size:17px; line-height:1.6; opacity:0.78; max-width:850px;">
AI-powered assistant for AV & Unified Communications, technical documents, trusted web research, troubleshooting, and source-grounded answers.
</div>

<div style="margin-top:18px; font-size:14px; opacity:0.65;">
📄 Documents &nbsp;&nbsp; • &nbsp;&nbsp; 🌐 Trusted Web &nbsp;&nbsp; • &nbsp;&nbsp; 🛠 Technical Guidance
</div>

</div>
""",
unsafe_allow_html=True
)
# Sidebar
with st.sidebar:
    st.markdown(
    """
    <div style="font-size:20px; font-weight:750; margin-bottom:6px;">
    📄 Document Upload
    </div>
    <div style="font-size:13px; opacity:0.65; margin-bottom:10px;">
    Upload one or more PDF documents for AI analysis.
    </div>
    """,
    unsafe_allow_html=True
    )

    uploaded_files = st.file_uploader(
    "Upload PDF files",
    type=["pdf"],
    accept_multiple_files=True
)

    st.divider()
    
    st.markdown(
    """
    <div style="font-size:20px; font-weight:750; margin-bottom:6px;">
    🔎 Search Mode
    </div>
    <div style="font-size:13px; opacity:0.65; margin-bottom:10px;">
    Choose where the assistant should look for information.
    </div>
    """,
    unsafe_allow_html=True
    )

    search_mode = st.radio(
        "Choose your search mode:",
        [
            "Documents Only",
            "Documents + Web",
            "Web Only"
        ],
        index=0,
        captions=[
            "Answer only from your uploaded PDF documents.",
            "Combine uploaded documents with trusted web sources. Works without a PDF too.",
            "Search the web only; no document upload required."
        ]
    )
st.divider()

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

            vector_store = create_vector_store(text_chunks)
            st.success(
                f"✅ {len(uploaded_files)} document(s) ready for AI analysis."
            )
        else:
            st.warning(
                "No readable text was found in this PDF."
            )

    except Exception as error:
        st.error(f"Error processing PDF: {error}")

# Display conversation history
if st.session_state.messages:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
# Main interface
st.markdown(
"""
<div style="padding:20px 22px; border-radius:16px; border:1px solid rgba(120,120,120,0.16); background:rgba(255,255,255,0.72); margin-bottom:12px;">
<div style="font-size:26px; font-weight:750; margin-bottom:6px;">
💬 Ask Your AV Assistant
</div>
<div style="font-size:14px; opacity:0.68;">
Ask about AV systems, products, troubleshooting, uploaded documents, or current technical information.
</div>
</div>
""",
unsafe_allow_html=True
)
if st.button("🗑️ Clear Chat"):
    st.session_state.messages = []
    st.session_state.last_resolved_query = None
    st.session_state.question_input = ""
    st.rerun()
st.caption("⚡ Quick prompts")

quick_col1, quick_col2 = st.columns(2)

with quick_col1:
    if st.button("🔧 Troubleshoot an AV issue", use_container_width=True):
        st.session_state.question_input = "Help me troubleshoot an AV system issue."
        st.rerun()

    if st.button("📄 Search my documents", use_container_width=True):
        st.session_state.question_input = "Search my uploaded documents and summarize the most relevant information."
        st.rerun()

with quick_col2:
    if st.button("🎛️ Explain a product", use_container_width=True):
        st.session_state.question_input = "Explain an AV product and its main capabilities."
        st.rerun()

    if st.button("⚖️ Compare technologies", use_container_width=True):
        st.session_state.question_input = "Compare two AV technologies and explain their main differences."
        st.rerun()
def submit_question():
    current_question = st.session_state.get("question_input", "").strip()

    if current_question:
        st.session_state.pending_question = current_question
        st.session_state.question_input = ""
question = st.text_area(
    "Message AV Intelligence Assistant",
    placeholder="Ask about AV systems, uploaded documents, products, troubleshooting, or current technical information...",
    key="question_input",
    height=90
)

send_col1, send_col2 = st.columns([12, 1])

with send_col2:
    submitted = st.button(
        "↑",
        type="primary",
        use_container_width=True,
        on_click=submit_question
    )

if submitted:
    question = st.session_state.pop("pending_question", "")
    if question:
        st.session_state.messages.append({
            "role": "user",
            "content": question
        })
    question_lower = question.lower() if question else ""

    # Intelligent conversation router
    router_history = ""
    
    for message in st.session_state.messages[-5:-1]:
        role = "User" if message["role"] == "user" else "Assistant"
        router_history += f"{role}: {message['content']}\n"
    
    router_prompt = f"""
    Classify the user's CURRENT MESSAGE into exactly ONE intent.
    
    Allowed intents:
    
    CASUAL
    WRITING
    TRANSLATION
    TECHNICAL
    DOCUMENT
    WEB_CURRENT
    
    Definitions:
    
    CASUAL:
    Normal conversation or general assistance that does not require external research.
    Examples include:
    - greetings
    - jokes
    - opinions
    - emotional/supportive conversation
    - everyday questions
    - general advice
    - asking whether you can help
    - general work or project discussion when the user has not yet provided enough information
    - short conversational follow-ups
    
    Examples:
    "How are you?"
    "احكيلي اشي يضحكني"
    "شو رأيك باسم التطبيق؟"
    "بتقدر تساعدني بشغلي؟"
    "Can you help me with my work?"
    "عندي مشروع ومش عارف كيف أبلش"
    
    WRITING:
    The user wants help creating, rewriting, polishing, formatting, or replying to written content.
    Examples:
    "Write an email for me"
    "زبطلي هاد الايميل"
    "Give me a reply to this"
    "اعطيني رد عليه"
    "Can you help me do a report for my work?"
    "Write a project status report"
    
    TRANSLATION:
    The user explicitly asks to translate text from one language to another.
    Examples:
    "ترجم"
    "ترجمه للعربي"
    "Translate this to English"
    "لا اكتبو بالانجليزي"
    
    TECHNICAL:
    The user asks a technical, engineering, AV/UC, product, troubleshooting, design, installation, configuration, or professional-domain question that can be answered without requiring current web information.
    Examples:
    "Tell me about Q-SYS"
    "What is Dante?"
    "How does HDMI EDID work?"
    "شو وظيفة MXA920؟"
    "How should I troubleshoot this AV issue?"
    
    DOCUMENT:
    The user explicitly asks for information from, about, or based on an uploaded document or documents.
    Examples:
    "According to the PDF..."
    "حسب الملف شو مكتوب؟"
    "Summarize this document"
    "What does my CV say about Q-SYS?"
    
    WEB_CURRENT:
    The user explicitly needs current, latest, changing, externally verified, or web-researched information.
    Examples:
    "What is the latest Q-SYS firmware?"
    "Search the web for the newest Barco model"
    "كم سعر CTS حالياً؟"
    "Find current Samsung video wall models"
    "What changed in Dante recently?"
    
    Important routing rules:
    
    - Classify the CURRENT MESSAGE by the user's actual intent, not merely by keywords.
    - Do NOT classify a request as WEB_CURRENT merely because it concerns work, projects, products, reports, or professional topics.
    - Do NOT use WEB_CURRENT when the user is simply asking for help writing, planning, discussing, or understanding something.
    - Technical product questions are TECHNICAL unless the user explicitly needs current/latest/web-verified information.
    - Requests to write or reply are WRITING even when the subject is technical or professional.
    - Explicit translation requests are TRANSLATION.
    - Explicit requests based on uploaded files are DOCUMENT.
    - Use recent conversation only to resolve short follow-ups and references.
    - A follow-up should preserve the intent of the immediately relevant conversation when appropriate.
    - If a short message changes the requested action, classify according to the new action.
    
    Recent conversation:
    {router_history}
    
    Current message:
    {question}
    
    Return EXACTLY ONE label and nothing else:
    CASUAL
    WRITING
    TRANSLATION
    TECHNICAL
    DOCUMENT
    WEB_CURRENT
    """
    detected_conversation_style = "NEUTRAL"
    # Strong dialect hints before LLM classification
    dialect_hint = None
    
    levantine_cues = (
        "شو",
        "ليش",
        "كيفك",
        "وين",
        "هيك",
        "هلق",
        "هلأ",
        "بدي",
        "بدك",
        "بدنا",
        "بزبط",
        "زهقت",
        "بتنصحني",
        "احكيلي",
        "قلي",
        "عندي",
        "معي",
        "مو",
        "مش",
    )
    
    egyptian_cues = (
        "ازيك",
        "إزيك",
        "عايز",
        "عاوز",
        "ليه",
        "كده",
        "إيه",
        "ايه",
        "مش عارف",
    )
    
    iraqi_cues = (
        "شلون",
        "شكو",
        "اكو",
        "أكو",
        "شنو",
        "هواية",
        "ليش هيج",
    )
    
    gulf_cues = (
        "وش",
        "وشو",
        "شلونك",
        "أبي",
        "ابغى",
        "أبغى",
        "وشلون",
    )
    
    if any(cue in question_lower for cue in levantine_cues):
        dialect_hint = "LEVANTINE"
    
    elif any(cue in question_lower for cue in egyptian_cues):
        dialect_hint = "EGYPTIAN"
    
    elif any(cue in question_lower for cue in iraqi_cues):
        dialect_hint = "IRAQI"
    
    elif any(cue in question_lower for cue in gulf_cues):
        dialect_hint = "GULF"
    
    if question:
        try:
            router_result = call_qwen_llm(router_prompt).strip().upper()

            allowed_intents = {
                "CASUAL",
                "WRITING",
                "TRANSLATION",
                "TECHNICAL",
                "DOCUMENT",
                "WEB_CURRENT",
            }
            
            router_intent = (
                router_result
                if router_result in allowed_intents
                else "CASUAL"
            )
            
            is_casual_chat = router_intent == "CASUAL"
            is_writing_request = router_intent == "WRITING"
            is_translation_request = router_intent == "TRANSLATION"
            is_technical_request = router_intent == "TECHNICAL"
            is_document_request = router_intent == "DOCUMENT"
            is_web_current_request = router_intent == "WEB_CURRENT"

            if is_casual_chat and question:
                if dialect_hint:
                    detected_conversation_style = dialect_hint
            
                else:
                    dialect_prompt = f"""
            Detect the user's language and speaking style from the CURRENT MESSAGE and recent conversation.
            
            Recent conversation:
            {router_history}
            
            Current message:
            {question}
            
            Return exactly ONE label:
            
            LEVANTINE
            EGYPTIAN
            IRAQI
            GULF
            MAGHREBI
            FORMAL_ARABIC
            ENGLISH
            OTHER
            
            Rules:
            - Base the decision mainly on the user's own wording.
            - Do not guess a regional dialect if the evidence is weak.
            - Jordanian, Palestinian, Lebanese, and Syrian conversational Arabic should return LEVANTINE.
            - Saudi, Emirati, Kuwaiti, Qatari, Bahraini, and Omani conversational Arabic should return GULF.
            - If Arabic is colloquial but the exact dialect is uncertain, return OTHER.
            - Return only the label and nothing else.
            """
            
                try:
                    detected_conversation_style = call_qwen_llm(
                        dialect_prompt
                    ).strip().upper()
                except Exception:
                    detected_conversation_style = "OTHER"
        except Exception:
            is_casual_chat = False
    else:
        is_casual_chat = False 
    # Deterministic dialect hints always take priority
    if dialect_hint:
        detected_conversation_style = dialect_hint
    
    if not question:
        st.warning("Please enter a question.")
    
    elif is_writing_request:
        writing_prompt = f"""
    You are AV Intelligence Assistant.
    
    The user wants help creating, rewriting, polishing, formatting, or replying to written content.
    
    Recent conversation:
    {router_history}
    
    Current user request:
    {question}
    
    Instructions:
    - Follow the user's requested language.
    - If the user asks for English, write in natural professional English.
    - If the user asks for Arabic, match the user's appropriate Arabic style.
    - Preserve all facts and details provided by the user.
    - Do not invent missing project details, names, dates, technical facts, or commitments.
    - Do not search the web unless the user explicitly asks for research or current information.
    - If enough information is available, produce the requested text directly.
    - If essential information is genuinely missing, ask one concise clarifying question.
    - For emails and professional reports, use a natural professional tone rather than robotic wording.
    - Return only the useful response to the user.
    """
    
        try:
            direct_answer = call_conversation_llm(
                prompt=writing_prompt,
                temperature=0.3
            ).strip()
        except Exception as e:
            direct_answer = f"AI model error: {e}"
    
        if direct_answer:
            st.session_state.messages.append({
                "role": "assistant",
                "content": direct_answer
            })
    
            st.markdown(
                """
                <div style="padding:18px 20px; border-radius:16px; border:1px solid rgba(120,120,120,0.16);">
                    <div style="font-size:24px; font-weight:750; margin-bottom:8px;">
                        🤖 AI Answer
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
            st.markdown(direct_answer)
            st.stop()
    elif is_translation_request:
        translation_prompt = f"""
    You are AV Intelligence Assistant.
    
    The user wants a faithful translation.
    
    Recent conversation:
    {router_history}
    
    Current user request:
    {question}
    
    Instructions:
    - Translate exactly what the user asked to translate.
    - Preserve the full meaning, tone, structure, names, dates, numbers, and technical terms.
    - Do not summarize.
    - Do not omit information.
    - Do not add greetings, explanations, emojis, or extra commentary unless they already exist in the source text.
    - If the user specifies a target language, use that language.
    - If the target language is implied by the conversation, follow that context.
    - Keep professional wording professional and casual wording casual.
    - For technical AV/UC terms, preserve product names and standard terminology accurately.
    - Return only the translation.
    """
    
        try:
            direct_answer = call_conversation_llm(
                prompt=translation_prompt,
                temperature=0.1
            ).strip()
        except Exception as e:
            direct_answer = f"AI model error: {e}"
    
        if direct_answer:
            st.session_state.messages.append({
                "role": "assistant",
                "content": direct_answer
            })
    
            st.markdown(
                """
                <div style="padding:18px 20px; border-radius:16px; border:1px solid rgba(120,120,120,0.16);">
                    <div style="font-size:24px; font-weight:750; margin-bottom:8px;">
                        🤖 AI Answer
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    
            st.markdown(direct_answer)
            st.stop()
    
    elif search_mode == "Web Only" and not is_casual_chat:
        try:
            with st.spinner("Searching trusted sources and preparing your answer..."):
                # Preserve conversation context for Web Only follow-up questions
                web_only_question = question
                
                web_only_follow_up_starters = (
                    "what about",
                    "how about",
                    "and what",
                    "and how",
                    "and does",
                    "and is",
                    "and can",
                    "طيب",
                    "طيب شو",
                    "وشو",
                    "وماذا",
                )
                
                is_web_only_follow_up = question.lower().strip().startswith(
                    web_only_follow_up_starters
                )
                
                if is_web_only_follow_up:
                    previous_user_questions = [
                        message["content"]
                        for message in st.session_state.messages[:-1]
                        if message["role"] == "user"
                    ]
                
                    if previous_user_questions:
                        previous_question = previous_user_questions[-1]
                
                        web_only_question = rewrite_follow_up_query(
                            previous_question,
                            question
                        )
                qsys_overview_question = (
                    "q-sys" in web_only_question.lower()
                    and any(
                        phrase in web_only_question.lower()
                        for phrase in (
                            "what is",
                            "explain",
                            "overview",
                            "about q-sys",
                            "ما هو",
                            "ما هي",
                            "اشرح",
                            "شرح",
                            "شو هو",
                            "شو هي",
                        )
                    )
                )
                
                if qsys_overview_question:
                    web_search_query = "Q-SYS platform system overview integrated audio video control"
                else:
                    web_search_query = normalize_search_query(web_only_question)
                
                web_results = search_web_tavily(web_search_query)

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
{web_only_question}

Web search context:
{web_context}

Answer using only the web search context above.
Do not invent information that is not supported by the web results.

Answer in the same primary language as the user's question.

If the user asks in Arabic:
- Write fluent, natural Modern Standard Arabic suitable for AV/IT professionals.
- Summarize and explain the source information naturally; do not translate source sentences word-for-word.
- Keep established AV/IT terms and product terminology in English when that is clearer, including Q-SYS, Q-SYS OS, Core, SIP, SNMP, VoIP, API, UI, DSP, Dante, and AES67.
- Never invent Arabic translations for product names, architecture terms, protocols, or technical features.
- If a source phrase cannot be translated naturally and accurately, omit that phrase instead of producing malformed Arabic.
- Prefer a concise 1-2 sentence overview followed by only 3-5 clear bullet points.
- Select only the most relevant facts needed to answer the user's question.
- Do not attempt to translate or summarize every available web source.
- Prefer fewer high-confidence facts over a longer answer with awkward wording.
- Avoid repetition and include only the most useful information needed to answer the question.
- Do not transliterate English technical terms into Arabic letters; keep the original English term instead.
- Every factual sentence or bullet point must end with at least one supporting [WEB X] citation.

For every factual claim, cite the supporting source using the exact format [WEB X],
for example [WEB 1] or [WEB 2].

Use only source numbers that actually appear in the Web Search context.
Do not create or guess source numbers.
If multiple sources support the same claim, cite them like [WEB 1] [WEB 2].
"""

            answer = call_qwen_llm(prompt)

            if re.search(r"[\u0400-\u052F\u3040-\u30FF\u4E00-\u9FFF\uAC00-\uD7AF]", answer):
                repair_prompt = f"""
            Repair only the malformed mixed-script words in the Arabic answer below.
            
            Rules:
            - Preserve the exact factual meaning.
            - Preserve every [WEB X] citation exactly as written.
            - Preserve product names, model numbers, acronyms, and technical terms.
            - Replace only malformed words containing Cyrillic, Japanese, Korean, or Chinese characters.
            - Do not rewrite correct sentences.
            - Do not add or remove facts.
            - Return only the repaired answer.
            
            ANSWER:
            {answer}
            """
            
                try:
                    repaired_answer = call_qwen_llm(
                        repair_prompt,
                        preferred_models_override=[
                            "openai/gpt-oss-20b",
                            "Qwen/Qwen2.5-Coder-32B-Instruct",
                        ]
                    ).strip()
            
                    if repaired_answer:
                        answer = repaired_answer
            
                except Exception:
                    pass

            answer = normalize_model_names(answer)
            answer = polish_arabic_answer(answer)
            answer = clean_arabic_av_phrasing(answer)
            

            # Keep Web Only answers in the same language as the user's question
            web_only_user_used_arabic = bool(
                re.search(r"[\u0600-\u06FF]", question)
            )
            
            web_only_user_used_english = (
                bool(re.search(r"[A-Za-z]", question))
                and not web_only_user_used_arabic
            )
            
            web_only_arabic_chars = len(
                re.findall(r"[\u0600-\u06FF]", answer)
            )
            
            if (
                web_only_user_used_english
                and web_only_arabic_chars >= 10
            ):
                english_fix_prompt = f"""
            Translate the VERIFIED ANSWER below into clear, natural English.
            
            VERIFIED ANSWER:
            {answer}
            
            Rules:
            - Translate only the wording.
            - Do not add, remove, infer, or change any factual information.
            - Preserve product names, model numbers, acronyms, numbers, and technical terms accurately.
            - Preserve every citation exactly as written, including all [WEB X] labels.
            - Do not create new citations.
            - Return only the translated answer.
            """
            
                try:
                    answer = call_qwen_llm(
                        english_fix_prompt,
                        preferred_models_override=[
                            "openai/gpt-oss-20b",
                            "Qwen/Qwen2.5-Coder-32B-Instruct",
                        ]
                    ).strip()
                except Exception:
                    pass
            
            st.markdown(
            """
            <div style="padding:18px 20px; border-radius:16px; border:1px solid rgba(120,120,120,0.16); background:rgba(255,255,255,0.78); margin-top:14px; margin-bottom:10px;">
            <div style="font-size:24px; font-weight:750; margin-bottom:8px;">
            🤖 AI Answer
            </div>
            </div>
            """,
            unsafe_allow_html=True
            )
            
            st.markdown(answer)
    
            st.markdown(
            """
            <div style="padding:16px 18px; border-radius:14px; border:1px solid rgba(120,120,120,0.14); background:rgba(255,255,255,0.72); margin-top:18px; margin-bottom:10px;">
            <div style="font-size:22px; font-weight:750;">
            🌐 Web Sources
            </div>
            <div style="font-size:13px; opacity:0.65; margin-top:4px;">
            Sources used to support the answer above.
            </div>
            </div>
            """,
            unsafe_allow_html=True
            )
    
            for source_number, result in enumerate(web_results, start=1):
                title = result.get("title", "Web source")
                url = result.get("url", "")
                source_type = result.get("source_type", "External")
            
                if url:
                    if source_type == "Official":
                        manufacturer = get_manufacturer_name(url)
                        st.markdown(
                            f"- **[WEB {source_number}]** ✅ **{manufacturer} Official** - [{title}]({url})"
                        )
                    else:
                        st.markdown(
                            f"- **[WEB {source_number}]** 🌐 **External Source** - [{title}]({url})"
                        )
        except Exception as e:
            st.error(f"Web search error: {e}")

    elif (
        search_mode == "Documents Only"
        and not uploaded_files
        and not is_casual_chat
    ):
        st.warning("Please upload at least one PDF document first.")
    
    elif (
        search_mode == "Documents Only"
        and not document_pages
        and not is_casual_chat
    ):
        st.warning("The uploaded PDF files do not contain readable text.")
    
    elif (
        search_mode == "Documents Only"
        and vector_store is None
        and not is_casual_chat
    ):
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
            "main responsibilities",
            "responsibilities",
            "مسؤولياته الرئيسية",
            "المسؤوليات الرئيسية",
            "مسؤولياته",
            "واجباته",
            "مسماه الوظيفي",
            "المسمى الوظيفي",
            "مسماه الوظيفي الحالي",
            "المسمى الوظيفي الحالي",
            "وظيفته الحالية",
            "ما هي وظيفته",
            "شو وظيفته",
            "مهاراته التقنية",
            "المهارات التقنية",
            "مهارات تقنية",
            "أقوى مهاراته التقنية",
            "career focus",
            "professional focus",
            "تركيزه المهني",
            "التركيز المهني",
            "تركيز مهني",
            "مجاله المهني",
            "خبراته المهنية",
            "خبرته المهنية",
            "الخبرات المهنية",
            "الخبرة المهنية",
        ]
        cv_summary_phrases = (
            "what in the cv",
            "what is in the cv",
            "what's in the cv",
            "what is inside the cv",
            "what does the cv contain",
            "summarize the cv",
            "summarise the cv",
            "summary of the cv",
            "tell me about the cv",
            "what is in the resume",
            "what's in the resume",
            "summarize the resume",
            "tell me about the resume",
            "شو في بال cv",
            "شو في بالسيرة الذاتية",
            "شو موجود بالسيرة الذاتية",
            "لخص ال cv",
            "لخص السيرة الذاتية",
        )
        is_summary_question = (
            any(
                phrase in question_lower
                for phrase in summary_phrases
            )
            or any(
                phrase in question_lower
                for phrase in cv_summary_phrases
            )
            or question_lower.startswith("summarize ")
            or question_lower.startswith("summarise ")
        )
        is_profile_recommendation_question_early = (
            any(
                term in question_lower
                for term in ("certification", "certifications")
            )
            and any(
                cue in question_lower
                for cue in ("should", "recommend", "next", "pursue")
            )
        )
        
        if is_profile_recommendation_question_early:
            is_summary_question = True
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
        "تبعتو",
        "تبعو",
        "تبعها",
        "تبعهم",
        "هاد",
        "هاي",
        "هيدا",
        "هذي",
        }
        
        retrieval_question_words = set(
            question_lower
            .replace("?", "")
            .replace(",", "")
            .replace(".", "")
            .split()
        )
        retrieval_follow_up_starters = (
            "if ",
            "what happens",
            "what about",
            "how about",
            "and ",
            "then ",
        "طيب",
        "وإذا",
        "اذا",
        "إذا",
        )
        
        retrieval_starts_like_follow_up = question_lower.strip().startswith(
            retrieval_follow_up_starters
        )
        retrieval_is_follow_up = (
            bool(retrieval_question_words & retrieval_follow_up_references)
            or retrieval_starts_like_follow_up
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
                search_query = f"{previous_question} {search_query} {question}".strip()
        # Prefer the document whose full content best matches the user's subject
        if not matched_source and not is_casual_chat:
            normalized_question = "".join(
                char.lower()
                for char in search_query
                if char.isalnum()
            )
        
            source_scores = {}
        
            for page in document_pages:
                source_name = page.get("source")
                page_text = page.get("text", "")
        
                normalized_page_text = "".join(
                    char.lower()
                    for char in page_text
                    if char.isalnum()
                )
        
                if source_name not in source_scores:
                    source_scores[source_name] = 0
        
                if "qsys" in normalized_question:
                    source_scores[source_name] += normalized_page_text.count("qsys")
        
                if "core110" in normalized_question:
                    source_scores[source_name] += (
                        normalized_page_text.count("core110") * 2
                    )
        
            if source_scores:
                best_source = max(
                    source_scores,
                    key=source_scores.get
                )
        
                if source_scores[best_source] > 0:
                    matched_source = best_source
        if is_casual_chat:
            search_results = []
        
        elif vector_store is None:
            search_results = []
        
        elif matched_source:
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
        keyword_source_text = search_query if retrieval_is_follow_up else question
        question_keywords = [
            word.lower().strip(".,?!:;()[]{}\"'")
            for word in keyword_source_text.split()
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
            "certificates",
            "does",
            "do",
            "did",
            "is",
            "are",
            "has",
            "have",
            "had",
            "can",
            "could",
            "support",
            "supports",
            "supported",
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
        verification_keyword_aliases = {
            "redundant": ("redundant", "redundancy"),
            "redundancy": ("redundant", "redundancy"),
            "connection": ("connection", "connections"),
            "connections": ("connection", "connections"),
            "network": ("network", "networks"),
            "networks": ("network", "networks"),
            "support": ("support", "supports", "supported", "supporting"),
            "supports": ("support", "supports", "supported", "supporting"),
            "responsibility": (
            "responsibility",
            "responsibilities",
            "managed",
            "coordinated",
            "worked",
            "applied",
            "supported",
            "planning",
            "delivery",
        ),
        "responsibilities": (
            "responsibility",
            "responsibilities",
            "managed",
            "coordinated",
            "worked",
            "applied",
            "supported",
            "planning",
            "delivery",
        ),
        "career": (
            "career",
            "professional",
            "summary",
            "experience",
            "audio-visual",
            "project management",
            "technology",
        ),
        "focus": (
            "focus",
            "professional",
            "summary",
            "experience",
            "audio-visual",
            "project management",
            "technology",
        ),
        }
        evidence_documents = []
        
        for document, score in search_results:
            document_text = document.page_content.lower()
        
            keyword_matches = sum(
                1
                for keyword in evidence_keywords
                if any(
                    alias in document_text
                    for alias in verification_keyword_aliases.get(
                        keyword,
                        (keyword,)
                    )
                )
            )
        
            product_matches = sum(
                1 for keyword in product_keywords
                if keyword in document_text
            )
        
            if (
                score <= RELEVANCE_THRESHOLD
                or (
                    is_verification_question
                    and keyword_matches > 0
                )
                or (
                    retrieval_is_follow_up
                    and keyword_matches >= 2
                )
            ):
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
                    and keyword_matches >= max(
                        1,
                        len(evidence_keywords) - 1
                    )
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
        # Expand context with pages that explicitly contain the requested subject
        if any(
            phrase in question_lower
            for phrase in (
                "شو بحكي الدوكيومنت عن ",
                "شو بحكي المستند عن ",
                "شو مكتوب بالدوكيومنت عن ",
                "شو مكتوب بالمستند عن ",
            )
        ):
            requested_subject = question.split(" عن ", 1)[1].strip().rstrip("؟?")
        
            normalized_requested_subject = "".join(
                char.lower()
                for char in requested_subject
                if char.isalnum()
            )
        
            for page in document_pages:
                page_text = page.get("text", "")
        
                normalized_page_text = "".join(
                    char.lower()
                    for char in page_text
                    if char.isalnum()
                )
        
                if (
                    normalized_requested_subject
                    and normalized_requested_subject in normalized_page_text
                ):
                    doc_key = (
                        page.get("source"),
                        page.get("page_number")
                    )
        
                    doc_number = doc_source_numbers.get(doc_key)
        
                    if doc_number is not None:
                        subject_page_text = (
                            f"[DOC {doc_number}]\n"
                            f"Source: {page.get('source')}\n"
                            f"Page: {page.get('page_number')}\n"
                            f"{page_text}"
                        )
        
                        if subject_page_text not in expanded_texts:
                            expanded_texts.append(subject_page_text)
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
            and not is_casual_chat
        ):
            st.subheader("🤖 AI Answer")
            st.write("The information was not found in the document.")
            st.stop()
        subject_found = False

        if is_summary_question:
            summary_pages = document_pages
            
            if any(
                phrase in question_lower
                for phrase in cv_summary_phrases
            ):
                cv_pages = [
                    page
                    for page in document_pages
                    if (
                        "cv" in page.get("source", "").lower()
                        or "resume" in page.get("source", "").lower()
                    )
                ]
            
                if cv_pages:
                    summary_pages = cv_pages
            full_document_text = "\n".join(
                page["text"] for page in summary_pages
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
            elif (
                "main responsibilities" in question_lower
                or "responsibilities" in question_lower
                or "responsibility" in question_lower
                or "duties" in question_lower
                or "مسؤولياته الرئيسية" in question_lower
                or "المسؤوليات الرئيسية" in question_lower
                or "مسؤولياته" in question_lower
                or "واجباته" in question_lower
            ):
                start = full_document_lower.find("professional summary")
                end = full_document_lower.find("professional experience", start)
            
                if start != -1:
                    if end != -1:
                        context = full_document_text[start:end].strip()
                    else:
                        context = full_document_text[start:].strip()
                else:
                    context = full_document_text
            elif (
                "career focus" in question_lower
                or "professional focus" in question_lower
            ):
                start = full_document_lower.find("professional summary")
                end = full_document_lower.find("professional experience", start)
            
                if start != -1:
                    if end != -1:
                        context = full_document_text[start:end].strip()
                    else:
                        context = full_document_text[start:].strip()
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
        is_document_focused_question = False
        
        if search_mode == "Documents + Web" and not is_casual_chat:
            
            document_only_phrases = (
                "what does the document say",
                "according to the document",
                "in this document",
                "in this pdf",
                "based on the document",
                "based only on the document",
                "according to this document",
                "what does this document say",
            "شو بحكي الدوكيومنت",
            "شو بحكي المستند",
            "شو مكتوب بالدوكيومنت",
            "شو مكتوب بالمستند",
            "حسب الدوكيومنت",
            "حسب المستند",
            "بناء على الدوكيومنت",
            "بناء على المستند",
            "في هذا الدوكيومنت",
            "في هذا المستند",
            "بالدوكيومنت",
            "بالمستند",
            )
        
            is_document_focused_question = (
                is_document_request
                or (
                    not is_web_current_request
                    and any(
                        phrase in question_lower
                        for phrase in document_only_phrases
                    )
                )
            )
        current_web_signals = (
            "current",
            "currently",
            "latest",
            "today",
            "updated",
            "up-to-date",
            "as of",
        )
        
        is_current_web_question = (
            is_web_current_request
            or (
                not is_document_request
                and any(
                    signal in question_lower
                    for signal in current_web_signals
                )
            )
        )
        if "document_scope_active" not in st.session_state:
            st.session_state.document_scope_active = False
        
        if is_current_web_question:
            st.session_state.document_scope_active = False
            web_search_query = build_document_aware_web_query(
                question,
                context
            )
        
        elif is_document_focused_question:
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
        "طيب",
        "طيب شو",
        "وشو",
        "شو كمان",
        "وبعدين",
        "وكمان",
        )

        web_follow_up_references = {
            "it",
            "its",
            "this",
            "that",
            "they",
            "their",
            "them",
        "تبعتو",
        "تبعو",
        "تبعها",
        "تبعهم",
        "هاد",
        "هاي",
        "هيدا",
        "هذي",
        }

        web_question_words = set(
            question_lower
            .replace("?", "")
            .replace(",", "")
            .replace(".", "")
            .split()
        )

        document_reference_phrases = (
            "this person",
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
                    resolved_previous_question = previous_question

                    if st.session_state.get("last_resolved_query"):
                        resolved_previous_question = st.session_state.last_resolved_query
                    
                    web_search_query = rewrite_follow_up_query(
                        resolved_previous_question,
                        question
                    )

                    if (
                        web_search_query
                        and re.search(
                            r"\b(?:Q-SYS|Core\s*\d+|MXA\d+|NV-\d+)\b",
                            web_search_query,
                            re.IGNORECASE
                        )
                    ):
                        st.session_state.last_resolved_query = web_search_query
        
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
            if (
                web_search_query
                and (
                    is_web_current_request
                    or is_technical_request
                    or (
                        not is_document_request
                        and search_mode == "Documents + Web"
                    )
                )
            ):
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
        def get_doc_number_for_phrase(phrase):
            phrase_lower = phrase.lower()
        
            for page in document_pages:
                page_text = page.get("text", "").lower()
        
                if phrase_lower in page_text:
                    doc_key = (
                        page.get("source"),
                        page.get("page_number")
                    )
                    return doc_source_numbers.get(doc_key)
        
            return None
        # Direct extractive handling for career focus questions
        career_focus_question = any(
            phrase in question_lower
            for phrase in (
                "career focus",
                "professional focus",
            "تركيزه المهني",
            "التركيز المهني",
            "تركيز مهني",
            "مجاله المهني",
            )
        )
        
        if career_focus_question and search_mode == "Documents Only":
            full_document_text = "\n".join(
                page["text"] for page in document_pages
            )
        
            full_document_lower = full_document_text.lower()
        
            start = full_document_lower.find("professional summary")
            end = full_document_lower.find("professional experience", start)
        
            if start != -1:
                if end != -1:
                    career_focus_text = full_document_text[start:end].strip()
                else:
                    career_focus_text = full_document_text[start:].strip()
        
                career_focus_text = career_focus_text.replace(
                    "Professional Summary",
                    ""
                ).strip()
        
                if career_focus_text:
                    career_focus_doc_number = get_doc_number_for_phrase(
                        "professional summary"
                    )
        
                    direct_answer = career_focus_text
        
                    if career_focus_doc_number:
                        direct_answer += f" [DOC {career_focus_doc_number}]"
        # Direct handling for job title questions
        job_title_phrases = [
            "job title",
            "current job title",
            "current title",
            "professional title",
            "what is mustafa's job",
            "what is mustafa’s job"
            "مسماه الوظيفي",
            "المسمى الوظيفي",
            "مسماه الوظيفي الحالي",
            "المسمى الوظيفي الحالي",
            "وظيفته الحالية",
            "ما هي وظيفته",
            "شو وظيفته",
        ]

        job_title_only_question = (
            any(phrase in question_lower for phrase in job_title_phrases)
            and not any(
                cue in question_lower
                for cue in (
                    "responsibilities",
                    "responsibility",
                    "duties",
                    "skills",
                    "experience",
                    "technologies",
                    "technical",
                    "what does he do",
                    "what does she do"
                )
            )
        )
        
        if job_title_only_question:
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
                if direct_answer:
                    job_title_doc_number = get_doc_number_for_phrase(
                        "Project Manager | AV & Education Technology Professional"
                    )
                    
                    if job_title_doc_number:
                        direct_answer += f" [DOC {job_title_doc_number}]"
        if (
            search_mode == "Documents Only"
            and "certification" in question_lower
            and not is_verification_question
        ):
            full_document_text = "\n".join(
                page["text"] for page in document_pages
            )
            full_document_lower = full_document_text.lower()
        
            start = full_document_lower.find("certifications & training")
            end = full_document_lower.find("languages", start)
        
            if start != -1:
                if end != -1:
                    certification_text = full_document_text[start:end]
                else:
                    certification_text = full_document_text[start:]
        
                direct_answer = (
                    certification_text
                    .replace("Certifications & Training", "")
                    .strip()
                )
        
                if direct_answer:
                    certification_doc_number = get_doc_number_for_phrase(
                        "Certifications & Training"
                    )
                    
                    if certification_doc_number:
                        direct_answer += f" [DOC {certification_doc_number}]"
                # Direct extractive answer for technologies and technical skills
        if (
            search_mode == "Documents Only"
            and (
                "technolog" in question_lower
                or "technical skill" in question_lower
                or "tools" in question_lower
                or "platforms" in question_lower
                or "systems" in question_lower
                or "مهاراته التقنية" in question_lower
                or "المهارات التقنية" in question_lower
                or "مهارات تقنية" in question_lower
                or "أقوى مهاراته التقنية" in question_lower
            )
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

                if direct_answer:
                    technical_doc_number = get_doc_number_for_phrase(
                        "Core Skills"
                    )
                    
                    if technical_doc_number:
                        direct_answer += f" [DOC {technical_doc_number}]"
                
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
        if (
            "career focus" in question_lower
            or "professional focus" in question_lower
        ):
            summary_instruction = (
                "Answer with 2-3 concise sentences describing the person's professional focus "
                "using ONLY facts explicitly stated in the provided Professional Summary context. "
                "Prefer the wording and terminology used in the source. "
                "Do not mention the person's name unless necessary. "
                "Do not invent, infer, broaden, or add employers, locations, sectors, roles, "
                "technologies, responsibilities, or experience that are not explicitly stated in the context. "
                "Do not use evaluative terms such as strong, extensive, deep, specialized, advanced, expert, or highly experienced unless those exact terms are explicitly supported by the context. "
                "If a detail is not explicitly stated, omit it."
            )
        else:
            summary_instruction = (
                "Answer with 3 complete sentences describing the person's professional experience."
            )
                    
        if is_summary_question:
            is_cv_summary_request = any(
                phrase in question_lower
                for phrase in cv_summary_phrases
            )
        
            if is_cv_summary_request:
                cv_full_text = "\n".join(
                    page.get("text", "")
                    for page in document_pages
                    if (
                        "cv" in page.get("source", "").lower()
                        or "resume" in page.get("source", "").lower()
                    )
                )
            
                def extract_cv_section(text, start_heading, end_headings):
                    text_lower = text.lower()
                    start = text_lower.find(start_heading.lower())
            
                    if start == -1:
                        return ""
            
                    start += len(start_heading)
            
                    end_positions = [
                        text_lower.find(heading.lower(), start)
                        for heading in end_headings
                        if text_lower.find(heading.lower(), start) != -1
                    ]
            
                    if end_positions:
                        end = min(end_positions)
                        return text[start:end].strip()
            
                    return text[start:].strip()
            
                cv_lines = [
                    line.strip()
                    for line in cv_full_text.splitlines()
                    if line.strip()
                ]
            
                cv_name = ""

                for line in cv_lines:
                    if (
                        not line.startswith("[DOC ")
                        and not line.lower().startswith("source:")
                        and not line.lower().startswith("page:")
                        and not line.isdigit()
                    ):
                        cv_name = line
                        break
            
                professional_summary = extract_cv_section(
                    cv_full_text,
                    "Professional Summary",
                    [
                        "Professional Experience",
                        "Core Skills",
                        "Certifications & Training",
                        "Languages",
                    ],
                )
            
                professional_experience = extract_cv_section(
                    cv_full_text,
                    "Professional Experience",
                    [
                        "Core Skills",
                        "Certifications & Training",
                        "Languages",
                    ],
                )
            
                core_skills = extract_cv_section(
                    cv_full_text,
                    "Core Skills",
                    [
                        "Certifications & Training",
                        "Languages",
                    ],
                )
            
                certifications_training = extract_cv_section(
                    cv_full_text,
                    "Certifications & Training",
                    [
                        "Languages",
                    ],
                )
            
                languages_page_text = next(
                    (
                        page.get("text", "")
                        for page in document_pages
                        if (
                            (
                                "cv" in page.get("source", "").lower()
                                or "resume" in page.get("source", "").lower()
                            )
                            and "languages" in page.get("text", "").lower()
                        )
                    ),
                    "",
                )
                
                languages = extract_cv_section(
                    languages_page_text,
                    "Languages",
                    [],
                )
            
                direct_answer = f"""
            **{cv_name}**
            
            **Professional Summary**
            {professional_summary}
            
            **Professional Experience**
            {professional_experience}
            
            **Core Skills**
            {core_skills}
            
            **Certifications & Training**
            {certifications_training}
            
            **Languages**
            {languages}
            """.strip()
            cv_doc_number = get_doc_number_for_phrase(cv_name)

            if cv_doc_number and f"[DOC {cv_doc_number}]" not in direct_answer:
                direct_answer += f"\n\n[DOC {cv_doc_number}]"
            else:
                prompt = f"""
        Context:
        {context}
        
        Based only on the context above, answer the following question.
        For CV or resume summaries:
        - Use only facts explicitly stated in the provided CV/resume context.
        - Preserve the person's name, job title, employer, certification status, and training names exactly as stated in the source.
        - Never convert training, preparation, coursework, or exam preparation into an earned certification.
        - Do not infer seniority, expertise level, employer, job title, sectors, responsibilities, or achievements unless explicitly stated.
        - If multiple documents are uploaded, summarize only the CV/resume content relevant to the user's request and do not mix in unrelated document content.
        - Keep the summary concise and factual.
        - Use the person's exact name as written in the CV/resume. Never rewrite, normalize, translate, or guess the name.
        - When mentioning certifications, training, preparation, courses, or badges, preserve the exact status and wording from the source. Do not shorten or upgrade them into an earned certification.
        - Never rewrite "Preparation", "Training", "Course", "Level", or similar learning status as a completed certification unless the source explicitly states it was earned.
        
        Question: {question}
        
        {summary_instruction}
        Do not repeat or rephrase the question.
        Do not write a question.
        If the question specifically asks about professional experience, do not include certifications or languages. For a general CV/resume summary, certifications and training may be included only when explicitly stated in the source.
        
        Answer:
        """
        else:
            subject = question.strip().rstrip("?")
        
            if question_lower.startswith("what is "):
                subject = question[8:].strip().rstrip("?")
            elif "features of the " in question_lower:
                subject = question_lower.split("features of the ", 1)[1].strip().rstrip("?")
            elif " عن " in question:
                subject = question.split(" عن ", 1)[1].strip().rstrip("؟?")
            elif question_lower.startswith("شو هو "):
                subject = question[6:].strip().rstrip("؟?")
            
            elif question_lower.startswith("شو هي "):
                subject = question[6:].strip().rstrip("؟?")
        
            normalized_subject = "".join(
                char.lower() for char in subject
                if char.isalnum()
            )
        
            subject_search_context = "\n".join(
                page.get("text", "")
                for page in document_pages
            )
            
            normalized_context = "".join(
                char.lower()
                for char in subject_search_context
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
        "طيب",
        "طيب شو",
        "وشو",
        "شو كمان",
        "وبعدين",
        "وكمان",
        )
        
        follow_up_references = {
            "it",
            "its",
            "this",
            "that",
            "they",
            "their",
            "them",
        "تبعتو",
        "تبعو",
        "تبعها",
        "تبعهم",
        "هاد",
        "هاي",
        "هيدا",
        "هذي",
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
        Question:- 
        {question}
        Follow-up question detected: {is_follow_up}
        If Follow-up question detected is False, treat the current question as a new topic and do not carry over entities or assumptions from previous conversation turns.
        If it is True, use the recent conversation only to resolve references such as it, its, this, that, or omitted product names.
        Combined context:
        {context}
        
        Subject detected in document: {subject_found}
        Answer using only the information provided in the context above.
        Language rules:
        - Answer in the same primary language as the user's question.
        - If the question mixes Arabic and English, answer in clear natural Arabic while preserving technical product names, certification names, acronyms, model numbers, and standard industry terms in English.
        - Do not translate technical names such as AVIXA CTS, Q-SYS, Dante, AES67, HDMI, or model numbers.
        - Avoid literal or awkward Arabic translations; use natural professional Arabic phrasing.
        - For yes/no questions starting with Does, Is, Can, Are, Has, Have, Was, Were, or Will, begin the answer with "Yes" or "No" when the context supports a clear answer, then briefly explain why with citations.
        - When answering in Arabic, use fluent professional Arabic suitable for AV/IT engineers, not literal word-for-word translation.
        - Keep established technical AV/IT terms in English when translating them would sound unnatural or inaccurate, including terms such as Core, I/O, Inputs, Outputs, GPIO, LAN A, LAN B, USB, OLED, firmware, fan speed, connector, port, codec, DSP, Dante, AES67, HDMI, and Q-SYS Designer.
        - Do not translate the product term "Core" as "النواة" when referring to a Q-SYS Core processor. Keep "Core" in English.
        - Prefer natural mixed technical phrasing such as "مداخل ومخارج الصوت (Audio Inputs/Outputs)" instead of awkward hybrid wording.
        - Do not transliterate English technical words into Arabic letters when the standard English term is clearer. For example, use "connector" rather than "كونكتور" and "audio" rather than "أوديو" when needed.
        - Preserve exact model names, standards, interfaces, connector names, and certification names exactly as supported by the context.
        - Avoid awkward machine-translated Arabic, mixed-script words, or non-Arabic characters unless they are part of an official technical name.
        - If a technical term has no clear natural Arabic equivalent, keep it in English and explain it briefly in Arabic if useful.
        - Distinguish network-interface redundancy from full Core/device redundancy.
        - LAN A / LAN B redundancy means redundant network connectivity and must not be confused with full Core processor redundancy.
        - If the context explicitly states "LAN-B - Redundancy", "redundant network", or that one LAN can remain operational when the other LAN is down, answer "Yes" to a question about redundant network connections.
        - Do not use evidence about full Core redundancy, backup Cores, GPIO redundancy, or POTS redundancy to negate a claim specifically about LAN/network-interface redundancy.
        - For yes/no technical questions, prioritize evidence that directly matches the exact feature being asked about over broader statements about the product.
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
        - Any claim about the person's existing certifications, current role, skills, experience, or career focus MUST be supported by a [DOC X] citation from the uploaded document.
        - Use [WEB X] citations only for external facts about certifications, products, requirements, or industry information; do not use web sources alone to support personal-profile claims.
        - Keep personal-profile facts and external certification facts in separate sentences whenever they rely on different source types, so each sentence can carry the correct citation.
        - Do not use a [DOC X] citation to support general facts about a certification, and do not use a [WEB X] citation to support claims about the person's own background, role, skills, or credentials.
        - Never combine a personal-profile claim and an external certification claim in the same sentence. Write them as separate sentences with separate citations.
        - For profile-based certification recommendations, use this structure: first sentence = recommendation only; second sentence = personal evidence with [DOC X]; third sentence = external certification evidence with [WEB X].
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
        - For broad explanation questions, start with a short 1-2 sentence overview, then organize the main points into clear bullet points.
        - Avoid large dense paragraphs when the answer contains multiple capabilities, features, components, or technical concepts.
        - Use short descriptive headings when they improve readability, especially for overview, capabilities, components, use cases, or recommendations.
        - Keep each bullet focused on one idea and avoid repeating the same fact in different wording.
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
        # Casual conversation path
        if is_casual_chat:
            casual_history = ""
        
            for message in st.session_state.messages[-7:-1]:
                role = "User" if message["role"] == "user" else "Assistant"
                casual_history += f"{role}: {message['content']}\n"
            conversation_style_instruction = {
                "LEVANTINE": """
            Reply ONLY in natural Levantine/Jordanian-style colloquial Arabic.
            
            Strict rules:
            - Use spoken Levantine Arabic, not Modern Standard Arabic.
            - Do not use Egyptian, Iraqi, Gulf, or Maghrebi expressions.
            - Avoid formal wording and formal sentence structure.
            - Match the user's own wording and rhythm as much as possible.
            - Sound relaxed, spontaneous, and conversational.
            - Prefer everyday Jordanian wording such as "اطلع", "احضر", "اسمع", "خدلك", "روق شوي", "شو رأيك".
            - Avoid formal imperative words such as "اخرج", "استمع", "تواصل", "مارس", "خذ قيلولة" when a natural colloquial alternative exists.
            - For simple casual questions, answer in 1-3 short conversational sentences unless the user asks for detailed advice.
            """,
            
                "EGYPTIAN": """
            Reply ONLY in natural Egyptian colloquial Arabic.
            Do not mix Egyptian Arabic with other Arabic dialects or formal Arabic.
            """,
            
                "IRAQI": """
            Reply ONLY in natural Iraqi colloquial Arabic.
            Do not mix Iraqi Arabic with other Arabic dialects or formal Arabic.
            """,
            
                "GULF": """
            Reply ONLY in natural Gulf colloquial Arabic matching the user's style.
            Do not mix Gulf Arabic with other Arabic dialects or formal Arabic.
            """,
            
                "MAGHREBI": """
            Reply in the user's Maghrebi conversational Arabic style when confidently understood.
            Do not mix it with unrelated Arabic dialects.
            """,
            
                "FORMAL_ARABIC": """
            Reply in clear Modern Standard Arabic because the user is speaking formally.
            """,
            
                "ENGLISH": """
            Reply naturally in English and match the user's conversational tone.
            """,
            
                "OTHER": """
            Reply in simple neutral conversational language.
            For Arabic, avoid strongly regional expressions and avoid stiff formal Arabic.
            """,
            }.get(
                detected_conversation_style,
                "Match the user's natural conversational language and tone."
            )
            casual_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are AV Intelligence Assistant. "
                        "For casual conversation, reply naturally and conversationally. "
                        "Match the user's current language, dialect, tone, and level of formality. "
                        f"The detected conversation style is {detected_conversation_style}. "
                        f"Follow this style guidance: {conversation_style_instruction} "
                        "When the user speaks colloquial Arabic, mirror their dialect naturally without exaggerating it. "
                        "Do not mix unrelated Arabic dialects and do not switch to formal Arabic unless the user is formal. "
                        "Prefer simple everyday wording over translated or textbook-style phrasing. "
                        "Respond directly to what the user actually said. "
                        "For simple casual messages, reply like a real chat: usually 1-3 short sentences, no lists, no headings, and no step-by-step advice unless the user explicitly asks for details. "
                        "Use emojis naturally when they fit the user's tone. "
                        "Use the previous conversation only for context and continuity. "
                        "Do not search documents or the web for normal casual conversation. "
                        "If directly asked whether you are human, answer truthfully that you are an AI assistant."
                    )
                }
            ]
            for message in st.session_state.messages[-7:-1]:
                casual_messages.append({
                    "role": message["role"],
                    "content": message["content"]
                })
            
            casual_messages.append({
                "role": "user",
                "content": question
            })
            try:
                direct_answer = call_conversation_llm(
                    messages=casual_messages,
                    temperature=0.4,
                    preferred_models_override=[
                        "CohereLabs/aya-expanse-32b"
                    ]
                ).strip()
                casual_answer_lines = [
                    line.strip()
                    for line in direct_answer.splitlines()
                    if line.strip()
                ]
                
                casual_needs_compaction = (
                    len(casual_answer_lines) > 4
                    or any(
                        line.startswith(("-", "*", "•"))
                        for line in casual_answer_lines
                    )
                )
            
                if casual_needs_compaction:
                    compact_prompt = f"""
                Rewrite the answer below as a short natural chat reply.
                    
                    ORIGINAL USER MESSAGE:
                    {question}
                    
                    ANSWER:
                    {direct_answer}
                    
                    DETECTED STYLE:
                    {detected_conversation_style}
                    
                    Rules:
                    - Keep the same meaning.
                    - Reply in the same language and dialect as the user.
                    - If detected style is LEVANTINE, write specifically in natural Jordanian/Levantine spoken Arabic.
                    - Do not repeat or restate the user's message.
                    - Avoid formal Arabic such as "يمكن", "استمع", "تواصل", "مارس", or textbook-style phrasing.
                    - Prefer natural Jordanian wording such as "خدلك بريك", "اطلع تمشى شوي", "روق", "احضرلك فيلم", "اشربلك قهوة" when appropriate.
                    - Do not force dialect expressions that do not fit naturally.
                    - Use only 1-3 short conversational sentences.
                    - No lists.
                    - No headings.
                    - No step-by-step advice.
                    - Remove repetition and unnecessary explanation.
                    - Do not add new advice or facts.
                    - Keep emojis only if they fit naturally.
                    - Return only the compact final reply.
                    """
                
                    direct_answer = call_conversation_llm(
                        prompt=compact_prompt,
                        temperature=0.2,
                        preferred_models_override=[
                            "CohereLabs/aya-expanse-32b"
                        ]
                    ).strip()
            except Exception as e:
                direct_answer = f"AI model error: {e}"
            
            if direct_answer is not None:
                answer = direct_answer.strip()
            
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer
                })
            
                st.markdown(
                    """
                    <div style="padding:18px 20px; border-radius:16px; border:1px solid rgba(120,120,120,0.16); background:rgba(255,255,255,0.78); margin-top:14px; margin-bottom:10px;">
                    <div style="font-size:24px; font-weight:750; margin-bottom:8px;">
                    🤖 AI Answer
                    </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
                st.markdown(answer)
            
                # Casual conversation ends here.
                # Never send casual answers through RAG/citation/technical post-processing.
                st.stop()
        else:
            with st.spinner("Analyzing sources and preparing your answer..."):
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

            profile_reference_review_cues = (
                "this person",
                "this profile",
                "this cv",
                "this resume",
            )
            
            profile_recommendation_review_cues = (
                "certification",
                "recommend",
                "recommendation",
                "pursue",
                "career",
                "next certification",
            )
            
            is_profile_recommendation_review = (
                any(
                    cue in question_lower
                    for cue in profile_reference_review_cues
                )
                and any(
                    cue in question_lower
                    for cue in profile_recommendation_review_cues
                )
            )
            
            has_any_citation = (
                "[DOC " in answer
                or "[WEB " in answer
            )
            
            needs_citation_review = (
                bool(uncited_bullets)
                or is_profile_recommendation_review
                or (
                    bool(answer.strip())
                    and not has_any_citation
                )
            )
            
            if needs_citation_review:
                citation_review_prompt = f"""
        Review the answer below using the provided context.
        Citation separation rules:
        - If one sentence mixes a personal-profile claim with an external certification, product, requirement, or industry claim, split it into separate sentences.
        - Personal-profile claims about the person's certifications, role, skills, experience, or career focus must use [DOC X].
        - External facts about certifications, products, requirements, or industry information must use [WEB X] when supported by web context.
        - Never use [DOC X] alone to support a general external certification fact.
        - Never use [WEB X] alone to support a claim about the person's own background.
        - Preserve the original recommendation and meaning; only separate claims and correct their citations.
        - Do not add new facts.
        - The opening recommendation sentence must contain only the recommendation itself and must not include uncited personal-profile facts as a preface.
        - Every sentence that mentions the person's certifications, role, skills, experience, background, or career focus MUST include the appropriate [DOC X] citation, even when that sentence also contains a recommendation.
        
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
                    answer = re.sub(
                        r"^\s*Corrected\s+answer\s*:\s*",
                        "",
                        answer,
                        flags=re.IGNORECASE
                    ).strip()
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
        profile_reference_cues = (
            "this person",
            "this profile",
            "this cv",
            "this resume",
        )
        
        profile_recommendation_cues = (
            "certification",
            "recommend",
            "recommendation",
            "pursue",
            "career",
            "next certification",
        )
        
        is_profile_recommendation_question = (
            any(
                cue in question_lower
                for cue in profile_reference_cues
            )
            and any(
                cue in question_lower
                for cue in profile_recommendation_cues
            )
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
                personal_profile_language = bool(
                    re.search(
                        r"\b("
                        r"existing certifications|"
                        r"current role|"
                        r"current job|"
                        r"professional background|"
                        r"career background|"
                        r"his skills|"
                        r"her skills|"
                        r"their skills|"
                        r"his experience|"
                        r"her experience|"
                        r"their experience|"
                        r"his focus|"
                        r"her focus|"
                        r"their focus|"
                        r"focus on|"
                        r"works as|"
                        r"working as"
                        r")\b",
                        line,
                        re.IGNORECASE
                    )
                )
        
                if (
                    (personal_skill_language or personal_profile_language)
                    and has_web_citation
                    and not has_doc_citation
                ):
                    continue
        
                filtered_lines.append(line)
        
            answer = "\n".join(filtered_lines).strip()
        # Build canonical profile identity from the uploaded CV/resume
        profile_pages = [
            page
            for page in document_pages
            if (
                "professional summary" in page.get("text", "").lower()
                and "professional experience" in page.get("text", "").lower()
            )
        ]
        
        canonical_profile_name = ""
        canonical_profile_title = ""
        profile_document_text = ""
        
        if profile_pages:
            profile_document_text = "\n".join(
                page.get("text", "") for page in profile_pages
            )
        
            profile_lines = [
                line.strip()
                for line in profile_pages[0].get("text", "").splitlines()
                if line.strip()
            ]
        
            if profile_lines:
                canonical_profile_name = profile_lines[0]
        
            if len(profile_lines) > 1:
                canonical_profile_title = profile_lines[1]
            if canonical_profile_name and canonical_profile_title:
                identity_guard_prompt = f"""
            Review the answer below and correct ONLY personal identity details.
            
            CANONICAL NAME:
            {canonical_profile_name}
            
            CANONICAL JOB TITLE:
            {canonical_profile_title}
            
            ANSWER:
            {answer}
            
            Rules:
            - If the answer mentions the person's name, it must match the canonical name exactly.
            - If the answer mentions the person's job title or professional role, it must match the canonical job title exactly.
            - Do not invent or infer any other name, title, employer, or role.
            - Do not add new facts.
            - Do not remove valid citations.
            - Preserve every [DOC X] and [WEB X] citation exactly.
            - Preserve the language of the answer.
            - Return only the corrected answer.
            
            Corrected answer:
            """

            import re
            try:
                answer = call_qwen_llm(identity_guard_prompt)
            except Exception as e:
                st.warning(f"Profile identity correction error: {e}")
            answer = re.sub(
                r"\b(?:Mahmoud|Mohammad|Mohammed|Mustafa)\s+[A-Za-z'-]+\b",
                canonical_profile_name,
                answer
            )
        # Validate that citation labels reference real available sources
               
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
        - Do not upgrade a listed skill, platform, technology, or training item into claims such as trained, specialized, expert or expertise, advanced, designed, created, or implemented unless the cited source explicitly states that level of experience.
        - Do not invent, alter, or infer a person's name, job title, employer, certification status, or professional role. Preserve those details exactly as stated in the cited source.
        - If the source only lists a technology under skills or training, describe it only as a listed skill or training item unless stronger experience is explicitly supported.
        - Do NOT explain that information was missing, unsupported, unavailable, or not found.
        - Do NOT add notes, warnings, explanations, verification comments, or summaries.
        - Keep the verified answer tightly focused on the user's exact question. Remove tangential troubleshooting, causes, restart steps, software/power speculation, or unrelated failure scenarios unless the user explicitly asked for them.
        - For failure or redundancy questions, keep the most direct documented operational consequence and do not add broader failure possibilities unless they are necessary to answer the question.
        - Preserve only supported claims and their correct citations.
        - Every factual claim that remains in the verified answer MUST retain its supporting [DOC X] or [WEB X] citation immediately after that claim.
        - Never return a factual sentence or bullet without its citation when that claim originally had a valid supporting citation.
        - Never invent or guess citation numbers that do not exist in SOURCE CONTENT.
        - If a claim is supported by a different existing [DOC X] or [WEB X] source than the citation currently attached to it, correct the citation to the exact supporting source.
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
        # Deterministic CV summary guard
        is_cv_summary_request = any(
            phrase in question_lower
            for phrase in cv_summary_phrases
        )
        
        if is_cv_summary_request and direct_answer is None:
            cv_text = "\n".join(
                page.get("text", "")
                for page in document_pages
                if (
                    "cv" in page.get("source", "").lower()
                    or "resume" in page.get("source", "").lower()
                )
            )
        
            # Preserve AVIXA CTS Preparation status exactly
            if "avixa cts preparation" in cv_text.lower():
               answer = re.sub(
                    r"(?:AVIXA\s+CTS(?:\s+certification)?(?:\s+in\s+preparation)?|"
                    r"preparation\s+for\s+AVIXA\s+CTS)",
                    "AVIXA CTS Preparation",
                    answer,
                    flags=re.IGNORECASE,
                )
        
        # Detect whether the user asked in Arabic
        user_used_arabic = bool(
            re.search(r"[\u0600-\u06FF]", question)
        )
        user_used_english = (
            bool(re.search(r"[A-Za-z]", question))
            and not user_used_arabic
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
        # If an English question accidentally produced an Arabic answer,
        # translate only the verified answer while preserving facts and citations.
        if (
            user_used_english
            and arabic_chars_in_answer >= 10
        ):
            english_fix_prompt = f"""
        Translate the VERIFIED ANSWER below into natural English.
        
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
        
        English answer:
        """
        
            try:
                answer = call_qwen_llm(english_fix_prompt)
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
        if (
            "certification" in question_lower
            and any(
                cue in question_lower
                for cue in ("should", "recommend", "next", "pursue")
            )
        ):
            is_recommendation_question = True
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
            profile_document_text = "\n".join(
                page.get("text", "")
                for page in document_pages
            )
            
            cts_preparation_present = bool(
                re.search(
                    r"\b(?:AVIXA\s+)?CTS\s+Preparation\b",
                    profile_document_text,
                    re.IGNORECASE
                )
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
            cts_preparation_page = next(
                (
                    page
                    for page in document_pages
                    if re.search(
                        r"\b(?:AVIXA\s+)?CTS\s+Preparation\b",
                        page.get("text", ""),
                        re.IGNORECASE
                    )
                ),
                None
            )
            
            doc_number = None
            
            if cts_preparation_page:
                doc_key = (
                    cts_preparation_page.get("source"),
                    cts_preparation_page.get("page_number")
                )
                doc_number = doc_source_numbers.get(doc_key)
            
            generic_next_certification_question = (
                "certification" in question_lower
                and any(
                    cue in question_lower
                    for cue in ("next", "should", "recommend", "pursue")
                )
                and "cts-i" not in question_lower
                and "cts-d" not in question_lower
            )
            if (
                cts_preparation_present
                and doc_number is not None
                and not active_cts_confirmed
                and not (
                    search_mode == "Documents + Web"
                    and web_results
                )
                and (
                    advanced_cts_recommended
                    or generic_next_certification_question
                )
            ):
                        
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
            
        answer = normalize_model_names(answer)

        if (
            "career focus" in question_lower
            or "professional focus" in question_lower
        ):
            answer = re.sub(
                r"\b(?:strong|extensive|deep|specialized|advanced|expert|highly experienced)\s+experience\b",
                "experience",
                answer,
                flags=re.IGNORECASE
            )
        
            answer = re.sub(
                r"\b(?:is|was)\s+(?:also\s+)?specialized\s+in\b",
                "has experience in",
                answer,
                flags=re.IGNORECASE
            )

        answer = polish_arabic_answer(answer)

        # Keep currency values readable inside Arabic RTL text
        currency_patterns = (
            (r"\bUSD\s+(\d+(?:\.\d+)?)\b", r"`USD \1`"),
            (r"\bEUR\s+(\d+(?:\.\d+)?)\b", r"`EUR \1`"),
            (r"\bGBP\s+(\d+(?:\.\d+)?)\b", r"`GBP \1`"),
            (r"\bAUD\s+(\d+(?:\.\d+)?)\b", r"`AUD \1`"),
        )
        
        for pattern, replacement in currency_patterns:
            answer = re.sub(
                pattern,
                replacement,
                answer,
                flags=re.IGNORECASE
            )
       
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
        
        st.markdown(
        """
        <div style="padding:18px 20px; border-radius:16px; border:1px solid rgba(120,120,120,0.16); background:rgba(255,255,255,0.78); margin-top:14px; margin-bottom:10px;">
        <div style="font-size:24px; font-weight:750; margin-bottom:8px;">
        🤖 AI Answer
        </div>
        </div>
        """,
        unsafe_allow_html=True
        )
        
        st.markdown(answer)
        
        if claim_verification_passed and (final_cited_docs or final_cited_web):
            st.success("✅ Verified against cited sources")
        if final_cited_docs:
            st.markdown(
            """
            <div style="padding:16px 18px; border-radius:14px; border:1px solid rgba(120,120,120,0.14); background:rgba(255,255,255,0.72); margin-top:18px; margin-bottom:10px;">
            <div style="font-size:22px; font-weight:750;">
            📄 Document Sources
            </div>
            <div style="font-size:13px; opacity:0.65; margin-top:4px;">
            Document pages cited in the answer above.
            </div>
            </div>
            """,
            unsafe_allow_html=True
            )
        
            for (source_name, page_number), doc_number in sorted(
                doc_source_numbers.items(),
                key=lambda item: item[1]
            ):
                if doc_number in final_cited_docs:
                    st.write(
                        f"[DOC {doc_number}] {source_name} – Page {page_number}"
                    )
        if search_mode == "Documents + Web" and web_results and final_cited_web:
            st.markdown(
            """
            <div style="padding:16px 18px; border-radius:14px; border:1px solid rgba(120,120,120,0.14); background:rgba(255,255,255,0.72); margin-top:18px; margin-bottom:10px;">
            <div style="font-size:22px; font-weight:750;">
            🌐 Web Sources
            </div>
            <div style="font-size:13px; opacity:0.65; margin-top:4px;">
            Web sources cited in the answer above.
            </div>
            </div>
            """,
            unsafe_allow_html=True
            )
        
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
