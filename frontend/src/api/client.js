import axios from "axios";

const API_BASE = process.env.REACT_APP_API_BASE || "http://localhost:8000";

const client = axios.create({ baseURL: API_BASE });

export const createComplaint = (raw_text, source_channel = "Manual") =>
  client.post("/api/complaints/", { raw_text, source_channel }).then((r) => r.data);

export const listComplaints = () =>
  client.get("/api/complaints/").then((r) => r.data);

export const getComplaint = (id) =>
  client.get(`/api/complaints/${id}`).then((r) => r.data);

export const updateStatus = (id, status, note) =>
  client.patch(`/api/complaints/${id}/status`, { status, note }).then((r) => r.data);

export const updateFields = (id, fields) =>
  client.patch(`/api/complaints/${id}/fields`, fields).then((r) => r.data);

export const rerunAi = (id) =>
  client.post(`/api/complaints/${id}/rerun-ai`).then((r) => r.data);

export default client;
