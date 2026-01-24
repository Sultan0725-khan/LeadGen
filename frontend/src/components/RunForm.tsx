import { useState } from "react";
import { api } from "../api/client";
import type { CreateRunRequest } from "../api/client";
import "./RunForm.css";

interface RunFormProps {
  onRunCreated: () => void;
}

export function RunForm({ onRunCreated }: RunFormProps) {
  const [location, setLocation] = useState("");
  const [category, setCategory] = useState("");
  const [requireApproval, setRequireApproval] = useState(true);
  const [dryRun, setDryRun] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data: CreateRunRequest = {
        location,
        category,
        require_approval: requireApproval,
        dry_run: dryRun,
      };

      await api.createRun(data);

      // Reset form
      setLocation("");
      setCategory("");

      // Notify parent
      onRunCreated();
    } catch (err: any) {
      setError(err.message || "Failed to create run");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card run-form">
      <h2 className="text-gradient">Start New Lead Generation Run</h2>

      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={handleSubmit} className="form">
        <div className="form-group">
          <label htmlFor="location">Location</label>
          <input
            id="location"
            type="text"
            className="input"
            placeholder="e.g., Berlin, Mitte or Munich, Bavaria"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            required
          />
          <small>Enter city, district, or region</small>
        </div>

        <div className="form-group">
          <label htmlFor="category">Category</label>
          <input
            id="category"
            type="text"
            className="input"
            placeholder="e.g., restaurant, café, bar"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            required
          />
          <small>Business type or industry</small>
        </div>

        <div className="form-checkboxes">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={requireApproval}
              onChange={(e) => setRequireApproval(e.target.checked)}
            />
            <span>Require manual approval before sending emails</span>
          </label>

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
            />
            <span>Dry run (generate emails but don't send)</span>
          </label>
        </div>

        <button type="submit" className="btn btn-large" disabled={loading}>
          {loading ? (
            <>
              <span className="spinner-small"></span>
              Creating Run...
            </>
          ) : (
            "Start Lead Generation"
          )}
        </button>
      </form>
    </div>
  );
}
