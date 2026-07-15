# Architecture Overview

This document outlines the production-oriented architecture scaffold for Road Beyond the Pines Studio.

## Layers

- Frontend: React, TypeScript, Vite, TailwindCSS, shadcn/ui
- Backend: FastAPI, SQLAlchemy, Pydantic, WebSockets
- Brain: provider-independent reasoning and goal creation
- Orchestrator: planning and coordination above the runtime
- Runtime: execution backbone for services and jobs
- Memory: persistent, structured project knowledge and snapshots
- Agent System: provider-independent execution framework with registry, manager, lifecycle, and capability-based dispatch
- Shared: contracts and schema definitions
- Documentation: architecture and implementation notes

## Principles

- Replaceable AI provider abstraction
- Replaceable Unreal MCP integration
- Modular service and agent layers
- Dependency injection friendly structure
- SQLite-first database path

## Next Implementation Steps

1. Introduce concrete persistence models and migrations.
2. Implement provider adapters and MCP client wrappers.
3. Wire websocket channels and real-time state updates.
4. Expand the frontend into dashboards and workflows.
5. Connect the Brain output to richer planner strategies and domain-specific reasoning.
