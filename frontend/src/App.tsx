import { useState, useEffect, useCallback } from "react";
import { RunForm } from "./components/RunForm";
import { RunsList } from "./components/RunsList";
import { LeadsTable } from "./components/LeadsTable";
import { DashboardStatsComponent } from "./components/DashboardStats";
import { api } from "./api/client";
import type { Run } from "./api/client";
import "./App.css";

function App() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [allRuns, setAllRuns] = useState<Run[]>([]);
  const [loadingRuns, setLoadingRuns] = useState(true);

  const loadAllRuns = useCallback(async () => {
    try {
      setLoadingRuns(true);
      const data = await api.getRuns();
      setAllRuns(data);
    } catch (err) {
      console.error("Failed to load runs in App:", err);
    } finally {
      setLoadingRuns(false);
    }
  }, []);

  useEffect(() => {
    loadAllRuns();
  }, [refreshTrigger, loadAllRuns]);

  const handleRunCreated = () => {
    // Trigger refresh of runs list
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleSelectRun = (runId: string) => {
    setSelectedRunId(runId);
  };
  const handleCloseLeads = () => {
    setSelectedRunId(null);
    // Refresh runs to get updated counts
    setRefreshTrigger((prev) => prev + 1);
  };

  const handleRefresh = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  return (
    <div className="app">
      <div className="container">
        {!selectedRunId && (
          <header className="header">
            <h1 className="text-gradient">LeadGen Pipeline</h1>
            <p>
              Agentic lead generation & enrichment with intelligent outreach
            </p>
          </header>
        )}
        {!selectedRunId && <DashboardStatsComponent />}

        {!selectedRunId && allRuns.some((r) => r.is_pinned) && (
          <div className="pinned-runs-section">
            <RunsList
              runs={allRuns.filter((r) => r.is_pinned)}
              onSelectRun={handleSelectRun}
              onRefresh={handleRefresh}
              onlyPinned={true}
              title="Pinned Runs"
              loading={loadingRuns}
            />
          </div>
        )}

        <div className="main-content">
          {!selectedRunId ? (
            <>
              <RunForm onRunCreated={handleRunCreated} />
              <div className="mt-md">
                <RunsList
                  runs={allRuns.filter((r) => !r.is_pinned)}
                  onSelectRun={handleSelectRun}
                  onRefresh={handleRefresh}
                  loading={loadingRuns}
                />
              </div>
            </>
          ) : (
            <LeadsTable runId={selectedRunId} onClose={handleCloseLeads} />
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
