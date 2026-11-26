"""
Offline extractive and thematic summarizer for Whisper transcripts.
Generates chapters, key bullet points, and executive summary without requiring external APIs.
"""

import re
from typing import List, Dict, Any
from collections import Counter

from exporters import seconds_to_hms


# Common stop words for English
STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
    "by", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "from", "up", "down", "in", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when", "where",
    "why", "how", "all", "any", "both", "each", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than",
    "too", "very", "can", "will", "just", "don", "should", "now", "i", "me",
    "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours",
    "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers",
    "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is",
    "are", "was", "were", "be", "been", "being", "have", "has", "had", "having",
    "do", "does", "did", "doing", "would", "could", "like", "know", "going", "think",
    "really", "actually", "yeah", "okay", "right", "well", "um", "uh", "kind", "sort"
}


def clean_words(text: str) -> List[str]:
    """Tokenizes and cleans words for frequency analysis."""
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    return [w for w in words if w not in STOP_WORDS]


def generate_chapters(segments: List[Dict[str, Any]], target_interval_sec: float = 120.0) -> List[Dict[str, Any]]:
    """
    Groups segments into time-based chapters (every ~2 minutes or on major speech pauses).
    """
    if not segments:
        return []

    chapters = []
    current_chapter_start = segments[0]["start"]
    current_texts = []
    last_end = current_chapter_start

    for seg in segments:
        start = seg.get("start", 0.0)
        end = seg.get("end", 0.0)
        text = seg.get("text", "").strip()

        # If pause between segments is large (> 3.5s) or time interval exceeded
        is_long_pause = (start - last_end) > 3.5
        interval_passed = (start - current_chapter_start) >= target_interval_sec

        if (interval_passed or is_long_pause) and current_texts:
            full_chunk = " ".join(current_texts)
            words = clean_words(full_chunk)
            top_words = [w.capitalize() for w, _ in Counter(words).most_common(3)]
            chapter_title = " / ".join(top_words) if top_words else f"Chapter at {seconds_to_hms(current_chapter_start)}"

            chapters.append({
                "start": current_chapter_start,
                "start_formatted": seconds_to_hms(current_chapter_start),
                "title": chapter_title,
                "preview": full_chunk[:140] + ("..." if len(full_chunk) > 140 else "")
            })

            current_chapter_start = start
            current_texts = [text]
        else:
            current_texts.append(text)

        last_end = end

    if current_texts:
        full_chunk = " ".join(current_texts)
        words = clean_words(full_chunk)
        top_words = [w.capitalize() for w, _ in Counter(words).most_common(3)]
        chapter_title = " / ".join(top_words) if top_words else f"Chapter at {seconds_to_hms(current_chapter_start)}"
        chapters.append({
            "start": current_chapter_start,
            "start_formatted": seconds_to_hms(current_chapter_start),
            "title": chapter_title,
            "preview": full_chunk[:140] + ("..." if len(full_chunk) > 140 else "")
        })

    return chapters


def generate_offline_summary(full_text: str, segments: List[Dict[str, Any]]) -> str:
    """
    Extracts high-value sentences and key takeaways from the transcript.
    """
    if not full_text or len(full_text.strip()) < 50:
        return "Audio too short to generate a meaningful summary."

    # Extract sentences
    raw_sentences = re.split(r"(?<=[.!?])\s+", full_text.strip())
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) > 20]

    if not sentences:
        return full_text[:300] + "..."

    # Frequency analysis
    all_words = clean_words(full_text)
    word_freq = Counter(all_words)
    max_freq = max(word_freq.values()) if word_freq else 1

    scored_sentences = []
    for idx, sent in enumerate(sentences):
        words = clean_words(sent)
        if not words:
            continue
        # Base score on word frequency
        score = sum(word_freq.get(w, 0) / max_freq for w in words) / (len(words) ** 0.5)
        # Give slight boost to earlier sentences (introductions) and concluding sentences
        if idx < 3:
            score *= 1.2
        elif idx >= len(sentences) - 2:
            score *= 1.1

        scored_sentences.append((score, idx, sent))

    # Top sentences for executive highlights
    scored_sentences.sort(key=lambda x: x[0], reverse=True)
    top_count = min(5, len(scored_sentences))
    chosen = sorted(scored_sentences[:top_count], key=lambda x: x[1])

    # Key topics
    top_keywords = [w for w, _ in word_freq.most_common(8)]

    # Chapters
    chapters = generate_chapters(segments)

    summary_md = []
    summary_md.append("### 🎯 Executive Highlights")
    for _, _, sent in chosen:
        summary_md.append(f"- {sent}")
    summary_md.append("")

    if top_keywords:
        summary_md.append("### 🔑 Key Topics & Terms")
        summary_md.append(", ".join(f"`{kw}`" for kw in top_keywords))
        summary_md.append("")

    if chapters:
        summary_md.append("### ⏱️ Timestamped Chapters")
        for ch in chapters:
            summary_md.append(f"- **`{ch['start_formatted']}`** {ch['title']}")
        summary_md.append("")

    return "\n".join(summary_md)
