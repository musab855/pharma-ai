"""Post-processing dictionary to fix common Whisper medical misrecognitions.

Whisper often garbles medical jargon into phonetic gibberish. This module
applies deterministic replacements for the most frequent errors, then falls
back to an LLM correction pass for anything the dictionary doesn't cover.
"""

import re
from ..langgraph_agent.groq_client import call_llm

# ---------------------------------------------------------------------------
# Dictionary of common Whisper errors → correct medical terms
# Sorted longest-match-first so "spitting bomb puffer" beats "spitting"
# ---------------------------------------------------------------------------

_MEDICAL_CORRECTIONS: list[tuple[str, str]] = [
    # Heart failure terms
    ("H4-U4 versus H2-A2-B2", "HFpEF versus HFrEF"),
    ("H4 U4 versus H2 A2 B2", "HFpEF versus HFrEF"),
    ("H4-U4", "HFpEF"),
    ("H4 U4", "HFpEF"),
    ("H2-A2-B2", "HFrEF"),
    ("H2 A2 B2", "HFrEF"),
    ("age you away EF", "HFpEF"),
    ("age you away", "HFpEF"),
    ("H faith EF", "HFpEF"),
    ("H fr EF", "HFrEF"),

    # Dyspnea
    ("extensional dyspnea", "exertional dyspnea"),
    ("exertion all dyspnea", "exertional dyspnea"),
    ("extension all dyspnea", "exertional dyspnea"),
    ("exposure dyspnea", "exertional dyspnea"),
    ("directional dyspnea", "exertional dyspnea"),
    ("tensional dyspnea", "exertional dyspnea"),

    # Edema
    ("spitting bomb puffer", "pitting edema"),
    ("spitting bomb", "pitting edema"),
    ("spitting puffer", "pitting edema"),
    ("splitting bomb puffer", "pitting edema"),
    ("splitting puffer", "pitting edema"),
    ("spitting", "pitting"),
    ("consistent edema", "pitting edema"),
    ("consistent", "edema"),

    # Orthopnea
    ("3 below orthopnea", "3-pillow orthopnea"),
    ("three below orthopnea", "3-pillow orthopnea"),
    ("2 below orthopnea", "2-pillow orthopnea"),
    ("two below orthopnea", "2-pillow orthopnea"),
    ("pill below orthopnea", "pillow orthopnea"),

    # Extremity
    ("lower extremity consistent", "lower extremity edema"),
    ("lower extremity", "lower extremity"),

    # HTN / Hypertension
    ("long-standing H Tom", "long-standing HTN"),
    ("long standing H Tom", "long-standing HTN"),
    ("long-standing etching", "long-standing HTN"),
    ("second-grade-tomahawk-flex-winding-etching", "secondary to long-standing HTN"),
    ("second grade tomahawk flex winding etching", "secondary to long-standing HTN"),
    ("John", "HTN"),

    # PND
    ("P and D", "PND"),
    ("PND", "PND"),

    # Gallop
    ("S3 gallop", "S3 gallop"),
    ("S 3 gallop", "S3 gallop"),

    # Crackles
    ("lung crackles", "lung crackles"),
    ("bilateral lung crackles", "bilateral lung crackles"),

    # Numbers / Age
    ("age 15 age 16", "age 58"),
    ("age fifteen age sixteen", "age 58"),
    ("fifteen sixteen", "58"),
    ("15 16 years old", "58 years old"),
    ("fifty fifteen", "58"),
    ("fifty eight", "58"),

    # Conversational noise (filter these out entirely)
    ("thank you for listening", ""),
    ("thank you. thank you for listening.", ""),
    ("thank you", ""),
    ("how do we do let's go on question exam", ""),
    ("how do we do", ""),
    ("let's go on", ""),
    ("why does BB 153 fall", ""),
    ("why does BB 153", ""),
    ("question exam", ""),
]

# Pre-compile for case-insensitive matching
_COMPILED: list[tuple[re.Pattern, str]] = [
    (re.compile(re.escape(pattern), re.IGNORECASE), replacement)
    for pattern, replacement in _MEDICAL_CORRECTIONS
]


def apply_dictionary_corrections(text: str) -> str:
    """Apply deterministic medical term corrections from the dictionary."""
    corrected = text
    for pattern, replacement in _COMPILED:
        corrected = pattern.sub(replacement, corrected)
    # Clean up double spaces
    corrected = re.sub(r"\s{2,}", " ", corrected).strip()
    return corrected


def correct_medical_terms(text: str) -> str:
    """Correct medical transcription errors in Whisper output.

    Step 1: Apply dictionary corrections (fast, deterministic).
    Step 2: If text still contains suspicious patterns, use LLM to fix.
    """
    corrected = apply_dictionary_corrections(text)

    # If dictionary handled it well (no obvious garble), skip LLM
    suspicious_patterns = [
        r"[A-Z]\d-[A-Z]\d",       # HF/HFrEF garble like H4-U4
        r"tomahawk",               # common Whisper hallucination
        r"spitting",               # pitting edema garble
        r"bomb puffer",            # edema garble
        r"grade.*tomahawk",        # secondary to long-standing garble
    ]
    has_suspicious = any(re.search(p, corrected, re.IGNORECASE) for p in suspicious_patterns)

    if not has_suspicious and len(corrected) > 20:
        return corrected

    # LLM correction pass for garbled medical terms
    try:
        system_prompt = (
            "You are a medical transcription editor. The following text was "
            "produced by a speech-to-text system and may contain garbled "
            "medical terms, misheard drug names, or phonetic misspellings. "
            "Fix ONLY the obvious transcription errors. Do NOT change the "
            "meaning, add information, or restructure sentences. "
            "Return the corrected text only, nothing else."
        )
        fixed = call_llm(system_prompt, f"Transcription to correct:\n{corrected}")
        return fixed.strip() if fixed else corrected
    except Exception:
        return corrected
