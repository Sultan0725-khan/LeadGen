import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { Lead } from "../api/client";
import { EmailDraftModal } from "./EmailDraftModal";
import "./LeadsTable.css";

interface LeadsTableProps {
  runId: string;
  onClose: () => void;
}

interface LeadEditModalProps {
  lead: Lead;
  onSave: (id: string, updates: Partial<Lead>) => Promise<void>;
  onClose: () => void;
}

function LeadEditModal({ lead, onSave, onClose }: LeadEditModalProps) {
  const [formData, setFormData] = useState({
    business_name: lead.business_name,
    email: lead.email || "",
    phone: lead.phone || "",
    website: lead.website || "",
    address: lead.address || "",
    notes: lead.notes || "",
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(lead.id, formData);
      onClose();
    } catch (error) {
      console.error("Failed to save lead:", error);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content card" style={{ maxWidth: "500px" }}>
        <h3>Edit Lead</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Business Name</label>
            <input
              type="text"
              value={formData.business_name}
              onChange={(e) =>
                setFormData({ ...formData, business_name: e.target.value })
              }
            />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) =>
                setFormData({ ...formData, email: e.target.value })
              }
            />
          </div>
          <div className="form-group">
            <label>Phone</label>
            <input
              type="text"
              value={formData.phone}
              onChange={(e) =>
                setFormData({ ...formData, phone: e.target.value })
              }
            />
          </div>
          <div className="form-group">
            <label>Website</label>
            <input
              type="text"
              value={formData.website}
              onChange={(e) =>
                setFormData({ ...formData, website: e.target.value })
              }
            />
          </div>
          <div className="form-group">
            <label>Address</label>
            <textarea
              value={formData.address}
              onChange={(e) =>
                setFormData({ ...formData, address: e.target.value })
              }
            />
          </div>
          <div className="form-group">
            <label>Notes</label>
            <textarea
              placeholder="Add personal notes here..."
              value={formData.notes}
              onChange={(e) =>
                setFormData({ ...formData, notes: e.target.value })
              }
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function LeadsTable({ runId, onClose }: LeadsTableProps) {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [drafting, setDrafting] = useState(false);
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [run, setRun] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"new" | "drafted">("new");
  const [filterHasEmail, setFilterHasEmail] = useState<boolean | null>(null);
  const [filterHasWebsite, setFilterHasWebsite] = useState<boolean | null>(
    null,
  );
  const [draftLanguage, setDraftLanguage] = useState<"EN" | "DE">("DE");
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const perPage = 100;

  const loadLeads = useCallback(async () => {
    try {
      setLoading(true);
      // Fetch leads with specific filters based on dashboard/tab state
      const filters = {
        has_email: filterHasEmail ?? undefined,
        has_website: filterHasWebsite ?? undefined,
        email_status: activeTab === "new" ? "new" : "drafted",
      };

      const data = await api.getLeads(runId, page, perPage, filters);

      setLeads(data.leads);
      setTotalCount(data.total);

      // Load run stats
      const runData = await api.getRun(runId);
      setRun(runData);
    } catch (err) {
      console.error("Failed to load leads:", err);
    } finally {
      setLoading(false);
    }
  }, [runId, activeTab, filterHasEmail, filterHasWebsite, page]);

  // Reset page when switching tabs or filters
  useEffect(() => {
    setPage(1);
  }, [activeTab, filterHasEmail, filterHasWebsite]);

  useEffect(() => {
    loadLeads();
  }, [loadLeads]);

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "score-high";
    if (score >= 0.5) return "score-medium";
    return "score-low";
  };

  const handleExport = () => {
    window.open(api.exportCSV(runId), "_blank");
  };

  const toggleSelectionMode = () => {
    setSelectionMode(!selectionMode);
    setSelectedIds(new Set());
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === leads.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(leads.map((l) => l.id)));
    }
  };

  const toggleLeadSelection = (leadId: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(leadId)) {
      newSelected.delete(leadId);
    } else {
      newSelected.add(leadId);
    }
    setSelectedIds(newSelected);
  };

  const handleDraftSelected = async () => {
    if (selectedIds.size === 0) return;
    setDrafting(true);
    try {
      await api.draftEmails(Array.from(selectedIds), draftLanguage);
      await loadLeads();
      setSelectionMode(false);
      setSelectedIds(new Set());
    } catch (error) {
      console.error("Failed to draft emails:", error);
    } finally {
      setDrafting(false);
    }
  };

  const handleSaveLead = async (id: string, updates: Partial<Lead>) => {
    try {
      await api.patch(`/api/leads/${id}`, updates);
      // Refresh local state
      setLeads((prev) =>
        prev.map((l) => (l.id === id ? { ...l, ...updates } : l)),
      );
    } catch (error) {
      console.error("Error updating lead:", error);
    }
  };

  const handleUpdateNote = async (id: string, notes: string) => {
    try {
      await api.patch(`/api/leads/${id}`, { notes });
      setLeads((prev) => prev.map((l) => (l.id === id ? { ...l, notes } : l)));
    } catch (error) {
      console.error("Error updating note:", error);
    }
  };

  const getBadgeClass = (status: string) => {
    const s = status?.toLowerCase();
    switch (s) {
      case "sent":
        return "badge-success";
      case "failed":
        return "badge-error";
      case "pending_approval":
        return "badge-warning";
      case "drafted":
        return "badge-info interactive";
      case "approved":
        return "badge-info interactive";
      default:
        return "badge-warning";
    }
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
      <div
        className="leads-header"
        style={{
          marginBottom: "1.5rem",
          borderBottom: "1px solid rgba(255,255,255,0.1)",
          paddingBottom: "1rem",
        }}
      >
        <h2 className="text-gradient" style={{ fontSize: "2rem" }}>
          Leads ({run?.total_leads || 0})
        </h2>
      </div>
      {/* Run Specific Stats in Header */}
      {run && (
        <div className="run-stats-summary">
          <div className="card">
            <h4 style={{ margin: 0, opacity: 0.7, fontSize: "0.85rem" }}>
              Emails Found
            </h4>
            <div
              style={{
                fontSize: "1.75rem",
                fontWeight: 800,
                color: "var(--primary-start)",
                marginTop: "0.5rem",
              }}
            >
              {run.total_emails || 0}
            </div>
          </div>
          <div className="card">
            <h4 style={{ margin: 0, opacity: 0.7, fontSize: "0.85rem" }}>
              Websites Found
            </h4>
            <div
              style={{
                fontSize: "1.75rem",
                fontWeight: 800,
                color: "var(--accent)",
                marginTop: "0.5rem",
              }}
            >
              {run.total_websites || 0}
            </div>
          </div>
          <div className="card">
            <h4 style={{ margin: 0, opacity: 0.7, fontSize: "0.85rem" }}>
              Run Status
            </h4>
            <div
              style={{
                fontSize: "1.25rem",
                fontWeight: 700,
                textTransform: "uppercase",
                marginTop: "0.75rem",
                color: "var(--text-primary)",
              }}
            >
              {run.status}
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="leads-tabs">
        <button
          className={`tab-btn ${activeTab === "new" ? "active" : ""}`}
          onClick={() => setActiveTab("new")}
        >
          New Leads ({(run?.total_leads || 0) - (run?.total_drafts || 0)})
        </button>
        <button
          className={`tab-btn ${activeTab === "drafted" ? "active" : ""}`}
          onClick={() => setActiveTab("drafted")}
        >
          Drafted Emails ({run?.total_drafts || 0})
        </button>
      </div>

      {/* Advanced Filters */}
      <div className="filter-controls">
        {selectionMode && (
          <button
            className="btn btn-outline btn-sm"
            onClick={toggleSelectAll}
            style={{ borderRadius: "20px", padding: "4px 15px" }}
          >
            {selectedIds.size === leads.length && leads.length > 0
              ? "Deselect All"
              : "Select All"}
          </button>
        )}

        <label className="filter-group">
          <input
            type="checkbox"
            checked={filterHasEmail === true}
            onChange={(e) => setFilterHasEmail(e.target.checked ? true : null)}
            className="checkbox-custom"
          />
          <span>Has Email</span>
        </label>
        <label className="filter-group">
          <input
            type="checkbox"
            checked={filterHasWebsite === true}
            onChange={(e) =>
              setFilterHasWebsite(e.target.checked ? true : null)
            }
            className="checkbox-custom"
          />
          <span>Has Website</span>
        </label>

        {/* Language Selection for Drafting */}
        {selectionMode && (
          <div className="lang-toggle">
            <button
              className={`lang-btn ${draftLanguage === "DE" ? "active" : ""}`}
              onClick={() => setDraftLanguage("DE")}
            >
              GER
            </button>
            <button
              className={`lang-btn ${draftLanguage === "EN" ? "active" : ""}`}
              onClick={() => setDraftLanguage("EN")}
            >
              EN
            </button>
          </div>
        )}

        <div className="result-count">
          Showing {leads.length} {leads.length === 1 ? "Lead" : "Leads"}
        </div>
      </div>

      {/* Main Actions Bar */}
      <div className="main-actions-bar">
        {selectionMode ? (
          <>
            <span className="selected-count">{selectedIds.size} selected</span>
            <button
              className="btn btn-outline btn-sm"
              onClick={toggleSelectionMode}
            >
              Cancel
            </button>
            {selectedIds.size > 0 && (
              <button
                className="btn btn-primary btn-sm"
                onClick={handleDraftSelected}
                disabled={drafting}
              >
                {drafting ? "Drafting..." : "Draft Emails"}
              </button>
            )}
          </>
        ) : (
          <>
            <button
              className="btn btn-outline btn-sm"
              onClick={toggleSelectionMode}
            >
              Mark for Mail
            </button>
            <button className="btn btn-outline btn-sm" onClick={handleExport}>
              Export CSV
            </button>
            <button
              className="btn btn-sm"
              onClick={onClose}
              style={{ display: "flex", alignItems: "center", gap: "8px" }}
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
                <polyline points="9 22 9 12 15 12 15 22" />
              </svg>
            </button>
          </>
        )}
      </div>

      {drafting && (
        <div className="progress-container">
          <div className="progress-bar" style={{ width: "100%" }}></div>
          <small
            style={{ display: "block", textAlign: "center", marginTop: "5px" }}
          >
            Processing emails via Ollama...
          </small>
        </div>
      )}

      {leads.length === 0 ? (
        <p className="empty-state">No leads found for this run.</p>
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th className="col-select">Select</th>
                <th className="col-rank">#</th>
                <th className="col-business">Business Name</th>
                <th className="col-address">Address</th>
                <th className="col-contact">Contact</th>
                <th className="col-social">Social Media</th>
                <th className="col-notes">Notes</th>
                <th className="col-status">Email Status</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead, index) => (
                <tr
                  key={lead.id}
                  className={selectedIds.has(lead.id) ? "row-selected" : ""}
                >
                  <td className="col-select">
                    {!selectionMode && (
                      <button
                        className="btn-text"
                        onClick={() => setEditingLead(lead)}
                        style={{ padding: "4px", opacity: 0.6 }}
                        title="Edit Lead"
                      >
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
                        </svg>
                      </button>
                    )}
                    <input
                      type="checkbox"
                      checked={selectedIds.has(lead.id)}
                      onChange={() => toggleLeadSelection(lead.id)}
                      className="checkbox-custom"
                    />
                  </td>
                  <td className="col-rank">
                    {(page - 1) * perPage + index + 1}
                  </td>
                  <td className="col-business">
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
                  <td className="col-address">{lead.address || "—"}</td>
                  <td className="col-contact">
                    {lead.email && (
                      <div className="contact-item">📧 {lead.email}</div>
                    )}
                    {lead.phone && (
                      <div className="contact-item">📞 {lead.phone}</div>
                    )}
                    {!lead.email && !lead.phone && "—"}
                  </td>
                  <td className="col-social">
                    <div className="social-links">
                      {Object.entries(
                        lead.enrichment_data?.social_links || {},
                      ).map(([platform, link]) => (
                        <a
                          key={platform}
                          href={link as string}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="social-icon"
                          title={platform}
                        >
                          {platform === "facebook" && "FB"}
                          {platform === "instagram" && "IG"}
                          {platform === "linkedin" && "LI"}
                          {platform === "twitter" && "TW"}
                          {![
                            "facebook",
                            "instagram",
                            "linkedin",
                            "twitter",
                          ].includes(platform) && "🔗"}
                        </a>
                      ))}
                    </div>
                  </td>
                  <td className="col-notes">
                    <textarea
                      className="note-input"
                      placeholder="Add note..."
                      defaultValue={lead.notes || ""}
                      onBlur={(e) => handleUpdateNote(lead.id, e.target.value)}
                    />
                  </td>
                  <td className="col-status">
                    {(() => {
                      const statusRaw = lead.email_status;
                      const status = statusRaw?.toLowerCase();
                      const badgeClass = getBadgeClass(status || "");

                      if (!status || status === "pending_approval") {
                        return <span className={badgeClass}>No Draft</span>;
                      }

                      let label = status.replace("_", " ");
                      if (status === "approved") label = "Email Approved";
                      if (status === "sent") label = "Email Send";
                      if (status === "drafted") label = "Drafted";

                      return (
                        <span
                          className={`badge ${badgeClass}`}
                          onClick={() =>
                            lead.email_id && setSelectedEmailId(lead.email_id)
                          }
                          title={
                            ["drafted", "approved"].includes(status)
                              ? "Click to edit/send"
                              : ""
                          }
                        >
                          {label}
                        </span>
                      );
                    })()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {totalCount > perPage && (
        <div className="pagination">
          <button
            className="btn btn-outline btn-small"
            disabled={page === 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
          >
            Previous
          </button>
          <div className="page-info">
            Page {page} of {Math.ceil(totalCount / perPage)} ({totalCount}{" "}
            total)
          </div>
          <button
            className="btn btn-outline btn-small"
            disabled={page >= Math.ceil(totalCount / perPage)}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}

      {selectedEmailId && (
        <EmailDraftModal
          emailId={selectedEmailId}
          onClose={() => setSelectedEmailId(null)}
          onUpdate={loadLeads}
        />
      )}

      {editingLead && (
        <LeadEditModal
          lead={editingLead}
          onSave={handleSaveLead}
          onClose={() => setEditingLead(null)}
        />
      )}
    </div>
  );
}
