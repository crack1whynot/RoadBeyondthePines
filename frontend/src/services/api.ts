const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export interface HealthResponse {
  status: string;
  service: string;
  environment: string;
  timestamp: string;
}

export interface SettingsResponse {
  app_name: string;
  app_env: string;
  app_debug: boolean;
  log_level: string;
  backend_host: string;
  backend_port: number;
  frontend_url: string;
  unreal_mcp_enabled: boolean;
  ai_provider: string;
}

export const apiClient = {
  async getHealth(): Promise<HealthResponse> {
    const response = await fetch(`${API_BASE_URL}/health`);
    if (!response.ok) {
      throw new Error('Unable to reach backend health endpoint');
    }
    return response.json();
  },

  async getSettings(): Promise<SettingsResponse> {
    const response = await fetch(`${API_BASE_URL}/settings`);
    if (!response.ok) {
      throw new Error('Unable to load application settings');
    }
    return response.json();
  },
};
