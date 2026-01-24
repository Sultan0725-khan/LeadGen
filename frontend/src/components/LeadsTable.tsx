import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { Lead } from "../api/client";
import "./LeadsTable.css";

interface LeadsTableProps {
  runId: string;
  onClose: () => void;
}

export function LeadsTable({ runId, onClose }: LeadsTableProps) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    loadLeads();
  }, [runId]);

  const loadLeads = async () => {
    try {
      const data = await api.getLeads(runId);
      setLeads(data.leads);
      setTotal(data.total);
    } catch (err) {
      console.error("Failed to load leads:", err);
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "score-high";
    if (score >= 0.5) return "score-medium";
    return "score-low";
  };

  const handleExport = () => {
    window.open(api.exportCSV(runId), "_blank");
  };

  if (loading) {
    return (
      <div
        className="card"
        style={{ display: "flex", justifyContent: "center", padding: "3rem" }}
      >
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="card leads-table">
      <div className="leads-header">
        <h2 className="text-gradient">Leads ({total})</h2>
        <div className="leads-actions">
          <button className="btn btn-outline" onClick={handleExport}>
            Export CSV
          </button>
          <button className="btn" onClick={onClose}>
            Back to Runs
          </button>
        </div>
      </div>

      {leads.length === 0 ? (
        <p className="empty-state">No leads found for this run.</p>
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Business Name</th>
                <th>Address</th>
                <th>Contact</th>
                <th>Score</th>
                <th>Sources</th>
                <th>Email Status</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead) => (
                <tr key={lead.id}>
                  <td>
                    <div className="business-name">{lead.business_name}</div>
                    {lead.website && (
                      <a
                        href={lead.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="website-link"
                      >
                        {lead.website}
                      </a>
                    )}
                  </td>
                  <td>{lead.address || "—"}</td>
                  <td>
                    {lead.email && (
                      <div className="contact-item">📧 {lead.email}</div>
                    )}
                    {lead.phone && (
                      <div className="contact-item">📞 {lead.phone}</div>
                    )}
                    {!lead.email && !lead.phone && "—"}
                  </td>
                  <td>
                    <span
                      className={`score-badge ${getScoreColor(lead.confidence_score)}`}
                    >
                      {(lead.confidence_score * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td>
                    <div className="sources">
                      {lead.sources.map((source, idx) => (
                        <span key={idx} className="source-tag">
                          {source}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td>
                    {lead.email_status ? (
                      <span
                        className={`badge badge-${
                          lead.email_status === "sent"
                            ? "success"
                            : lead.email_status === "failed"
                              ? "error"
                              : lead.email_status === "pending_approval"
                                ? "warning"
                                : "info"
                        }`}
                      >
                        {lead.email_status.replace("_", " ")}
                      </span>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
