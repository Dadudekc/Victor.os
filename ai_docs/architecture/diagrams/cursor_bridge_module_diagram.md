# Cursor Bridge Module Diagram

```mermaid
graph TD
    subgraph "dreamos.integrations.cursor"
        A[bridge] --> B[bridge_loop.py]
        A --> C[http_bridge_service.py]
        A --> D[relay]
        A --> E[feedback]
        A --> F[schemas]
        
        subgraph "config"
            G[bridge_config.yaml]
        end
        
        subgraph "utils"
            H[cursor_injector.py]
        end
    end
    
    subgraph "External Dependencies"
        I[ChatGPTWebAgent]
        J[AppConfig]
        K[TaskNexus]
    end
    
    B --> I
    B --> J
    B --> K
    C --> H
    B --> H
    
    style A fill:#f9f,stroke:#333,stroke-width:2px
    style G fill:#bbf,stroke:#333,stroke-width:2px
    style H fill:#bfb,stroke:#333,stroke-width:2px
```

## Module Descriptions

### Core Components
- **bridge_loop.py**: Main orchestrator for the bridge functionality
- **http_bridge_service.py**: FastAPI service for HTTP-based bridge interactions
- **relay/**: Handles message relay between systems
- **feedback/**: Manages feedback mechanisms
- **schemas/**: Contains data structure definitions

### Configuration
- **bridge_config.yaml**: Primary configuration file for bridge settings

### Utilities
- **cursor_injector.py**: Handles Cursor IDE interaction via PyAutoGUI

### Dependencies
- **ChatGPTWebAgent**: Manages ChatGPT web UI interactions
- **AppConfig**: Application-wide configuration management
- **TaskNexus**: Task management and coordination

## Data Flow
1. Input prompts are received via HTTP or file system
2. Bridge loop processes prompts through ChatGPTWebAgent
3. Responses are captured and stored
4. Feedback and relay systems handle communication flow 