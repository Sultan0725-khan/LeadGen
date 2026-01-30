import { useState, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
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

  useEffect(() => {
    const handleEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleEsc);
    return () => {
      window.removeEventListener("keydown", handleEsc);
    };
  }, [onClose]);

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

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

  return createPortal(
    <div className="modal-overlay" onClick={handleOverlayClick}>
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
    </div>,
    document.body,
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
  useEffect(() => {
    // Apply theme class to body for global background transition
    document.body.classList.add(`theme-${activeTab}`);

    // Cleanup other theme classes when switching or unmounting
    const themes = ["theme-new", "theme-drafted", "theme-sent"];
    themes.forEach((t) => {
      if (t !== `theme-${activeTab}`) {
        document.body.classList.remove(t);
      }
    });

    return () => {
      document.body.classList.remove(`theme-${activeTab}`);
    };
  }, [activeTab]);

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
    window.open(api.exportCSV(runId, activeTab), "_blank");
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
    setLoadingIds((prev) => new Set(prev).add(emailId));
    try {
      const result = await api.sendEmail(emailId);
      if (result.status === "success") {
        showToast("E-Mail erfolgreich gesendet!");
      } else {
        alert(`Fehler beim Senden: ${result.error}`);
      }
    } catch (err) {
      console.error("Resend error:", err);
    } finally {
      setLoadingIds((prev) => {
        const next = new Set(prev);
        next.delete(emailId);
        return next;
      });
      await loadLeads(false);
    }
  };

  const handleResendSingleSFDC = async (leadId: string) => {
    setLoadingIds((prev) => new Set(prev).add(leadId));
    try {
      const result = await api.sendToSalesforce([leadId]);
      if (result.results[0].success) {
        showToast("Salesforce Sync erfolgreich!");
      } else {
        alert(`Salesforce Fehler: ${result.results[0].error}`);
      }
    } catch (error) {
      console.error("SFDC Resend error:", error);
    } finally {
      setLoadingIds((prev) => {
        const next = new Set(prev);
        next.delete(leadId);
        return next;
      });
      await loadLeads(false);
    }
  };

  const handleDraftSelected = async () => {
    // Only process leads with email addresses
    const selectableLeads = leads.filter((l) => selectedIds.has(l.id));
    const leadsWithEmail = selectableLeads.filter((l) => l.email);

    if (leadsWithEmail.length === 0) {
      if (selectableLeads.length > 0) {
        showToast("Keiner der gewählten Leads hat eine E-Mail Adresse.");
      } else {
        showToast("Please select at least one lead");
      }
      return;
    }

    if (leadsWithEmail.length < selectableLeads.length) {
      const skippedLeads = selectableLeads.filter((l) => !l.email);
      const skippedNames = skippedLeads
        .slice(0, 5)
        .map((l) => l.business_name)
        .join(", ");
      const moreText = skippedLeads.length > 5 ? "..." : "";

      if (
        !confirm(
          `${skippedLeads.length} Leads haben keine E-Mail Adresse (${skippedNames}${moreText}) und werden übersprungen. Fortfahren?`,
        )
      ) {
        return;
      }
    }

    setDrafting(true);
    try {
      await api.draftEmails(
        leadsWithEmail.map((l) => l.id),
        draftLanguage,
      );
      showToast(`${leadsWithEmail.length} Drafts angestoßen.`);
      await loadLeads(false);
      setSelectedIds(new Set());
    } catch (error) {
      console.error("Failed to draft emails:", error);
      showToast("Draft error - check terminal");
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
      <div className="leads-header-mini">
        <h2 className="text-gradient">Leads ({run?.total_leads || 0})</h2>
        {run && (
          <div className="header-stats-row">
            <div className="stat-capsule">
              <span className="stat-label">Emails:</span>
              <span className="stat-val primary">{run.total_emails || 0}</span>
            </div>
            <div className="stat-capsule">
              <span className="stat-label">Websites:</span>
              <span className="stat-val secondary">
                {run.total_websites || 0}
              </span>
            </div>
          </div>
        )}
      </div>
      {/* Run Specific Stats in Header */}

      {/* ----------------------------- Tabs Container----------------------------------------------------------------- */}
      {/* Tabs moved here to be right above the table */}
      <div className="leads-tabs-container">
        <div className="leads-tabs-cards">
          <button
            className={`tab-card ${activeTab === "new" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("new");
              setSearchQuery("");
              setSelectedIds(new Set());
            }}
          >
            <span className="tab-card-label">New Leads</span>
            <span className="tab-card-value">
              {(run?.total_leads || 0) -
                (run?.total_drafts || 0) -
                (run?.total_sent || 0)}
            </span>
          </button>
          <button
            className={`tab-card ${activeTab === "drafted" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("drafted");
              setSearchQuery("");
              setSelectedIds(new Set());
            }}
          >
            <span className="tab-card-label">Drafted Emails</span>
            <span className="tab-card-value">{run?.total_drafts || 0}</span>
          </button>
          <button
            className={`tab-card ${activeTab === "sent" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("sent");
              setSearchQuery("");
              setSelectedIds(new Set());
            }}
          >
            <span className="tab-card-label">Sent Emails</span>
            <span className="tab-card-value">{run?.total_sent || 0}</span>
          </button>
        </div>

        {/* ----------------------------- Home Button ----------------------------------------------------------------- */}
        <button
          className="export-card"
          onClick={handleExport}
          title="Export CSV"
        >
          <div className="export-card-icon">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
          </div>
          <span className="export-card-label">
            {activeTab === "new"
              ? "New"
              : activeTab === "drafted"
                ? "Drafted"
                : "Sent"}
          </span>
        </button>
        {/* ----------------------------- Home Button ----------------------------------------------------------------- */}
        <button
          className="home-card"
          onClick={onClose}
          title="Back to Dashboard"
        >
          <div className="home-card-icon">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
          </div>
          <span className="home-card-label">Home</span>
        </button>
        {/* ----------------------------- Home Button ----------------------------------------------------------------- */}
      </div>

      {/* --------------------------------- Filter Controls ------------------------------------------------------ */}
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

        {activeTab === "new" && (
          <>
            <label className="filter-group">
              <input
                type="checkbox"
                checked={filterHasEmail === true}
                onChange={(e) =>
                  setFilterHasEmail(e.target.checked ? true : null)
                }
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
          </>
        )}

        {/* Language Selection moved to AI Draft header */}

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
                {drafting ? "🦙..🐏..🦙..🐏" : "Draft Email"}
              </button>
            ) : (
              <>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleDraftSelected}
                  disabled={drafting}
                >
                  {drafting ? "🦙..🐏..🦙..🐏" : "Re-Draft Email"}
                </button>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleSendToSalesforce}
                  disabled={sendingToSalesforce}
                  style={{ marginLeft: "10px", backgroundColor: "#00a1e0" }}
                >
                  {sendingToSalesforce
                    ? "Sending..."
                    : "Send Lead only to SFDC"}
                </button>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={async () => {
                    if (selectedIds.size === 0) return;
                    setSendingToSalesforce(true);
                    try {
                      const result = await api.sendBulkEmails(
                        Array.from(selectedIds),
                      );
                      const successes = result.results.filter(
                        (r) => r.success,
                      ).length;
                      const failures = result.results.filter((r) => !r.success);

                      if (successes > 0) {
                        showToast(`Successfully sent ${successes} emails!`);
                      }
                      if (failures.length > 0) {
                        alert(
                          `Failed to send ${failures.length} emails. Error: ${failures[0].error}`,
                        );
                      }
                      await loadLeads();
                      setSelectedIds(new Set());
                    } catch (error) {
                      console.error("Failed to send bulk emails:", error);
                      alert("An error occurred while sending emails.");
                    } finally {
                      setSendingToSalesforce(false);
                    }
                  }}
                  disabled={sendingToSalesforce}
                  style={{ marginLeft: "10px", backgroundColor: "#22c55e" }}
                >
                  {sendingToSalesforce ? "Sending..." : "Send Email"}
                </button>
              </>
            )}
          </>
        )}
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
                <th className="col-social">Social</th>
                <th className="col-edit">Edit</th>
                {activeTab !== "new" && (
                  <th className="col-ai-email">AI Email</th>
                )}
                {activeTab === "sent" ? (
                  <>
                    <th className="col-status">Delivery</th>
                    <th className="col-status-sf">SFDC</th>
                  </>
                ) : (
                  <th className="col-actions">
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        gap: "8px",
                      }}
                    >
                      <span>
                        {activeTab === "new" ? "AI Draft" : "📧 ☑️ ⇢ ☁️ ☑️"}
                      </span>
                      {activeTab === "new" && (
                        <div className="lang-toggle-compact">
                          <button
                            className={`lang-btn-xs ${draftLanguage === "DE" ? "active" : ""}`}
                            onClick={() => setDraftLanguage("DE")}
                            title="German"
                          >
                            DE
                          </button>
                          <button
                            className={`lang-btn-xs ${draftLanguage === "EN" ? "active" : ""}`}
                            onClick={() => setDraftLanguage("EN")}
                            title="English"
                          >
                            EN
                          </button>
                        </div>
                      )}
                    </div>
                  </th>
                )}
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
                  {activeTab !== "new" && (
                    <td className="col-ai-email">
                      <button
                        className="btn-edit"
                        onClick={() =>
                          lead.email_id && setSelectedEmailId(lead.email_id)
                        }
                        disabled={!lead.email_id}
                        title="View Email"
                        style={{
                          width: "auto",
                          padding: "0 12px",
                          fontSize: "0.8rem",
                          whiteSpace: "nowrap",
                        }}
                      >
                        View E-Mail
                      </button>
                    </td>
                  )}
                  {activeTab !== "sent" ? (
                    <td className="col-actions">
                      <button
                        className="btn btn-primary btn-small"
                        onClick={async () => {
                          if (activeTab === "new") {
                            if (!lead.email) {
                              showToast(
                                "Lead hat keine E-Mail Adresse. Draft nicht möglich!",
                              );
                              return;
                            }
                            setDrafting(true); // Trigger big llama loader
                            try {
                              await api.draftEmails([lead.id], draftLanguage);
                              await loadLeads(false);
                            } catch (err) {
                              console.error("Draft error:", err);
                            } finally {
                              setDrafting(false);
                            }
                          } else {
                            // Drafted tab - Send Email
                            if (!lead.email_id) return;
                            setLoadingIds((prev) => new Set(prev).add(lead.id));
                            try {
                              const result = await api.sendEmail(lead.email_id);
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
                      >
                        {loadingIds.has(lead.id) || drafting
                          ? "🦙..🐏..🦙..🐏"
                          : activeTab === "new"
                            ? "Create Email"
                            : "Send Email"}
                      </button>
                      {/* Removed extra View Email button here as requested in previous instruction but just to be sure it is gone */}
                    </td>
                  ) : (
                    <>
                      <td className="col-status">
                        <div className="status-group">
                          <span
                            className={`badge badge-compact ${lead.email_status === "SENT" ? "badge-success" : lead.email_status === "FAILED" ? "badge-danger" : "badge-warning"}`}
                            data-tooltip={
                              lead.email_status === "FAILED"
                                ? lead.email_error ||
                                  "Fehler beim E-Mail Versand"
                                : lead.email_status !== "SENT"
                                  ? "E-Mail Versand ausstehend"
                                  : undefined
                            }
                          >
                            {lead.email_status === "SENT"
                              ? "✅"
                              : lead.email_status === "FAILED"
                                ? "❌"
                                : "⏳"}
                          </span>
                          <button
                            className={`btn-retry-icon ${loadingIds.has(lead.email_id || "") ? "spinning" : ""}`}
                            onClick={() =>
                              lead.email_id &&
                              handleResendSingleEmail(lead.email_id)
                            }
                            disabled={loadingIds.has(lead.email_id || "")}
                            title="E-Mail erneut senden"
                          >
                            🔄
                          </button>
                        </div>
                      </td>
                      <td className="col-status-sf">
                        <div className="status-group">
                          <span
                            className={`badge badge-compact ${lead.sfdc_status === "success" ? "badge-success" : lead.sfdc_status === "failed" ? "badge-danger" : "badge-warning"}`}
                            data-tooltip={
                              lead.sfdc_status === "failed"
                                ? lead.sfdc_error ||
                                  "Salesforce Sync fehlgeschlagen"
                                : lead.sfdc_status !== "success"
                                  ? "Salesforce Sync ausstehend"
                                  : undefined
                            }
                          >
                            {lead.sfdc_status === "success"
                              ? "✅"
                              : lead.sfdc_status === "failed"
                                ? "❌"
                                : "⏳"}
                          </span>
                          <button
                            className={`btn-retry-icon ${loadingIds.has(lead.id) ? "spinning" : ""}`}
                            onClick={() => handleResendSingleSFDC(lead.id)}
                            disabled={loadingIds.has(lead.id)}
                            title="An Salesforce senden"
                          >
                            ☁️
                          </button>
                          {lead.sfdc_id && lead.sfdc_instance_url && (
                            <a
                              href={`${lead.sfdc_instance_url}/lightning/r/Lead/${lead.sfdc_id}/view`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn-retry-icon"
                              title="Salesforce Lead öffnen"
                            >
                              🔗
                            </a>
                          )}
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
