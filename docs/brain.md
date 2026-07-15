# Brain Layer

The Brain layer is the Studio's central reasoning component. It does not execute work, does not call the Runtime layer directly, and does not perform tasks. Its responsibility is to understand the project and turn a user request into a structured goal for the Planner.

## Responsibilities

- Understand user intent.
- Build project context from current project state.
- Read documentation, memory, and configuration.
- Create goals that describe what should happen.
- Pass goals onward to downstream planning layers.

## Design Principles

- Provider-independent.
- No fake AI or provider-specific implementations.
- Dependency injection throughout.
- Clear separation between understanding and execution.
