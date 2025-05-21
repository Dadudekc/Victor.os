# System Architecture Diagrams

## Core Components

```mermaid
graph TD
    A[Agent Loop] --> B[Action Queue]
    B --> C[Tool Executor]
    C --> D[State Manager]
    D --> E[Recovery System]
    E --> A
    
    F[Discord Bot] --> G[Command Handler]
    G --> H[Task Manager]
    H --> I[Agent Controller]
    I --> A
```

## Data Flow

```mermaid
sequenceDiagram
    participant A as Agent
    participant Q as Queue
    participant T as Tools
    participant S as State
    
    A->>Q: Queue Action
    Q->>T: Execute
    T->>S: Update State
    S->>A: Continue
```

## Recovery Flow

```mermaid
graph LR
    A[Stop Detected] --> B[Reset Cycle]
    B --> C[Load State]
    C --> D[Queue Action]
    D --> E[Continue]
```

## Notes
- All components operate non-blockingly
- State is maintained continuously
- Recovery is automatic
- No human input required 