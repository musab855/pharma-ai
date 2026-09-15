import React from "react";
import { useSelector } from "react-redux";

const SECTIONS = [
  { key: "clinical_summary", title: "Clinical Summary" },
  { key: "chief_complaint", title: "Chief Complaint" },
  { key: "history_of_present_illness", title: "History of Present Illness" },
  { key: "symptoms", title: "Symptoms" },
  { key: "past_medical_history", title: "Past Medical History" },
  { key: "medication_history", title: "Medication History" },
  { key: "clinical_observations", title: "Clinical Observations" },
  { key: "assessment", title: "Assessment" },
  { key: "plan", title: "Plan" },
];

function Section({ title, children }) {
  return (
    <div className="summary-section">
      <div className="summary-section-header">
        <span className="section-title">{title}</span>
      </div>
      <div className="summary-section-body">
        {children || <span className="empty-text">No data extracted yet</span>}
      </div>
    </div>
  );
}

function ListItem({ text }) {
  return <div className="summary-list-item">{text}</div>;
}

function renderValue(val) {
  if (!val) return null;
  if (Array.isArray(val)) {
    return val.map((item, i) => (
      <ListItem key={i} text={typeof item === "string" ? item : JSON.stringify(item)} />
    ));
  }
  if (typeof val === "object") {
    // medication_history has nested structure
    if (val.current_medications || val.allergies) {
      return (
        <>
          {val.current_medications && val.current_medications.length > 0 && (
            <div>
              <strong>Current Medications:</strong>
              {val.current_medications.map((m, i) => (
                <ListItem key={i} text={`${m.name || "Unknown"} — ${m.dosage || "N/A"}${m.adherence ? ` (${m.adherence})` : ""}`} />
              ))}
            </div>
          )}
          {val.allergies && val.allergies.length > 0 && (
            <div>
              <strong>Allergies:</strong>
              {val.allergies.map((a, i) => <ListItem key={i} text={a} />)}
            </div>
          )}
          {(!val.current_medications || val.current_medications.length === 0) &&
           (!val.allergies || val.allergies.length === 0) && null}
        </>
      );
    }
    // symptoms has positives/negatives
    if (val.positives || val.negatives) {
      return (
        <>
          {val.positives && val.positives.length > 0 && (
            <div>
              <strong>Positive:</strong>
              {val.positives.map((s, i) => <ListItem key={i} text={s} />)}
            </div>
          )}
          {val.negatives && val.negatives.length > 0 && (
            <div>
              <strong>Negative (denied):</strong>
              {val.negatives.map((s, i) => <ListItem key={i} text={s} />)}
            </div>
          )}
        </>
      );
    }
    // generic object
    return Object.entries(val).map(([k, v]) => (
      <ListItem key={k} text={`${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`} />
    ));
  }
  return <ListItem text={String(val)} />;
}

export default function ClinicalSummary() {
  const { analysis } = useSelector((s) => s.transcription);
  const data = analysis || {};

  const pd = data.patient_details || {};

  const handleCopy = () => {
    if (!analysis) return;
    const lines = [
      `Patient: ${pd.name || "N/A"}, Age: ${pd.age || "N/A"}, Sex: ${pd.sex || "N/A"}`,
      "",
      `CHIEF COMPLAINT:\n${data.chief_complaint || "N/A"}`,
      "",
      `HISTORY OF PRESENT ILLNESS:\n${data.history_of_present_illness || "N/A"}`,
      "",
      `SYMPTOMS:\n${data.symptoms ? JSON.stringify(data.symptoms, null, 2) : "N/A"}`,
      "",
      `PAST MEDICAL HISTORY:\n${data.past_medical_history || "N/A"}`,
      "",
      `MEDICATION HISTORY:\n${data.medication_history ? JSON.stringify(data.medication_history, null, 2) : "N/A"}`,
      "",
      `CLINICAL OBSERVATIONS:\n${data.clinical_observations || "N/A"}`,
      "",
      `ASSESSMENT:\n${data.assessment || "N/A"}`,
      "",
      `PLAN:\n${data.plan || "N/A"}`,
      "",
      `CLINICAL SUMMARY:\n${data.clinical_summary || "N/A"}`,
    ];
    navigator.clipboard.writeText(lines.join("\n")).then(() => {
      alert("Copied to clipboard!");
    });
  };

  return (
    <div className="transcription-right">
      <div className="card summary-card">
        <div className="card-header">
          <div className="card-title">
            <span className="card-icon">&#x1FA7A;</span> AI Medical Summary
          </div>
        </div>

        <div className="patient-info">
          <div className="patient-row">
            <strong>Patient Name:</strong> {pd.name || "N/A"}
          </div>
          <div className="patient-row">
            Age: {pd.age || "N/A"}&nbsp;&nbsp;Sex: {pd.sex || "N/A"}
          </div>
          {pd.identifiers && (
            <div className="patient-row">ID: {pd.identifiers}</div>
          )}
        </div>

        {SECTIONS.map(({ key, title }) => (
          <Section key={key} title={title}>
            {analysis ? renderValue(data[key]) : null}
          </Section>
        ))}

        <button
          className="btn btn-prescription"
          onClick={handleCopy}
          disabled={!analysis}
        >
          &#x1F4CB; Copy to Prescription
        </button>
      </div>
    </div>
  );
}
