"""
GLN Quiz Bot - Question Normalization, SHA-256 Hashing & Semantic Duplicate Detection
Enforces the strict unique question rule:
- Normalizes Hindi unicode (NFKC), removes accents/nuktas variations, lowercases, removes punctuation & extra spaces.
- Generates SHA-256 hash for database and session-level uniqueness checks.
- Detects semantic duplicates (rephrased questions like 'What is the capital of India?' vs 'India's capital is?').
"""

import re
import hashlib
import unicodedata
import difflib
from typing import Set, List, Optional

# High-frequency grammatical Hindi and English stopwords for competitive quiz questions
HINDI_STOPWORDS = {
    "का", "के", "की", "में", "पर", "से", "को", "ने", "है", "हैं", "था", "थी", "थे",
    "होता", "होती", "होते", "गया", "गई", "गए", "द्वारा", "रूप", "नाम", "कहा",
    "जाता", "जाती", "जाते", "किया", "किए", "और", "या", "तथा", "एवं", "जो",
    "वह", "यह", "ये", "वे", "निम्न", "निम्नलिखित", "इनमें", "कौन", "क्या",
    "किस", "किसे", "किसका", "किसकी", "किसके", "कहाँ", "कब", "कैसे", "क्यों",
    "कितना", "कितने", "कितनी", "कौनसा", "कौनसी", "कौनसे", "सही", "विकल्प",
    "कथन", "बताइए", "हैं?", "है?", "था?", "थी?", "थे?",
    "is", "the", "what", "which", "are", "in", "of", "to", "for", "a", "an", "capital"
}

def normalize_question_text(text: str) -> str:
    """
    Normalizes Hindi/English text:
    - NFKC Unicode standard normalization (standardizes Devanagari matras, conjuncts, nuktas)
    - Lowercase
    - Strip punctuation including Hindi purna viram (।), deergh viram (॥), commas, question marks, brackets
    - Collapse repeated whitespace and trim
    """
    if not text:
        return ""

    # 1. Normalize Unicode (NFKC handles Devanagari conjuncts & ligatures uniformly)
    norm = unicodedata.normalize("NFKC", str(text))

    # 2. Lowercase
    norm = norm.lower()

    # 3. Remove punctuation and special symbols
    norm = re.sub(r'[\?؟!।,॥\.\'\"“”‘’`\(\)\[\]\{\}:;\-_/\\*&^%$#@~+=<>|]', ' ', norm)

    # 4. Collapse multiple whitespaces and trim edges
    norm = re.sub(r'\s+', ' ', norm).strip()

    return norm

def generate_question_hash(question_text: str) -> str:
    """
    Generates SHA-256 hash of the normalized question text.
    """
    normalized = normalize_question_text(question_text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

def extract_content_keywords(normalized_text: str) -> Set[str]:
    """
    Extracts significant content words, excluding grammatical stop words.
    """
    tokens = normalized_text.split()
    return {w for w in tokens if w not in HINDI_STOPWORDS and len(w) > 1}

def is_semantically_similar(text_a: str, text_b: str, threshold: float = 0.75) -> bool:
    """
    Detects if two questions are identical or semantically equivalent (near-duplicates).
    Catches variations such as:
    - 'What is the capital of India?' vs "India's capital is?"
    - 'भारत की राजधानी क्या है?' vs 'भारत की राजधानी कौन-सी है?'
    - 'हड़प्पा सभ्यता की खोज किस वर्ष हुई थी?' vs 'हड़प्पा की खोज कब हुई?'
    """
    norm_a = normalize_question_text(text_a)
    norm_b = normalize_question_text(text_b)

    if not norm_a or not norm_b:
        return False

    # Exact normalized match
    if norm_a == norm_b:
        return True

    # Check numerical tokens: if both have numbers and the numbers differ, they are distinct questions
    nums_a = re.findall(r'\d+', norm_a)
    nums_b = re.findall(r'\d+', norm_b)
    if nums_a and nums_b and nums_a != nums_b:
        return False

    # Character sequence ratio
    seq_ratio = difflib.SequenceMatcher(None, norm_a, norm_b).ratio()
    if seq_ratio >= 0.85:
        return True

    # Keyword overlap & Jaccard similarity
    words_a = extract_content_keywords(norm_a)
    words_b = extract_content_keywords(norm_b)

    if words_a and words_b:
        intersection = words_a & words_b
        union = words_a | words_b
        jaccard = len(intersection) / len(union) if union else 0.0

        min_len = min(len(words_a), len(words_b))
        subset_ratio = len(intersection) / min_len if min_len > 0 else 0.0

        # If keyword Jaccard is high, or significant content words overlap >= 80% with sequence similarity
        if jaccard >= threshold:
            return True
        if len(intersection) >= 2 and subset_ratio >= 0.80 and seq_ratio >= 0.60:
            return True

    return False

def check_semantic_duplicate(candidate_text: str, existing_texts: List[str], threshold: float = 0.75) -> Optional[str]:
    """
    Checks if candidate_text is semantically duplicate with any existing text.
    Returns the matching existing text if duplicate, else None.
    """
    for ex in existing_texts:
        if is_semantically_similar(candidate_text, ex, threshold=threshold):
            return ex
    return None
