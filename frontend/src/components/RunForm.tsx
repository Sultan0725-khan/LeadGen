import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { CreateRunRequest, Provider } from "../api/client";
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

  // Provider selection
  const [providers, setProviders] = useState<Provider[]>([]);
  const [selectedProviders, setSelectedProviders] = useState<string[]>([]);
  const [providerLimits, setProviderLimits] = useState<Record<string, number>>(
    {},
  );
  const [loadingProviders, setLoadingProviders] = useState(true);

  // Load providers on mount and refresh periodically
  useEffect(() => {
    loadProviders();
    // Refresh providers every 60 seconds to update quotas
    const interval = setInterval(loadProviders, 60000);
    return () => clearInterval(interval);
  }, []);

  const loadProviders = async () => {
    try {
      const data = await api.getProviders();
      setProviders(data);

      // Auto-select enabled providers with available quota
      const availableProviders = data.filter(
        (p) => p.enabled && p.quota_available > 0,
      );
      setSelectedProviders(availableProviders.map((p) => p.id));

      // Set default limits for all providers
      const defaultLimits: Record<string, number> = {};
      data.forEach((p) => {
        if (!providerLimits[p.id]) {
          defaultLimits[p.id] = p.query_limit;
        }
      });
      setProviderLimits((prev) => ({ ...defaultLimits, ...prev }));
    } catch (err) {
      console.error("Failed to load providers:", err);
    } finally {
      setLoadingProviders(false);
    }
  };

  const toggleProvider = (providerId: string) => {
    setSelectedProviders((prev) =>
      prev.includes(providerId)
        ? prev.filter((id) => id !== providerId)
        : [...prev, providerId],
    );
  };

  const updateProviderLimit = (providerId: string, limit: number) => {
    setProviderLimits((prev) => ({
      ...prev,
      [providerId]: limit,
    }));
  };

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
        providers: selectedProviders.length > 0 ? selectedProviders : undefined,
        provider_limits: providerLimits,
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

  const getQuotaPercentage = (provider: Provider) => {
    if (provider.quota_limit === 0) return 0; // Unlimited
    return Math.round((provider.quota_used / provider.quota_limit) * 100);
  };

  const getQuotaColor = (percentage: number) => {
    if (percentage >= 90) return "#f5576c";
    if (percentage >= 70) return "#ffa726";
    return "#43e97b";
  };

  return (
    <div className="card run-form">
      <h2 className="text-gradient">Start New Lead Generation Run</h2>

      {error && <div className="alert alert-error">{error}</div>}

      <form onSubmit={handleSubmit} className="form">
        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="location">Location</label>
            <input
              id="location"
              type="text"
              className="input"
              placeholder="e.g., Berlin, Mitte"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              required
            />
            <small>City, district, or region</small>
          </div>

          <div className="form-group">
            <label htmlFor="category">Category</label>
            <input
              id="category"
              type="text"
              className="input"
              placeholder="e.g., restaurant, café"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              required
            />
            <small>Business type or industry</small>
          </div>
        </div>

        {/* Provider Selection */}
        <div className="form-group">
          <label>Select Data Sources</label>
          {loadingProviders ? (
            <p style={{ fontSize: "0.9rem", opacity: 0.7 }}>
              Loading providers...
            </p>
          ) : (
            <div className="providers-grid">
              {providers.map((provider) => {
                const isQuotaExceeded =
                  provider.quota_available <= 0 && provider.quota_limit > 0;
                const quotaPercentage = getQuotaPercentage(provider);
                const quotaColor = getQuotaColor(quotaPercentage);

                return (
                  <div
                    key={provider.id}
                    className={`provider-card ${
                      isQuotaExceeded ? "provider-card-disabled" : ""
                    } ${
                      selectedProviders.includes(provider.id)
                        ? "provider-card-selected"
                        : ""
                    }`}
                  >
                    <div className="provider-card-header">
                      <div className="provider-card-title">
                        {!isQuotaExceeded && (
                          <input
                            type="checkbox"
                            checked={selectedProviders.includes(provider.id)}
                            onChange={() => toggleProvider(provider.id)}
                            disabled={!provider.enabled || isQuotaExceeded}
                          />
                        )}
                        <span className="provider-name">{provider.name}</span>
                      </div>
                      <div className="provider-badges">
                        {provider.free_tier && (
                          <span className="badge badge-success">FREE</span>
                        )}
                        {!provider.enabled && (
                          <span className="badge badge-info">Disabled</span>
                        )}
                      </div>
                    </div>

                    <div className="provider-card-description">
                      {provider.description}
                    </div>

                    {/* Quota Display */}
                    {provider.quota_limit > 0 && (
                      <div className="provider-quota">
                        <div className="provider-quota-text">
                          <span>
                            {provider.quota_used.toLocaleString()} /{" "}
                            {provider.quota_limit.toLocaleString()}
                          </span>
                          <span className="provider-quota-period">
                            {provider.quota_period}
                          </span>
                        </div>
                        <div className="provider-quota-bar">
                          <div
                            className="provider-quota-fill"
                            style={{
                              width: `${Math.min(quotaPercentage, 100)}%`,
                              backgroundColor: quotaColor,
                            }}
                          />
                        </div>
                      </div>
                    )}

                    {/* Quota Exceeded Message */}
                    {isQuotaExceeded && (
                      <div className="provider-quota-exceeded">
                        ⚠️ Free Limit Reached
                      </div>
                    )}

                    {/* WHERE Limit Input */}
                    {!isQuotaExceeded && provider.enabled && (
                      <div className="provider-limit-input">
                        <label>
                          WHERE Limit:
                          <input
                            type="number"
                            min="1"
                            max="1000"
                            value={
                              providerLimits[provider.id] ||
                              provider.query_limit
                            }
                            onChange={(e) =>
                              updateProviderLimit(
                                provider.id,
                                parseInt(e.target.value) ||
                                  provider.query_limit,
                              )
                            }
                          />
                        </label>
                        <small>Max records to fetch</small>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
          <small>Choose which sources to query for lead data</small>
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
