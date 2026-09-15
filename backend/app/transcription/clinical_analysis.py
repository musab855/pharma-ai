"""LLM-based clinical analysis of a consultation transcript.

Extracts structured medical information and generates a concise clinical
summary suitable for a medical record.
"""

import json
import re
from ..langgraph_agent.groq_client import call_llm_json, call_llm

SYSTEM_PROMPT = (
    "You are a medical scribe AI. Given a raw consultation transcript between "
    "a clinician and a patient, extract structured medical information. "
    "Respond with ONLY a valid JSON object with EXACTLY these keys:\n\n"
    "1. patient_details: object with keys name, age, sex, identifiers (use null for any not mentioned)\n"
    "   IMPORTANT: If the patient age seems implausible for the stated conditions (e.g., age 15 with heart failure, "
    "diabetes, or hypertension — which are adult-onset conditions), add a note: 'age may be transcription error — verify with patient'.\n"
    "2. chief_complaint: string — the primary reason for the visit in the patient's own terms\n"
    "3. history_of_present_illness: string — onset, duration, progression, aggravating and relieving factors\n"
    "4. symptoms: object with keys positives (array of strings) and negatives (array of strings — things explicitly denied)\n"
    "5. past_medical_history: string — prior conditions, surgeries, hospitalisations\n"
    "6. medication_history: object with keys current_medications (array of {name, dosage, adherence}), allergies (array of strings)\n"
    "7. clinical_observations: string — vitals and examination findings stated aloud\n"
    "8. assessment: string — provisional diagnosis or differentials as stated by the clinician\n"
    "9. plan: string — investigations ordered, prescriptions, advice, follow-up\n"
    "10. clinical_summary: string — 2-3 sentence concise summary for the medical record\n\n"
    "Use null for any field not mentioned. Do not invent data. "
    "Keep the patient's own terms for the chief complaint."
)

USER_TEMPLATE = """
Transcript:
---
{transcript}
---
"""


def analyze_transcript(transcript: str) -> dict:
    """Send the full transcript to the LLM and return structured clinical data."""
    user_prompt = USER_TEMPLATE.format(transcript=transcript)
    try:
        result = call_llm_json(SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        result = {
            "error": f"LLM analysis failed: {e}",
            "clinical_summary": "Analysis unavailable due to an error.",
        }
    return result
