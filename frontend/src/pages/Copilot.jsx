import React, { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import {
  sendCopilotMessage,
  uploadCopilotFile,
  resetCopilot,
  addUserMessage,
  seedMessage,
} from "../store/copilotSlice";
import { getComplaint } from "../api/client";
import { SeverityBadge, StatusBadge } from "../components/StatusBadge";

const SAMPLE =
  "Apollo Pharmacy reported discolored capsules in Amoxicillin capsules 500 mg. " +
  "Batch number AMX240602, manufacturing date March 2026, expiry date Feb 2028. " +
  "Please log this complaint.";

export default function Copilot() {
  const { id } = useParams(); // present when opened from an existing complaint
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const { messages, complaint, status } = useSelector((s) => s.copilot);
  const [input, setInput] = useState("");
  const bottomRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => {
    dispatch(resetCopilot());
    if (id) {
      getComplaint(id).then((data) => {
        dispatch({
          type: "copilot/sendMessage/fulfilled",
          payload: { reply: "", tool_used: "load", complaint: data },
        });
        if (data.copilot_history && data.copilot_history.length) {
          data.copilot_history.forEach((m) => dispatch(seedMessage(m)));
        }
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const currentComplaintId = complaint?.id || id || null;

  const handleSend = (text) => {
    const msg = (text ?? input).trim();
    if (!msg) return;
    dispatch(addUserMessage(msg));
    dispatch(sendCopilotMessage({ complaintId: currentComplaintId, message: msg })).then(
      (action) => {
        const newId = action.payload?.complaint?.id;
        if (newId && !id) navigate(`/copilot/${newId}`, { replace: true });
      }
    );
    setInput("");
  };

  const handleFile = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    dispatch(addUserMessage(`📎 Uploaded: ${file.name}`));
    dispatch(uploadCopilotFile({ complaintId: currentComplaintId, file })).then((action) => {
      const newId = action.payload?.complaint?.id;
      if (newId && !id) navigate(`/copilot/${newId}`, { replace: true });
    });
    e.target.value = "";
  };

  return (
    <div>
      <div className="page-header">
        <h2>AIVOA Copilot</h2>
        {complaint && (
          <div style={{ display: "flex", gap: 8 }}>
            <SeverityBadge severity={complaint.severity} />
            <StatusBadge status={complaint.status} />
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 20 }}>
        {/* LEFT: AI-filled form, read-only — filled only via the copilot */}
        <div className="card">
          <label style={{ marginBottom: 4 }}>
            {complaint ? complaint.complaint_number : "Log Customer Complaint"}
          </label>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 14 }}>
            Fields are populated by the AI Copilot — describe or paste the complaint on the right.
          </div>

          <div className="field-grid">
            <ReadField label="Customer" value={complaint?.customer_name} />
            <ReadField label="Product Name" value={complaint?.product_name} />
            <ReadField label="Batch / Lot Number" value={complaint?.batch_number} />
            <ReadField label="Manufacturing Date" value={complaint?.manufacturing_date} />
            <ReadField label="Expiry Date" value={complaint?.expiry_date} />
            <ReadField label="Complaint Type" value={complaint?.complaint_type} />
          </div>

          <label>Structured Defect Summary</label>
          <div className="ai-readonly">
            {complaint?.ai_summary || "AI will synthesize the complaint into a formal QMS description..."}
          </div>

          {complaint && (
            <>
              <h4 style={{ marginTop: 18, fontSize: 13, color: "var(--primary-dark)" }}>
                RISK ASSESSMENT
              </h4>
              <div className="field-grid">
                <ReadField label="Severity" value={complaint.severity} />
                <ReadField label="Completeness" value={`${complaint.ai_completeness_score ?? "—"}%`} />
              </div>
              <label>Suggested Next Action</label>
              <div className="ai-readonly">{complaint.ai_suggested_action || "—"}</div>
              <label>Initial Risk Assessment</label>
              <div className="ai-readonly">{complaint.ai_risk_notes || "—"}</div>

              {complaint.ai_missing_fields?.length > 0 && (
                <>
                  <label style={{ marginTop: 10 }}>Missing Fields</label>
                  <ul className="missing-list">
                    {complaint.ai_missing_fields.map((m) => (
                      <li key={m.field}>{m.label}</li>
                    ))}
                  </ul>
                </>
              )}
            </>
          )}
        </div>

        {/* RIGHT: Chat copilot */}
        <div className="card" style={{ display: "flex", flexDirection: "column", height: 560 }}>
          <label style={{ marginBottom: 0 }}>AIVOA Copilot</label>
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 10 }}>
            Drop complaint files or paste text below.
          </div>

          <div style={{ flex: 1, overflowY: "auto", marginBottom: 10 }}>
            {messages.length === 0 && (
              <div className="ai-panel">
                Ready to process new complaints. Paste the raw complaint text, or upload a file.
                I'll extract the data and run the initial risk assessment.
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                style={{
                  marginBottom: 10,
                  textAlign: m.role === "user" ? "right" : "left",
                }}
              >
                <div
                  style={{
                    display: "inline-block",
                    maxWidth: "85%",
                    padding: "8px 12px",
                    borderRadius: 10,
                    fontSize: 13.5,
                    background: m.role === "user" ? "var(--primary)" : "#f0f2f8",
                    color: m.role === "user" ? "white" : "var(--text)",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {m.content}
                  {m.tool_used && m.tool_used !== "chat" && m.tool_used !== "load" && (
                    <div style={{ fontSize: 10, opacity: 0.7, marginTop: 4 }}>
                      via {m.tool_used.replace(/_/g, " ")}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {status === "loading" && (
              <div style={{ fontSize: 13, color: "var(--text-muted)" }}>AI Copilot is thinking…</div>
            )}
            <div ref={bottomRef} />
          </div>

          <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <button className="btn secondary" onClick={() => handleSend(SAMPLE)}>
              Try Sample Complaint
            </button>
            <button className="btn secondary" onClick={() => fileInputRef.current.click()}>
              📎 Upload Document
            </button>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: "none" }}
              onChange={handleFile}
            />
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <input
              style={{ marginBottom: 0 }}
              placeholder="Type a message or paste a complaint..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <button className="btn" onClick={() => handleSend()}>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ReadField({ label, value }) {
  return (
    <div>
      <label>{label}</label>
      <div className="ai-readonly small">{value || "Awaiting AI extraction..."}</div>
    </div>
  );
}
