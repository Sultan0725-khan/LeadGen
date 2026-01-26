const API_BASE_URL = "http://localhost:8000/api";

export interface Run {
  id: string;
  status: string;
  location: string;
  category: string;
  require_approval: boolean;
  dry_run: boolean;
  total_leads: number;
  total_emails?: number;
  total_websites?: number;
  selected_providers?: string[];
  provider_limits?: Record<string, number>;
  error_message?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface Lead {
  id: string;
  run_id: string;
  business_name: string;
  address?: string;
  website?: string;
  email?: string;
  phone?: string;
  latitude?: number;
  longitude?: number;
  confidence_score: number;
  sources: string[];
  enrichment_data: Record<string, unknown>;
  notes?: string;
  created_at: string;
  email_status?: string;
  email_id?: string;
}

export interface Email {
  id: string;
  lead_id: string;
  status: string;
  subject: string;
  body: string;
  language: string;
  generated_at: string;
  sent_at?: string;
  error_message?: string;
}

export interface Provider {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  requires_api_key: boolean;
  free_tier: boolean;
  daily_limit: string;
  quota_limit: number;
  quota_used: number;
  quota_period: string;
  quota_available: number;
  query_limit: number;
  statistics_url?: string;
}

export interface CreateRunRequest {
  location: string;
  category: string;
  require_approval: boolean;
  dry_run: boolean;
  providers?: string[]; // Optional list of provider IDs
  provider_limits?: Record<string, number>; // Dict of provider_id -> query limit
}

export interface DashboardStats {
  total_leads: number;
  total_emails: number;
  total_websites: number;
  total_runs: number;
  recent_runs: number;
  email_coverage: number;
  website_coverage: number;
}

export const api = {
  // Runs
  async createRun(data: CreateRunRequest): Promise<Run> {
    const response = await fetch(`${API_BASE_URL}/runs/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error("Failed to create run");
    return response.json();
  },

  async getRuns(): Promise<Run[]> {
    const response = await fetch(`${API_BASE_URL}/runs/`);
    if (!response.ok) throw new Error("Failed to fetch runs");
    return response.json();
  },

  async getRun(runId: string): Promise<Run> {
    const response = await fetch(`${API_BASE_URL}/runs/${runId}`);
    if (!response.ok) throw new Error("Failed to fetch run");
    return response.json();
  },

  async deleteRun(runId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/runs/${runId}`, {
      method: "DELETE",
    });
    if (!response.ok) throw new Error("Failed to delete run");
  },

  // Leads
  async getLeads(
    runId: string,
    page = 1,
    per_page = 50,
    filters?: {
      has_email?: boolean;
      has_website?: boolean;
      email_status?: string;
    },
  ): Promise<{ leads: Lead[]; total: number }> {
    let url = `${API_BASE_URL}/leads/run/${runId}?page=${page}&per_page=${per_page}`;
    if (filters?.has_email !== undefined)
      url += `&has_email=${filters.has_email}`;
    if (filters?.has_website !== undefined)
      url += `&has_website=${filters.has_website}`;
    if (filters?.email_status !== undefined)
      url += `&email_status=${filters.email_status}`;

    const response = await fetch(url);
    if (!response.ok) throw new Error("Failed to fetch leads");
    return response.json();
  },

  // Emails
  async draftEmails(
    leadIds: string[],
    language = "DE",
  ): Promise<{ drafted_count: number }> {
    const response = await fetch(`${API_BASE_URL}/emails/draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lead_ids: leadIds, language }),
    });
    if (!response.ok) throw new Error("Failed to draft emails");
    return response.json();
  },

  async getEmail(emailId: string): Promise<Email> {
    const response = await fetch(`${API_BASE_URL}/emails/${emailId}`);
    if (!response.ok) throw new Error("Failed to fetch email");
    return response.json();
  },

  async updateEmail(
    emailId: string,
    data: { subject: string; body: string },
  ): Promise<Email> {
    const response = await fetch(`${API_BASE_URL}/emails/${emailId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error("Failed to update email");
    return response.json();
  },

  async sendEmail(emailId: string): Promise<{ status: string }> {
    const response = await fetch(`${API_BASE_URL}/emails/${emailId}/send`, {
      method: "POST",
    });
    if (!response.ok) throw new Error("Failed to send email");
    return response.json();
  },

  async approveEmail(emailId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/emails/${emailId}/approve`, {
      method: "POST",
    });
    if (!response.ok) throw new Error("Failed to approve email");
  },

  async suppressEmail(emailId: string): Promise<void> {
    const response = await fetch(`${API_BASE_URL}/emails/${emailId}/suppress`, {
      method: "POST",
    });
    if (!response.ok) throw new Error("Failed to suppress email");
  },

  // Export
  exportCSV(runId: string): string {
    return `${API_BASE_URL}/export/run/${runId}/csv`;
  },

  async getLogs(runId: string): Promise<Record<string, unknown>[]> {
    const response = await fetch(`${API_BASE_URL}/export/run/${runId}/logs`);
    if (!response.ok) throw new Error("Failed to fetch logs");
    return response.json();
  },

  // Providers
  async getProviders(): Promise<Provider[]> {
    const response = await fetch(`${API_BASE_URL}/providers/`);
    if (!response.ok) throw new Error("Failed to fetch providers");
    return response.json();
  },

  // Statistics
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await fetch(`${API_BASE_URL}/stats/dashboard`);
    if (!response.ok) throw new Error("Failed to fetch dashboard stats");
    return response.json();
  },

  async getProviderStats(providerId: string): Promise<Record<string, unknown>> {
    const response = await fetch(
      `${API_BASE_URL}/stats/providers/${providerId}`,
    );
    if (!response.ok) throw new Error("Failed to fetch provider stats");
    return response.json();
  },

  async refreshProviderStats(
    providerId: string,
  ): Promise<Record<string, unknown>> {
    const response = await fetch(
      `${API_BASE_URL}/stats/providers/${providerId}/refresh`,
      {
        method: "POST",
      },
    );
    if (!response.ok) throw new Error("Failed to refresh provider stats");
    return response.json();
  },

  async patch(
    url: string,
    data: Record<string, unknown>,
  ): Promise<Record<string, unknown>> {
    const response = await fetch(`${API_BASE_URL}${url}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error(`Failed to patch ${url}`);
    return response.json();
  },

  async sendToSalesforce(leadIds: string[]): Promise<{
    results: {
      lead_id: string;
      success: boolean;
      error?: string;
      salesforce_id?: string;
      status?: string;
    }[];
  }> {
    const response = await fetch(`${API_BASE_URL}/salesforce/send-leads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lead_ids: leadIds }),
    });
    if (!response.ok) throw new Error("Failed to send leads to Salesforce");
    return response.json();
  },
};
