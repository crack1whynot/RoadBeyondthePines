import { useEffect, useState } from 'react';

import { apiClient, type HealthResponse, type SettingsResponse } from './services/api';

const App = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadStudioData = async () => {
      try {
        const [healthResponse, settingsResponse] = await Promise.all([apiClient.getHealth(), apiClient.getSettings()]);
        setHealth(healthResponse);
        setSettings(settingsResponse);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to connect to backend');
      } finally {
        setLoading(false);
      }
    };

    void loadStudioData();
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <section className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-24">
        <p className="text-sm uppercase tracking-[0.3em] text-cyan-400">Road Beyond the Pines Studio</p>
        <h1 className="text-4xl font-semibold sm:text-6xl">AI-powered Unreal Engine development environment</h1>
        <p className="max-w-3xl text-lg text-slate-400">
          The MVP now includes a live backend connection check, settings, logging hooks, and placeholder managers for
          plugins, Unreal, Git, and tasks.
        </p>

        <div className="grid gap-4 rounded-2xl border border-slate-800 bg-slate-900/80 p-6 shadow-2xl shadow-slate-950/50 md:grid-cols-2">
          <div>
            <h2 className="text-lg font-semibold">Backend status</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-300">
              {loading && <p>Checking connection…</p>}
              {error && <p className="text-rose-400">{error}</p>}
              {!loading && !error && health && (
                <>
                  <p className="font-medium text-emerald-400">Connected</p>
                  <p>Service: {health.service}</p>
                  <p>Environment: {health.environment}</p>
                  <p>Timestamp: {health.timestamp}</p>
                </>
              )}
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold">Application settings</h2>
            <div className="mt-3 space-y-2 text-sm text-slate-300">
              {settings ? (
                <>
                  <p>Name: {settings.app_name}</p>
                  <p>Environment: {settings.app_env}</p>
                  <p>Debug: {settings.app_debug ? 'Enabled' : 'Disabled'}</p>
                  <p>Log level: {settings.log_level}</p>
                  <p>AI provider: {settings.ai_provider}</p>
                </>
              ) : (
                <p>Settings unavailable.</p>
              )}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
};

export default App;
