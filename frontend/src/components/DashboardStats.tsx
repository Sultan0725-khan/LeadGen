import { useState, useEffect } from "react";
import { api, type DashboardStats } from "../api/client";
import "./DashboardStats.css";

export function DashboardStatsComponent() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
    // Refresh stats every 30 seconds
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const data = await api.getDashboardStats();
      setStats(data);
    } catch (err) {
      console.error("Failed to load dashboard stats:", err);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !stats) {
    return null;
  }

  return (
    <div className="dashboard-stats">
      <div className="stat-card stat-card-leads">
        <div className="stat-icon">📊</div>
        <div className="stat-content">
          <div className="stat-value">{stats.total_leads.toLocaleString()}</div>
          <div className="stat-label">New Total Leads</div>
        </div>
      </div>

      <div className="stat-card stat-card-emails">
        <div className="stat-icon">📧</div>
        <div className="stat-content">
          <div className="stat-value">
            {stats.total_emails.toLocaleString()}
          </div>
          <div className="stat-label">Email Addresses</div>
          <div className="stat-coverage">{stats.email_coverage}% coverage</div>
        </div>
      </div>

      <div className="stat-card stat-card-websites">
        <div className="stat-icon">🌐</div>
        <div className="stat-content">
          <div className="stat-value">
            {stats.total_websites.toLocaleString()}
          </div>
          <div className="stat-label">Websites</div>
          <div className="stat-coverage">
            {stats.website_coverage}% coverage
          </div>
        </div>
      </div>

      <div className="stat-card stat-card-runs">
        <div className="stat-icon">🚀</div>
        <div className="stat-content">
          <div className="stat-value">{stats.total_runs.toLocaleString()}</div>
          <div className="stat-label">Total Runs</div>
          <div className="stat-recent">{stats.recent_runs} in last 7 days</div>
        </div>
      </div>
    </div>
  );
}
