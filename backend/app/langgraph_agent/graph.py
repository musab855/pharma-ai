from langgraph.graph import StateGraph, START, END
from .state import CopilotState
from .nodes import (
    classify_intent, extract_fields, apply_edit,
    completeness_check, risk_assessment, summarize, compose_reply,
)


def _route_after_classify(state: CopilotState) -> str:
    intent = state.get("intent")
    if intent == "log_new":
        return "extract_fields"
    if intent == "edit_existing":
        return "apply_edit"
    return "compose_reply"


def build_graph():
    graph = StateGraph(CopilotState)

    graph.add_node("classify_intent", classify_intent)
    graph.add_node("extract_fields", extract_fields)       # Log Complaint tool
    graph.add_node("apply_edit", apply_edit)                # Edit Complaint tool
    graph.add_node("completeness_check", completeness_check)
    graph.add_node("risk_assessment", risk_assessment)
    graph.add_node("summarize", summarize)
    graph.add_node("compose_reply", compose_reply)

    graph.add_edge(START, "classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        _route_after_classify,
        {
            "extract_fields": "extract_fields",
            "apply_edit": "apply_edit",
            "compose_reply": "compose_reply",
        },
    )

    # Log Complaint tool path
    graph.add_edge("extract_fields", "completeness_check")
    graph.add_edge("completeness_check", "risk_assessment")
    graph.add_edge("risk_assessment", "summarize")
    graph.add_edge("summarize", "compose_reply")

    # Edit Complaint tool path (re-run risk + summary on the merged fields)
    graph.add_edge("apply_edit", "risk_assessment")

    graph.add_edge("compose_reply", END)

    return graph.compile()


copilot_graph = build_graph()


def run_copilot(message: str, existing_fields: dict | None, is_new: bool) -> dict:
    initial_state: CopilotState = {
        "message": message,
        "existing_fields": existing_fields or {},
        "is_new": is_new,
    }
    return copilot_graph.invoke(initial_state)
