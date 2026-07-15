# Runtime Layer

The runtime layer is the core orchestration component of Road Beyond the Pines Studio. It provides an in-process foundation for services, events, commands, jobs, worker execution, plugin loading, and shared application state.

## Components

- Service Registry: registers, resolves, and lists runtime services.
- Event Bus: subscribes, unsubscribes, and publishes domain events.
- Command Bus: dispatches commands with middleware support and handler registration.
- Task Queue: supports prioritization, progress tracking, cancellation, and retries.
- Worker: executes queued jobs in a background thread with graceful shutdown support.
- State Manager: manages shared runtime state and persistence hooks.
- Plugin Loader: loads, unloads, and reloads plugins with metadata management.

## Initialization

The runtime initializes automatically during backend startup through the dependency injection container in the application entrypoint.

## Future extension points

- Introduce durable persistence for state and job history.
- Add plugin discovery from disk.
- Connect the runtime to concrete Unreal and AI orchestration services.
