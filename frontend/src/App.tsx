import { useState } from "react";
import { RunForm } from "./components/RunForm";
import { RunsList } from "./components/RunsList";
import { LeadsTable } from "./components/LeadsTable";
import { DashboardStatsComponent } from "./components/DashboardStats";
import "./App.css";

function App() {
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

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

  return (
    <div className="app">
      <div className="container">
        <header className="header">
          <h1 className="text-gradient">LeadGen Pipeline</h1>
          <p>Agentic lead generation & enrichment with intelligent outreach</p>
        </header>

        <DashboardStatsComponent />

        <div className="main-content">
          {!selectedRunId ? (
            <>
              <RunForm onRunCreated={handleRunCreated} />
              <div className="mt-md">
                <RunsList
                  refreshTrigger={refreshTrigger}
                  onSelectRun={handleSelectRun}
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
