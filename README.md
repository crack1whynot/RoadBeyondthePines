# Road Beyond the Pines Studio

Road Beyond the Pines Studio is a production-oriented AI-powered development environment for Unreal Engine 5.8. The repository now includes a working MVP foundation with a FastAPI backend, a Vite frontend, shared settings, logging, and placeholder managers for plugins, Unreal, Git, and tasks.

## What is included

- FastAPI backend with a live health endpoint at /health
- Vite + React + TypeScript frontend with backend connection status
- Application settings endpoint at /settings
- Logging and error handling in the API layer
- Runtime layer with service registry, event bus, command bus, task queue, worker, state manager, and plugin loader
- Orchestrator layer that executes explicit diagnostic/echo goals through the Runtime
- Brain layer that builds context and unique goals, plus `/brain/execute` for the Phase 0 handoff
- Memory layer for structured in-process knowledge with optional JSON persistence
- Provider-independent Agent System with registry, manager, factory, loader, lifecycle, and one real DiagnosticAgent
- Placeholder manager services for plugins, Unreal, Git, and tasks

## Run locally

#### One-click startup on Windows

Run this script from the project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_app.ps1
```

This will start:
- Backend on http://127.0.0.1:8000
- Frontend on http://127.0.0.1:5173

#### Backend

```powershell
cd c:\GameDevelopment\RoadBeyondthePinesStudio
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe" -m pip install -r requirements.txt
"C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\ThirdParty\Python3\Win64\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd c:\GameDevelopment\RoadBeyondthePinesStudio\frontend
npm install
npm run dev
```

### Verify the MVP

- Open http://127.0.0.1:5173 to view the UI.
- The UI will display backend connectivity and application settings.
- The backend health endpoint is available at http://127.0.0.1:8000/health.
- The settings endpoint is available at http://127.0.0.1:8000/settings.

## Status

The project is an MVP foundation with a truthful local execution pipeline for
explicit diagnostic/echo requests. It does not yet generate gameplay systems,
control a live Unreal Editor, use a real AI provider, or automate Git/build
work. See `docs/EXECUTION_PIPELINE.md` for the current execution boundary.
