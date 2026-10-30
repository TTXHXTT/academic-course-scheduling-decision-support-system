/**
 * ACS API Client and Auth Management
 */

const API = {
  // Auth helpers
  getToken() {
    return localStorage.getItem("acs_token");
  },

  getUser() {
    const raw = localStorage.getItem("acs_user");
    return raw ? JSON.parse(raw) : null;
  },

  setAuth(token, user) {
    localStorage.setItem("acs_token", token);
    localStorage.setItem("acs_user", JSON.stringify(user));
  },

  logout() {
    localStorage.removeItem("acs_token");
    localStorage.removeItem("acs_user");
    window.location.href = "/login";
  },

  requireAuth() {
    const token = this.getToken();
    if (!token) {
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
      return null;
    }
    return this.getUser();
  },

  async request(endpoint, options = {}) {
    const token = this.getToken();
    const headers = { ...options.headers };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (options.body && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    try {
      const response = await fetch(endpoint, {
        ...options,
        headers,
      });

      if (response.status === 401) {
        this.logout();
        throw new Error("Session expired. Please log in again.");
      }

      if (response.status === 204) {
        return null;
      }

      const data = await response.json();
      if (!response.ok) {
        const errorMsg = data.detail || (Array.isArray(data) ? JSON.stringify(data) : "Request failed");
        throw new Error(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg));
      }
      return data;
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  },

  // Auth endpoints
  async login(email, password) {
    const data = await this.request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.setAuth(data.access_token, data.user);
    return data;
  },

  async getMe() {
    return await this.request("/api/auth/me");
  },

  // Datasets
  async getDatasets() {
    return await this.request("/api/datasets");
  },

  async getDataset(id) {
    return await this.request(`/api/datasets/${id}`);
  },

  async uploadDataset(formData) {
    return await this.request("/api/datasets/upload", {
      method: "POST",
      body: formData,
    });
  },

  async deleteDataset(id) {
    return await this.request(`/api/datasets/${id}`, {
      method: "DELETE",
    });
  },

  // Records / Explorer
  async queryRecords(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return await this.request(`/api/records?${qs}`);
  },

  async getRecordFilterOptions(datasetId) {
    const qs = datasetId ? `?dataset_id=${datasetId}` : "";
    return await this.request(`/api/records/filter-options${qs}`);
  },

  // Analysis
  async getAnalysisRuns(datasetId) {
    const qs = datasetId ? `?dataset_id=${datasetId}` : "";
    return await this.request(`/api/analysis${qs}`);
  },

  async getAnalysisRun(id) {
    return await this.request(`/api/analysis/${id}`);
  },

  async runAnalysis(data) {
    return await this.request("/api/analysis/run", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async getCourseMetrics(analysisId, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return await this.request(`/api/analysis/${analysisId}/courses?${qs}`);
  },

  // Recommendations
  async getRecommendations(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return await this.request(`/api/recommendations?${qs}`);
  },

  async updateRecommendationStatus(id, status, notes = "") {
    return await this.request(`/api/recommendations/${id}/status`, {
      method: "PUT",
      body: JSON.stringify({ action_status: status, decision_notes: notes }),
    });
  },

  // Scenarios
  async getScenarios(analysisId) {
    const qs = analysisId ? `?baseline_analysis_id=${analysisId}` : "";
    return await this.request(`/api/scenarios${qs}`);
  },

  async getScenario(id) {
    return await this.request(`/api/scenarios/${id}`);
  },

  async createScenario(data) {
    return await this.request("/api/scenarios", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Audit
  async getAuditLogs(params = {}) {
    const qs = new URLSearchParams(params).toString();
    return await this.request(`/api/audit?${qs}`);
  },
};

// UI notification helper
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container") || createToastContainer();
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.style.cssText = `
    background: ${type === "error" ? "#b91c1c" : type === "success" ? "#15803d" : "#0369a1"};
    color: white;
    padding: 0.75rem 1rem;
    border-radius: 6px;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
    opacity: 0;
    transition: opacity 0.2s ease-in-out;
  `;
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => toast.style.opacity = "1", 10);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}

function createToastContainer() {
  const container = document.createElement("div");
  container.id = "toast-container";
  container.style.cssText = `
    position: fixed;
    bottom: 1.5rem;
    right: 1.5rem;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    max-width: 360px;
  `;
  document.body.appendChild(container);
  return container;
}

// User state initialization
document.addEventListener("DOMContentLoaded", () => {
  const user = API.getUser();
  if (user) {
    const userRoleEl = document.getElementById("user-role-display");
    const userNameEl = document.getElementById("user-name-display");
    if (userRoleEl) userRoleEl.textContent = user.role.replace("_", " ").toUpperCase();
    if (userNameEl) userNameEl.textContent = user.full_name;

    // RBAC: Show/Hide based on role
    if (user.role === "student") {
      document.querySelectorAll(".admin-only, .scheduler-only, .chair-only").forEach(el => el.style.display = "none");
    } else if (user.role === "program_coordinator") {
      document.querySelectorAll(".admin-only, .scheduler-only").forEach(el => el.style.display = "none");
    } else if (user.role === "academic_scheduler") {
      document.querySelectorAll(".chair-only").forEach(el => el.style.display = "none");
    }
  }
});
