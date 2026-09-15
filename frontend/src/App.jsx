import React from "react";
import { Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Copilot from "./pages/Copilot";
import ComplaintDetail from "./pages/ComplaintDetail";
import Transcription from "./pages/Transcription";

export default function App() {
  return (
    <div className="app-shell">
      <div className="sidebar">
        <h1>PharmaComplaint AI</h1>
        <div className="subtitle">Complaint Management</div>
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          Dashboard
        </NavLink>
        <NavLink to="/copilot" className={({ isActive }) => (isActive ? "active" : "")}>
          Log Complaint (AI Copilot)
        </NavLink>
        <NavLink to="/transcription" className={({ isActive }) => (isActive ? "active" : "")}>
          Live Transcription
        </NavLink>
      </div>
      <div className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/copilot" element={<Copilot />} />
          <Route path="/copilot/:id" element={<Copilot />} />
          <Route path="/complaints/:id" element={<ComplaintDetail />} />
          <Route path="/transcription" element={<Transcription />} />
        </Routes>
      </div>
    </div>
  );
}
