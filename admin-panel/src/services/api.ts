/**
 * API client for Claude Self-Reflect Admin Panel
 */

// Try to get API URL from runtime config (set by start-admin.sh)
// Otherwise fallback to env var or default
const getApiUrl = () => {
  if (typeof window !== 'undefined' && (window as any).ADMIN_CONFIG?.API_URL) {
    return (window as any).ADMIN_CONFIG.API_URL;
  }
  return import.meta.env.VITE_API_URL || 'http://localhost:8003/api';
};

//const API_BASE_URL = getApiUrl();
const API_BASE_URL = "http://192.168.50.136:8003/api";

class ApiClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  // Dashboard endpoints
  async getDashboardMetrics() {
    return this.request('/dashboard/metrics');
  }

  async getSystemStats() {
    return this.request('/dashboard/stats');
  }

  // Projects endpoints
  async listProjects() {
    return this.request('/projects/');
  }

  async getProjectDetails(projectName: string) {
    return this.request(`/projects/${projectName}`);
  }

  // Imports endpoints
  async getImportStatus() {
    return this.request('/imports/status');
  }

  async listImportedFiles(project?: string, limit = 100) {
    const params = new URLSearchParams();
    if (project) params.append('project', project);
    params.append('limit', limit.toString());
    return this.request(`/imports/files?${params}`);
  }

  // Collections endpoints
  async listCollections() {
    return this.request('/collections/');
  }

  async getCollectionInfo(collectionName: string) {
    return this.request(`/collections/${collectionName}`);
  }

  // Settings endpoints
  async getEmbeddingConfig() {
    return this.request('/settings/embedding');
  }

  async updateEmbeddingMode(mode: 'local' | 'cloud') {
    return this.request('/settings/embedding/mode', {
      method: 'POST',
      body: JSON.stringify({ mode }),
    });
  }

  // Docker endpoints
  async listDockerServices() {
    return this.request('/docker/services');
  }

  async startService(serviceName: string) {
    return this.request(`/docker/services/${serviceName}/start`, {
      method: 'POST',
    });
  }

  async stopService(serviceName: string) {
    return this.request(`/docker/services/${serviceName}/stop`, {
      method: 'POST',
    });
  }

  // Logs endpoints
  async getMcpLogs(lines = 100) {
    return this.request(`/logs/mcp?lines=${lines}`);
  }

  async getDockerLogs(service: string, lines = 100) {
    return this.request(`/logs/docker/${service}?lines=${lines}`);
  }

  // Batch jobs endpoints
  async listBatchJobs(limit = 50) {
    return this.request(`/batch/jobs?limit=${limit}`);
  }

  async getBatchJob(jobId: string) {
    return this.request(`/batch/jobs/${jobId}`);
  }
}

export const api = new ApiClient(API_BASE_URL);
