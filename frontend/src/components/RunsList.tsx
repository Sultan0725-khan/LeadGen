import { useState } from "react";
import { api } from "../api/client";
import type { Run } from "../api/client";
import "./RunsList.css";

interface RunsListProps {
  runs: Run[];
  loading?: boolean;
  onSelectRun: (runId: string) => void;
  onRefresh?: () => void;
  onlyPinned?: boolean;
  title?: string;
}

export function RunsList({
  runs: initialRuns,
  loading = false,
  onSelectRun,
  onRefresh,
  onlyPinned = false,
  title = "Recent Runs",
}: RunsListProps) {
  const [sortConfig, setSortConfig] = useState<{
    key: keyof Run | "total_leads";
    direction: "asc" | "desc";
  }>({
    key: "created_at",
    direction: "desc",
  });

  const getSortedRuns = () => {
    const sortedData = [...initialRuns];

    sortedData.sort((a, b) => {
      const aVal = a[sortConfig.key];
      const bVal = b[sortConfig.key];

      if (aVal === undefined || bVal === undefined) return 0;

      if (aVal < bVal) return sortConfig.direction === "asc" ? -1 : 1;
      if (aVal > bVal) return sortConfig.direction === "asc" ? 1 : -1;
      return 0;
    });

    return sortedData;
  };

  const sortedRuns = getSortedRuns();

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const day = date.getDate().toString().padStart(2, "0");
    const month = (date.getMonth() + 1).toString().padStart(2, "0");
    const year = date.getFullYear().toString().slice(-2);
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");
    return `${day}.${month}.${year} ${hours}:${minutes}h`;
  };

  const handleSort = (key: keyof Run | "total_leads") => {
    setSortConfig((prev) => ({
      key,
      direction: prev.key === key && prev.direction === "asc" ? "desc" : "asc",
    }));
  };

  const getSortIcon = (key: keyof Run | "total_leads") => {
    if (sortConfig.key !== key) return "↕";
    return sortConfig.direction === "asc" ? "↑" : "↓";
  };

  const handleTogglePin = async (runId: string) => {
    try {
      await api.togglePinRun(runId);
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error("Failed to toggle pin:", err);
    }
  };

  const handleDelete = async (runId: string, location: string) => {
    if (
      !confirm(
        `Delete run "${location}"? This will permanently delete all leads, emails, and logs.`,
      )
    ) {
      return;
    }

    try {
      await api.deleteRun(runId);
      if (onRefresh) onRefresh();
    } catch (err) {
      console.error("Failed to delete run:", err);
      alert("Failed to delete run. Please try again.");
    }
  };

  const getStatusBadge = (status: string) => {
    const classMap: Record<string, string> = {
      queued: "badge-info",
      running: "badge-warning",
      completed: "badge-success",
      failed: "badge-error",
    };
    return (
      <span className={`badge ${classMap[status] || "badge-info"}`}>
        {status}
      </span>
    );
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
    <div className={`card runs-list ${onlyPinned ? "pinned-runs" : ""}`}>
      <h2 className="text-gradient">{title}</h2>

      {sortedRuns.length === 0 ? (
        <p className="empty-state">
          {onlyPinned
            ? "You can pin runs"
            : "No runs yet. Start your first lead generation run above!"}
        </p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th onClick={() => handleSort("location")} className="sortable">
                Location {getSortIcon("location")}
              </th>
              <th onClick={() => handleSort("category")} className="sortable">
                Category {getSortIcon("category")}
              </th>
              <th onClick={() => handleSort("status")} className="sortable">
                Status {getSortIcon("status")}
              </th>
              <th
                onClick={() => handleSort("total_leads")}
                className="sortable col-leads"
              >
                Leads {getSortIcon("total_leads")}
              </th>
              <th
                onClick={() => handleSort("created_at")}
                className="sortable col-created"
              >
                Created {getSortIcon("created_at")}
              </th>
              <th className="col-narrow">Pin</th>
              <th className="col-narrow">View</th>
              <th className="col-narrow">Delete</th>
            </tr>
          </thead>
          <tbody>
            {sortedRuns.map((run) => (
              <tr key={run.id}>
                <td>{run.location}</td>
                <td>{run.category}</td>
                <td>{getStatusBadge(run.status)}</td>
                <td className="col-leads">{run.total_leads}</td>
                <td className="col-created date-text">
                  {formatDate(run.created_at)}
                </td>
                <td className="col-narrow">
                  <button
                    className="btn-icon"
                    onClick={() => handleTogglePin(run.id)}
                    style={{
                      color: run.is_pinned ? "#4ade80" : "#7dd3fc",
                    }}
                    title={run.is_pinned ? "Unpin this run" : "Pin this run"}
                  >
                    <svg
                      width="20"
                      height="20"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                    >
                      <path d="M16,12V4H17V2H7V4H8V12L6,14V16H11.2V22H12.8V16H18V14L16,12Z" />
                    </svg>
                  </button>
                </td>
                <td className="col-narrow">
                  <button
                    className="btn-icon"
                    onClick={() => onSelectRun(run.id)}
                    disabled={run.status !== "completed"}
                    style={{ color: "#60a5fa" }}
                    title="View Leads"
                  >
                    👁️
                  </button>
                </td>
                <td className="col-narrow">
                  <button
                    className="btn-icon text-error"
                    onClick={() => handleDelete(run.id, run.location)}
                    title="Delete this run"
                  >
                    🗑️
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
