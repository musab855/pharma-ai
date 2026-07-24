from .state import CopilotState
from .groq_client import call_llm_json, call_llm

# Mandatory fields for a pharma QMS customer complaint intake (21 CFR 211.198 /
# ICH Q10 aligned): who, what product/batch, when, and what happened.
MANDATORY_FIELDS = [
    ("customer_name", "Customer / complainant name"),
    ("product_name", "Product name"),
    ("batch_number", "Batch / lot number"),
    ("manufacturing_date", "Manufacturing date"),
    ("expiry_date", "Expiry date"),
    ("complaint_description", "Description of the complaint / defect observed"),
    ("complaint_type", "Complaint category (quality, packaging, efficacy, adverse event, etc.)"),
]

EMPTY_VALUES = ("", "null", "none", "n/a", "unknown")


def _is_empty(value):
    return not value or (isinstance(value, str) and value.strip().lower() in EMPTY_VALUES)


def classify_intent(state: CopilotState) -> CopilotState:
    if state.get("is_new"):
        state["intent"] = "log_new"
        return state

    system = (
        "You classify a user message sent to a pharmaceutical QMS complaint copilot. "
        "The copilot is already looking at an existing logged complaint. "
        "Respond with ONLY one of these words: EDIT or CHAT. "
        "EDIT = the user wants to change/correct/update a field's value (e.g. batch number, "
        "quantity, product name, severity, dates, description). "
        "CHAT = the user is asking a question or making general conversation, not changing data."
    )
    try:
        result = call_llm(system, state["message"]).strip().upper()
    except Exception:
        result = "EDIT"
    state["intent"] = "edit_existing" if "EDIT" in result else "general_chat"
    return state


def extract_fields(state: CopilotState) -> CopilotState:
    """Log Complaint tool: extract structured fields from freeform user text / pasted document."""
    system = (
        "You are a pharmaceutical QMS data extraction assistant. Extract structured "
        "fields from a raw customer complaint message (typed, emailed, or pasted from a document). "
        "Respond with ONLY a valid JSON object, no prose, no markdown fences. "
        "Use null for any field you cannot find. Do not invent data."
    )
    user = f"""
Extract these fields from the message below as JSON with EXACTLY these keys:
customer_name, product_name, batch_number, manufacturing_date, expiry_date,
complaint_description, complaint_type, suggested_severity (one of: Critical, Major, Minor).

Message:
---
{state['message']}
---
"""
    try:
        data = call_llm_json(system, user)
    except Exception as e:
        data = {"error": str(e)}

    for key in ["customer_name", "product_name", "batch_number", "manufacturing_date",
                "expiry_date", "complaint_description", "complaint_type"]:
        state[key] = data.get(key)
    state["severity"] = data.get("suggested_severity") or "Unclassified"
    state["extraction_raw"] = data
    state["tool_used"] = "log_complaint_tool"
    return state


def apply_edit(state: CopilotState) -> CopilotState:
    """Edit Complaint tool: given the existing field values + a natural-language instruction,
    figure out which fields change and to what, then merge onto existing_fields."""
    existing = state.get("existing_fields", {})
    editable_keys = ["customer_name", "product_name", "batch_number", "manufacturing_date",
                      "expiry_date", "complaint_description", "complaint_type", "severity"]

    system = (
        "You are a pharmaceutical QMS copilot editing an already-logged complaint. "
        "Given the CURRENT field values and a user instruction, decide which fields "
        "should change and their NEW values. Respond with ONLY a valid JSON object whose keys "
        "are a subset of the editable field names below — include ONLY fields that should change. "
        "Do not include fields the user didn't ask to change. severity must be one of: "
        "Critical, Major, Minor, Unclassified."
    )
    user = f"""
Editable fields: {editable_keys}

Current values:
{ {k: existing.get(k) for k in editable_keys} }

User instruction:
---
{state['message']}
---
"""
    try:
        diff = call_llm_json(system, user)
    except Exception:
        diff = {}

    merged = {k: existing.get(k) for k in editable_keys}
    changed = []
    for k, v in diff.items():
        if k in editable_keys and v is not None and v != merged.get(k):
            merged[k] = v
            changed.append(k)

    for k in editable_keys:
        state[k] = merged[k]
    state["edited_field_names"] = changed
    state["tool_used"] = "edit_complaint_tool"
    return state


