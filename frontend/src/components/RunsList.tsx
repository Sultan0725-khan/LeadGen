import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { Run } from "../api/client";
import "./RunsList.css";

interface RunsListProps {
  refreshTrigger: number;
  onSelectRun: (runId: string) => void;
}

export function RunsList({ refreshTrigger, onSelectRun }: RunsListProps) {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRuns();
  }, [refreshTrigger]);

  const loadRuns = async () => {
    try {
      const data = await api.getRuns();
      setRuns(data);
    } catch (err) {
      console.error("Failed to load runs:", err);
    } finally {
      setLoading(false);
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
      // Refresh runs list
      setRuns(runs.filter((r) => r.id !== runId));
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
    <div className="card runs-list">
      <h2 className="text-gradient">Recent Runs</h2>

      {runs.length === 0 ? (
        <p className="empty-state">
          No runs yet. Start your first lead generation run above!
        </p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Location</th>
              <th>Category</th>
              <th>Status</th>
              <th>Leads</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>{run.location}</td>
                <td>{run.category}</td>
                <td>{getStatusBadge(run.status)}</td>
                <td>{run.total_leads}</td>
                <td>{new Date(run.created_at).toLocaleString()}</td>
                <td>
                  <button
                    className="btn btn-small"
                    onClick={() => onSelectRun(run.id)}
                    disabled={run.status !== "completed"}
                  >
                    View Leads
                  </button>
                  <button
                    className="btn btn-small btn-danger"
                    onClick={() => handleDelete(run.id, run.location)}
                    style={{ marginLeft: "8px" }}
                    title="Delete this run and all associated data"
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
