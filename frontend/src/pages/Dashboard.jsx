import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { fetchComplaints } from "../store/complaintsSlice";
import { SeverityBadge, StatusBadge } from "../components/StatusBadge";

export default function Dashboard() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { items, status } = useSelector((s) => s.complaints);

  useEffect(() => {
    dispatch(fetchComplaints());
  }, [dispatch]);

  return (
    <div>
      <div className="page-header">
        <h2>Customer Complaints</h2>
        <button className="btn" onClick={() => navigate("/copilot")}>
          + Log Complaint (AI Copilot)
        </button>
      </div>

      {status === "loading" && <p>Loading...</p>}
      {status === "succeeded" && items.length === 0 && (
        <div className="card">No complaints yet. Create one to get started.</div>
      )}

      {items.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Complaint #</th>
              <th>Product</th>
              <th>Batch</th>
              <th>Severity</th>
              <th>Status</th>
              <th>AI Completeness</th>
              <th>Received</th>
            </tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id} onClick={() => navigate(`/complaints/${c.id}`)}>
                <td>{c.complaint_number}</td>
                <td>{c.product_name || "—"}</td>
                <td>{c.batch_number || "—"}</td>
                <td><SeverityBadge severity={c.severity} /></td>
                <td><StatusBadge status={c.status} /></td>
                <td>{c.ai_completeness_score != null ? `${c.ai_completeness_score}%` : "—"}</td>
                <td>{new Date(c.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
