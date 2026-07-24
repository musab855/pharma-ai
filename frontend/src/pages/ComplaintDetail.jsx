import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { fetchComplaint, changeStatus, editFields } from "../store/complaintsSlice";
import { SeverityBadge, StatusBadge } from "../components/StatusBadge";

const TRANSITIONS = {
  New: ["Under Review", "Rejected"],
  "Under Review": ["Investigation", "Rejected"],
  Investigation: ["CAPA", "Closed"],
  CAPA: ["Closed"],
  Closed: [],
  Rejected: [],
};

export default function ComplaintDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const complaint = useSelector((s) => s.complaints.current);
  const [investigation, setInvestigation] = useState({ root_cause: "", capa_notes: "" });
  const [editingInvestigation, setEditingInvestigation] = useState(false);

  useEffect(() => {
    dispatch(fetchComplaint(id));
  }, [dispatch, id]);

  useEffect(() => {
    if (complaint) {
      setInvestigation({
        root_cause: complaint.root_cause || "",
        capa_notes: complaint.capa_notes || "",
      });
    }
  }, [complaint]);

  if (!complaint) return <p>Loading...</p>;

  const saveInvestigation = () => {
    dispatch(editFields({ id, fields: investigation }));
    setEditingInvestigation(false);
  };

  const nextStatuses = TRANSITIONS[complaint.status] || [];

  return (
    <div>
      <div className="page-header">
        <h2>{complaint.complaint_number}</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <SeverityBadge severity={complaint.severity} />
          <StatusBadge status={complaint.status} />
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20 }}>
        <div>
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <label style={{ marginBottom: 0 }}>Complaint Details (logged by AI Copilot)</label>
              <button className="btn secondary" onClick={() => navigate(`/copilot/${id}`)}>
                Edit via AI Copilot
              </button>
            </div>

            <div className="field-grid">
              <ReadOnly label="Customer" value={complaint.customer_name} />
              <ReadOnly label="Product Name" value={complaint.product_name} />
              <ReadOnly label="Batch Number" value={complaint.batch_number} />
              <ReadOnly label="Manufacturing Date" value={complaint.manufacturing_date} />
              <ReadOnly label="Expiry Date" value={complaint.expiry_date} />
              <ReadOnly label="Complaint Type" value={complaint.complaint_type} />
            </div>

            <label>Structured Defect Summary</label>
            <div className="ai-readonly">{complaint.ai_summary || "—"}</div>

            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8 }}>
              <label style={{ marginBottom: 0 }}>Investigation (Root Cause &amp; CAPA)</label>
              {!editingInvestigation ? (
                <button className="btn secondary" onClick={() => setEditingInvestigation(true)}>
                  Edit
                </button>
              ) : (
                <button className="btn" onClick={saveInvestigation}>
                  Save
                </button>
              )}
            </div>

            <label>Root Cause</label>
            <textarea
              rows={3}
              value={investigation.root_cause}
              disabled={!editingInvestigation}
              onChange={(e) => setInvestigation({ ...investigation, root_cause: e.target.value })}
            />

            <label>CAPA Notes</label>
            <textarea
              rows={3}
              value={investigation.capa_notes}
              disabled={!editingInvestigation}
              onChange={(e) => setInvestigation({ ...investigation, capa_notes: e.target.value })}
            />
          </div>

          <div className="card">
            <label>Original Raw Complaint Text</label>
            <div style={{ fontSize: 13, color: "var(--text-muted)", whiteSpace: "pre-wrap" }}>
              {complaint.raw_text}
            </div>
          </div>

          <div className="card">
            <label>Workflow</label>
            <div className="status-actions">
              {nextStatuses.length === 0 && <span>No further transitions.</span>}
              {nextStatuses.map((s) => (
                <button
                  key={s}
                  className="btn secondary"
                  onClick={() => dispatch(changeStatus({ id, status: s }))}
                >
                  Move to {s}
                </button>
              ))}
            </div>
          </div>

          <div className="card">
            <label>History</label>
            {complaint.history.map((h, i) => (
              <div className="history-item" key={i}>
                <strong>{h.action}</strong>
                {h.note ? ` — ${h.note}` : ""}
                <div style={{ color: "var(--text-muted)", fontSize: 12 }}>
                  {new Date(h.timestamp).toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="ai-panel">
            <h4>AI Risk Assessment</h4>
            <div style={{ fontSize: 13, marginBottom: 10 }}>
              <strong>{complaint.ai_completeness_score ?? 0}%</strong> of mandatory intake fields captured
            </div>
            <label>Suggested Next Action</label>
            <div className="ai-readonly small" style={{ marginBottom: 10 }}>
              {complaint.ai_suggested_action || "—"}
            </div>
            <label>Initial Risk Assessment</label>
            <div className="ai-readonly small">{complaint.ai_risk_notes || "—"}</div>

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
          </div>
        </div>
      </div>
    </div>
  );
}

function ReadOnly({ label, value }) {
  return (
    <div>
      <label>{label}</label>
      <div className="ai-readonly small">{value || "—"}</div>
    </div>
  );
}