def completeness_check(state: CopilotState) -> CopilotState:
    missing = []
    present_count = 0
    for key, label in MANDATORY_FIELDS:
        if _is_empty(state.get(key)):
            missing.append({"field": key, "label": label})
        else:
            present_count += 1
    state["missing_fields"] = missing
    state["completeness_score"] = round((present_count / len(MANDATORY_FIELDS)) * 100, 1)
    return state


def risk_assessment(state: CopilotState) -> CopilotState:
    """Populates the copilot risk-assessment section: severity, suggested next action,
    and a short justification (initial risk assessment)."""
    system = (
        "You are a pharmaceutical QMS risk assessor. Given complaint details, respond with "
        "ONLY a JSON object with keys: severity (Critical, Major, or Minor), "
        "suggested_action (one short actionable sentence, e.g. what the Quality team should do "
        "next — retain sample review, batch recall evaluation, customer follow-up, etc.), and "
        "risk_notes (2-3 sentences justifying the severity: patient safety impact, "
        "batch-wide vs isolated unit, GMP implications)."
    )
    user = f"""
Product: {state.get('product_name')}
Batch: {state.get('batch_number')}
Complaint type: {state.get('complaint_type')}
Description: {state.get('complaint_description')}
"""
    try:
        data = call_llm_json(system, user)
        state["severity"] = data.get("severity") or state.get("severity") or "Unclassified"
        state["suggested_action"] = data.get("suggested_action", "")
        state["risk_notes"] = data.get("risk_notes", "")
    except Exception as e:
        state.setdefault("severity", "Unclassified")
        state["suggested_action"] = "Manual review required — automated risk assessment unavailable."
        state["risk_notes"] = f"(AI risk assessment unavailable: {e})"
    return state


def summarize(state: CopilotState) -> CopilotState:
    """Structured Defect Summary — concise synthesis of the complaint for the QMS record."""
    system = (
        "You are a pharmaceutical QMS complaint reviewer. Write a concise, factual "
        "2-3 sentence 'Structured Defect Summary' for the official complaint record. "
        "Mention product, batch (if known), and the defect observed. Plain prose, no markdown."
    )
    user = f"""
Product: {state.get('product_name')}, Batch: {state.get('batch_number')},
Type: {state.get('complaint_type')}, Severity: {state.get('severity')}
Description: {state.get('complaint_description') or state.get('message')}
"""
    try:
        state["summary"] = call_llm(system, user).strip()
    except Exception as e:
        state["summary"] = f"(AI summary unavailable: {e})"
    return state


def compose_reply(state: CopilotState) -> CopilotState:
    intent = state.get("intent")
    if intent == "log_new":
        missing = state.get("missing_fields", [])
        missing_str = ", ".join(m["label"] for m in missing) if missing else "none"
        state["reply"] = (
            f"Logged the complaint for **{state.get('product_name') or 'the product'}** "
            f"(batch {state.get('batch_number') or 'unknown'}). "
            f"Completeness: {state.get('completeness_score')}% — missing: {missing_str}. "
            f"Severity assessed as **{state.get('severity')}**. "
            f"Suggested next action: {state.get('suggested_action')}"
        )
    elif intent == "edit_existing":
        changed = state.get("edited_field_names", [])
        if changed:
            state["reply"] = (
                f"Updated {', '.join(changed)}. Re-ran the risk assessment — "
                f"severity is now **{state.get('severity')}**. "
                f"Suggested next action: {state.get('suggested_action')}"
            )
        else:
            state["reply"] = "I didn't find a clear field change in that message — could you specify which field and new value?"
    else:
        try:
            state["reply"] = call_llm(
                "You are AIVOA Copilot, a pharmaceutical QMS complaint assistant. Answer briefly and helpfully.",
                state["message"],
            ).strip()
        except Exception as e:
            state["reply"] = f"(assistant unavailable: {e})"
        state["tool_used"] = "chat"
    return state
