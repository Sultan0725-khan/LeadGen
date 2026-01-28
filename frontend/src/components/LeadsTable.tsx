import { useState, useEffect, useCallback } from "react";
import { api } from "../api/client";
import type { Lead, Run } from "../api/client";
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
    first_name: lead.first_name || "",
    last_name: lead.last_name || "",
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
          <div style={{ display: "flex", gap: "1rem" }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>First Name</label>
              <input
                type="text"
                value={formData.first_name}
                onChange={(e) =>
                  setFormData({ ...formData, first_name: e.target.value })
                }
              />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Last Name</label>
              <input
                type="text"
                value={formData.last_name}
                onChange={(e) =>
                  setFormData({ ...formData, last_name: e.target.value })
                }
              />
            </div>
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
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [loadingIds, setLoadingIds] = useState<Set<string>>(new Set());
  const [drafting, setDrafting] = useState(false); // Used for bulk drafting container
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);
  const [editingLead, setEditingLead] = useState<Lead | null>(null);
  const [run, setRun] = useState<Run | null>(null);
  const [activeTab, setActiveTab] = useState<"new" | "drafted" | "sent">("new");
  const [filterHasEmail, setFilterHasEmail] = useState<boolean | null>(null);
  const [filterHasWebsite, setFilterHasWebsite] = useState<boolean | null>(
    null,
  );
  const [draftLanguage, setDraftLanguage] = useState<"EN" | "DE">("DE");
  const [page, setPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [sendingToSalesforce, setSendingToSalesforce] = useState(false);
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [toast, setToast] = useState<{ message: string; visible: boolean }>({
    message: "",
    visible: false,
  });
  const perPage = 100;

  const loadLeads = useCallback(
    async (showLoading = true) => {
      try {
        if (showLoading) setLoading(true);
        // Fetch leads with specific filters based on dashboard/tab state
        const filters = {
          has_email: filterHasEmail ?? undefined,
          has_website: filterHasWebsite ?? undefined,
          email_status: activeTab,
          q: debouncedSearch || undefined,
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
        if (showLoading) setLoading(false);
      }
    },
    [runId, activeTab, filterHasEmail, filterHasWebsite, page, debouncedSearch],
  );

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 500);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const showToast = (message: string) => {
    setToast({ message, visible: true });
    setTimeout(() => {
      setToast((prev) => ({ ...prev, visible: false }));
    }, 3000);
  };

  useEffect(() => {
    // Initial load and tab switches show full loading spinner
    loadLeads(true);
  }, [runId, activeTab, loadLeads]);

  useEffect(() => {
    // Filter toggles and pagination use silent reload to prevent UI jump
    if (loading) return;
    loadLeads(false);
  }, [
    filterHasEmail,
    filterHasWebsite,
    page,
    loadLeads,
    loading,
    debouncedSearch,
  ]);

  const handleExport = () => {
    window.open(api.exportCSV(runId), "_blank");
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

  const handleResendSingleEmail = async (emailId: string) => {
    try {
      setDrafting(true);
      const result = await api.sendEmail(emailId);
      if (result.status === "success") {
        loadLeads(false);
      } else {
        alert(`Failed to re-send email: ${result.error}`);
      }
    } catch (err) {
      console.error("Resend error:", err);
    } finally {
      setDrafting(false);
    }
  };

  const handleResendSingleSFDC = async (leadId: string) => {
    setSendingToSalesforce(true);
    try {
      const result = await api.sendToSalesforce([leadId]);
      if (result.results[0].success) {
        loadLeads(false);
      } else {
        alert(`Failed to send to Salesforce: ${result.results[0].error}`);
      }
    } catch (error) {
      console.error("SFDC Resend error:", error);
    } finally {
      setSendingToSalesforce(false);
    }
  };

  const handleDraftSelected = async () => {
    if (selectedIds.size === 0) {
      showToast("Please select at least one checkbox or lead");
      return;
    }
    setDrafting(true);
    try {
      await api.draftEmails(Array.from(selectedIds), draftLanguage);
      await loadLeads();
      setSelectedIds(new Set());
    } catch (error) {
      console.error("Failed to draft emails:", error);
    } finally {
      setDrafting(false);
    }
  };

  const handleSendToSalesforce = async () => {
    if (selectedIds.size === 0) return;
    setSendingToSalesforce(true);
    try {
      const result = await api.sendToSalesforce(Array.from(selectedIds));
      const successes = result.results.filter((r) => r.success).length;
      const failures = result.results.filter((r) => !r.success);

      if (successes > 0) {
        alert(`Successfully sent ${successes} leads to Salesforce`);
      }
      if (failures.length > 0) {
        alert(
          `Failed to send ${failures.length} leads. Error: ${failures[0].error}`,
        );
      }

      await loadLeads();
      setSelectedIds(new Set());
    } catch (error) {
      console.error("Failed to send leads to Salesforce:", error);
      alert("An error occurred while sending leads to Salesforce.");
    } finally {
      setSendingToSalesforce(false);
    }
  };

  const handleSaveLead = async (id: string, updates: Partial<Lead>) => {
    try {
      await api.patch(`/leads/${id}`, updates);
      // Refresh local state
      setLeads((prev) =>
        prev.map((l) => (l.id === id ? { ...l, ...updates } : l)),
      );
    } catch (error) {
      console.error("Error updating lead:", error);
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
      case "sfdx":
        return "badge-success interactive";
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
      <div
        className="leads-tabs-container"
        style={{ display: "flex", alignItems: "center", marginBottom: "1rem" }}
      >
        <div className="leads-tabs">
          <button
            className={`tab-btn ${activeTab === "new" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("new");
              setSearchQuery("");
            }}
          >
            New Leads ({(run?.total_leads || 0) - (run?.total_drafts || 0)})
          </button>
          <button
            className={`tab-btn ${activeTab === "drafted" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("drafted");
              setSearchQuery("");
            }}
          >
            Drafted Emails ({run?.total_drafts || 0})
          </button>
          <button
            className={`tab-btn ${activeTab === "sent" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("sent");
              setSearchQuery("");
            }}
          >
            Sent Emails
          </button>
        </div>
        <button className="btn btn-outline btn-home-wide" onClick={onClose}>
          Home
        </button>
      </div>

      {/* Advanced Filters */}
      <div className="filter-controls">
        {activeTab === "sent" && (
          <div className="search-bar" style={{ marginRight: "1rem" }}>
            <input
              type="text"
              placeholder="🔍 Search Business..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                borderRadius: "20px",
                padding: "6px 15px",
                border: "1px solid #ddd",
                width: "350px",
                fontSize: "0.85rem",
                outline: "none",
                backgroundColor: "white",
              }}
            />
          </div>
        )}
        <button
          className="btn btn-outline btn-sm"
          onClick={() => {
            if (isSelectionMode) {
              setIsSelectionMode(false);
              setSelectedIds(new Set());
            } else {
              setIsSelectionMode(true);
            }
          }}
          style={{ borderRadius: "20px", padding: "4px 15px" }}
        >
          {isSelectionMode ? "Cancel Selection" : "Select Multiple Leads"}
        </button>
        {isSelectionMode && (
          <button
            className="btn btn-outline btn-sm"
            onClick={toggleSelectAll}
            style={{
              borderRadius: "20px",
              padding: "4px 15px",
              marginLeft: "10px",
            }}
          >
            {selectedIds.size === leads.length ? "Deselect All" : "Select All"}
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

        <div className="result-count">
          Showing {leads.length} {leads.length === 1 ? "Lead" : "Leads"}
        </div>
      </div>

      {/* Main Actions Bar */}
      <div className="main-actions-bar">
        {selectedIds.size > 0 && (
          <>
            <span className="selected-count">{selectedIds.size} selected</span>
            {activeTab === "new" ? (
              <button
                className="btn btn-primary btn-sm"
                onClick={handleDraftSelected}
                disabled={drafting}
              >
                {drafting ? "mhh mhh ing..." : "Draft Email"}
              </button>
            ) : (
              <>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleDraftSelected}
                  disabled={drafting}
                >
                  {drafting ? "mhh mhh ing..." : "Re-Draft Email"}
                </button>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleSendToSalesforce}
                  disabled={sendingToSalesforce}
                  style={{ marginLeft: "10px", backgroundColor: "#00a1e0" }}
                >
                  {sendingToSalesforce ? "Sending..." : "Send Lead to SFDC"}
                </button>
              </>
            )}
          </>
        )}
        <button
          className="btn btn-outline btn-sm"
          onClick={handleExport}
          style={{ marginLeft: selectedIds.size > 0 ? "10px" : "0" }}
        >
          Export CSV
        </button>
      </div>

      {drafting && (
        <div className="ollama-loader">
          <div className="ollama-brain">🦙..🐏..🦙..🐏</div>
          <div className="ollama-text">Ollama is mhh mhh ing...</div>
        </div>
      )}

      {leads.length === 0 ? (
        <p className="empty-state">No leads found for this run.</p>
      ) : (
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th className="col-rank" style={{ textAlign: "center" }}>
                  #
                </th>
                <th className="col-business">Business Name</th>
                <th className="col-info">Info</th>
                <th className="col-social">Social Media</th>
                {activeTab !== "sent" && <th className="col-edit">Edit</th>}
                <th className="col-status-left">
                  {activeTab === "sent" ? "Status Email" : "Status"}
                </th>
                <th className="col-actions-left">
                  {activeTab === "sent" ? "Status Salesforce" : "Action"}
                </th>
              </tr>
            </thead>
            <tbody>
              {leads.map((lead, index) => (
                <tr
                  key={lead.id}
                  className={selectedIds.has(lead.id) ? "row-selected" : ""}
                >
                  <td className="col-rank">
                    <div
                      style={{
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                        gap: "8px",
                      }}
                    >
                      <span>{(page - 1) * perPage + index + 1}</span>
                      {isSelectionMode && (
                        <input
                          type="checkbox"
                          checked={selectedIds.has(lead.id)}
                          onChange={() => toggleLeadSelection(lead.id)}
                          className="checkbox-custom"
                        />
                      )}
                    </div>
                  </td>
                  <td className="col-business">
                    <div className="business-name">{lead.business_name}</div>
                    {lead.website && (
                      <a
                        href={lead.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="website-link"
                        title={lead.website}
                      >
                        {lead.website}
                      </a>
                    )}
                  </td>
                  <td className="col-info">
                    <ul className="info-list">
                      {lead.email && (
                        <li className="info-item" title={lead.email}>
                          <span className="info-icon">📧</span>
                          <span className="truncate">{lead.email}</span>
                        </li>
                      )}
                      {lead.phone && (
                        <li className="info-item" title={lead.phone}>
                          <span className="info-icon">📞</span>
                          <span>{lead.phone}</span>
                        </li>
                      )}
                      {lead.address && (
                        <li className="info-item" title={lead.address}>
                          <span className="info-icon">📍</span>
                          <span className="truncate">{lead.address}</span>
                        </li>
                      )}
                      {!lead.email && !lead.phone && !lead.address && (
                        <li className="info-item">
                          <span className="info-icon">⚠️</span>
                          <span>No info found</span>
                        </li>
                      )}
                    </ul>
                  </td>
                  <td className="col-social">
                    <div className="social-links">
                      {Object.entries(
                        lead.enrichment_data?.social_links || {},
                      ).map(([platform, link]) => {
                        const platformClass = platform.toLowerCase();
                        return (
                          <a
                            key={platform}
                            href={link as string}
                            target="_blank"
                            rel="noopener noreferrer"
                            className={`social-icon ${platformClass} generic`}
                            title={platform}
                          >
                            {platform.toLowerCase() === "facebook" && "FB"}
                            {platform.toLowerCase() === "instagram" && "IG"}
                            {platform.toLowerCase() === "linkedin" && "LI"}
                            {platform.toLowerCase() === "twitter" && "TW"}
                            {platform.toLowerCase() === "tiktok" && "TT"}
                            {![
                              "facebook",
                              "instagram",
                              "linkedin",
                              "twitter",
                              "tiktok",
                            ].includes(platform.toLowerCase()) && "🔗"}
                          </a>
                        );
                      })}
                      {Object.keys(lead.enrichment_data?.social_links || {})
                        .length === 0 && (
                        <span style={{ fontSize: "0.8rem", opacity: 0.5 }}>
                          —
                        </span>
                      )}
                    </div>
                  </td>
                  {activeTab !== "sent" && (
                    <td className="col-edit">
                      <button
                        className="btn-edit"
                        onClick={() => setEditingLead(lead)}
                        title="Edit Lead"
                      >
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                      </button>
                    </td>
                  )}
                  {activeTab !== "sent" ? (
                    <>
                      <td className="col-status-left">
                        {(() => {
                          const statusRaw = lead.email_status;
                          const status = statusRaw?.toLowerCase();
                          const badgeClass = getBadgeClass(status || "");

                          if (!status || status === "pending_approval") {
                            return (
                              <span className={`badge ${badgeClass}`}>
                                No Draft
                              </span>
                            );
                          }

                          let label = status.replace("_", " ");
                          if (status === "approved") label = "Approved";
                          if (status === "sent") label = "Email Sent";
                          if (status === "drafted") label = "Drafted";
                          if (status === "sfdx") label = "In Salesforce";

                          return (
                            <span
                              className={`badge ${badgeClass}`}
                              onClick={() =>
                                lead.email_id &&
                                setSelectedEmailId(lead.email_id)
                              }
                              title={
                                ["drafted", "approved"].includes(status)
                                  ? "Click to edit/send"
                                  : ""
                              }
                            >
                              {status === "drafted" ? "View Email" : label}
                            </span>
                          );
                        })()}
                      </td>
                      <td className="col-actions-left">
                        <button
                          className="btn btn-primary btn-small"
                          onClick={async () => {
                            if (activeTab === "new") {
                              setLoadingIds((prev) =>
                                new Set(prev).add(lead.id),
                              );
                              try {
                                await api.draftEmails([lead.id], draftLanguage);
                                loadLeads(false);
                              } catch (err) {
                                console.error("Draft error:", err);
                              } finally {
                                setLoadingIds((prev) => {
                                  const next = new Set(prev);
                                  next.delete(lead.id);
                                  return next;
                                });
                              }
                            } else {
                              // Drafted tab - Send Email
                              if (!lead.email_id) return;
                              setLoadingIds((prev) =>
                                new Set(prev).add(lead.id),
                              );
                              try {
                                const result = await api.sendEmail(
                                  lead.email_id,
                                );
                                if (result.status === "success") {
                                  loadLeads(false);
                                  showToast(
                                    "Email and Salesforce sync successful!",
                                  );
                                } else {
                                  alert(`Send failed: ${result.error}`);
                                }
                              } catch (err: unknown) {
                                console.error("Send error:", err);
                                const errorMessage =
                                  err instanceof Error
                                    ? err.message
                                    : "Check terminal logs";
                                alert(`Send error: ${errorMessage}`);
                              } finally {
                                setLoadingIds((prev) => {
                                  const next = new Set(prev);
                                  next.delete(lead.id);
                                  return next;
                                });
                              }
                            }
                          }}
                          disabled={loadingIds.has(lead.id)}
                          style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                        >
                          {loadingIds.has(lead.id)
                            ? "mhh mhh ing..."
                            : activeTab === "new"
                              ? "Draft Email"
                              : "Send Email"}
                        </button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td className="col-status-left">
                        <div
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "flex-start",
                            gap: "6px",
                          }}
                        >
                          <span className={`badge badge-success`}>
                            Send (success)
                          </span>
                          <button
                            className="btn btn-outline btn-xs"
                            style={{ fontSize: "0.65rem", padding: "2px 6px" }}
                            onClick={() =>
                              lead.email_id &&
                              handleResendSingleEmail(lead.email_id)
                            }
                            disabled={drafting}
                          >
                            {drafting ? "..." : "Re-send Email"}
                          </button>
                        </div>
                      </td>
                      <td className="col-status-left">
                        <div
                          style={{
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "flex-start",
                            gap: "6px",
                          }}
                        >
                          <span
                            className={`badge ${lead.sfdc_status === "success" ? "badge-success" : "badge-warning"}`}
                          >
                            {lead.sfdc_status === "success"
                              ? "Send (success)"
                              : lead.sfdc_status === "failed"
                                ? "Failed"
                                : "Pending"}
                          </span>
                          <button
                            className="btn btn-outline btn-xs"
                            style={{ fontSize: "0.65rem", padding: "2px 6px" }}
                            onClick={() => handleResendSingleSFDC(lead.id)}
                            disabled={sendingToSalesforce}
                          >
                            {sendingToSalesforce
                              ? "..."
                              : "Re-send to Salesforce"}
                          </button>
                        </div>
                      </td>
                    </>
                  )}
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

      {toast.visible && (
        <div className="toast-notification">
          <span className="toast-icon">⚠️</span>
          {toast.message}
        </div>
      )}
    </div>
  );
}
