# Web Display Rotator - AI Implementation PRD

## Executive Summary

The Super Simple Kiosk application is a Flask-based web service that provides automated fullscreen web content display with MQTT-based remote control capabilities. This system is designed for simple digital signage management, enabling intelligent content orchestration through message queue integration and RESTful API control.

## Implementation Context

This application serves as a display endpoint.

### Integration Points
- **MQTT Command Interface**: Real-time display control
- **REST API**: Programmatic configuration and status monitoring
- **Event-Driven Architecture**: Reactive display management
- **Stateful Operation**: Persistent display state

## Technical Architecture

### Core Components
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   MQTT Broker   │────│  Flask Web App   │────│   Chromium      │
│                 │    │                  │    │   (Fullscreen)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                       ┌──────────────────┐
                       │  Configuration   │
                       │  (YAML + State)  │
                       └──────────────────┘
```

### Technology Stack
- **Web Framework**: Flask (Python)
- **Message Queue**: MQTT Client (paho-mqtt)
- **Browser Control**: Selenium WebDriver
- **Configuration**: YAML + JSON state management
- **Threading**: Background rotation + MQTT monitoring
- **HTTP API**: RESTful endpoints for external control

## Functional Requirements

### 1. Flask Web Application Framework

#### 1.1 Web Service Architecture
- **Description**: Implement core functionality as a Flask web service
- **Implementation Requirements**:
  - Flask application with proper route structure
  - Background thread management for display rotation
  - Thread-safe state management
  - Graceful shutdown handling
  - WSGI compatibility for production deployment

#### 1.2 RESTful API Endpoints
```python
# Configuration Management
GET / api / config  # Get current configuration
PUT / api / config  # Update configuration
POST / api / config / reload  # Reload from file

# Display Control
GET / api / status  # Get current display status
POST / api / control / pause  # Pause rotation
POST / api / control / resume  # Resume rotation
POST / api / control / jump / {index}  # Jump to URL index
POST / api / control / next  # Skip to next URL

# URL Management
GET / api / urls  # List all URLs
POST / api / urls  # Add new URL
PUT / api / urls / {index}  # Update URL at index
DELETE / api / urls / {index}  # Remove URL at index

# System Management
GET / api / health  # Health check endpoint
POST / api / system / restart  # Restart display system
```

### 2. MQTT Integration

#### 2.1 MQTT Client Configuration
```yaml
mqtt:
  broker: "localhost"              # MQTT broker address
  port: 1883                       # MQTT broker port
  username: null                   # Optional authentication
  password: null
  client_id: "web_rotator_001"     # Unique client identifier
  topics:
    commands: "displays/commands"   # Command topic
    status: "displays/status"       # Status reporting topic
    config: "displays/config"       # Configuration updates
```

#### 2.2 MQTT Command Protocol
```json
// Pause rotation
{
  "command": "pause",
  "timestamp": "2025-07-27T10:30:00Z",
  "device_id": "display_001"
}

// Resume rotation
{
  "command": "resume",
  "timestamp": "2025-07-27T10:31:00Z",
  "device_id": "display_001"
}

// Jump to specific URL
{
  "command": "jump",
  "index": 2,
  "timestamp": "2025-07-27T10:32:00Z",
  "device_id": "display_001"
}

// Update configuration
{
  "command": "update_config",
  "config": {
    "default_duration": 45,
    "urls": [...]
  },
  "timestamp": "2025-07-27T10:33:00Z",
  "device_id": "display_001"
}

// Add URL dynamically
{
  "command": "add_url",
  "url": "https://example.com",
  "duration": 30,
  "index": null,  // null = append, number = insert at index
  "timestamp": "2025-07-27T10:34:00Z",
  "device_id": "display_001"
}
```

#### 2.3 MQTT Status Reporting
```json
// Regular status updates (every 30 seconds)
{
  "device_id": "display_001",
  "status": "running",           // running, paused, error
  "current_url": "https://example.com",
  "current_index": 1,
  "total_urls": 5,
  "remaining_time": 25,          // seconds
  "last_error": null,
  "uptime": 3600,                // seconds
  "timestamp": "2025-07-27T10:35:00Z"
}

// Error reporting
{
  "device_id": "display_001",
  "status": "error",
  "error_type": "url_unreachable",
  "error_message": "Failed to load https://broken.com after 3 retries",
  "current_url": "https://broken.com",
  "timestamp": "2025-07-27T10:36:00Z"
}
```

### 3. Enhanced State Management

#### 3.1 Persistent State Storage
```python
# State structure stored as JSON
{
    "current_index": 2,
    "is_paused": false,
    "rotation_start_time": "2025-07-27T09:00:00Z",
    "total_rotations": 147,
    "error_count": 3,
    "last_config_update": "2025-07-27T08:30:00Z",
    "device_info": {
        "hostname": "display-kiosk-01",
        "version": "1.0.0",
        "chromium_version": "120.0.6099.109",
    },
}
```

#### 3.2 Configuration Validation
- JSON Schema validation for MQTT commands
- YAML configuration syntax validation
- URL format and reachability validation
- Duration value range validation (1-86400 seconds)

### 4. Advanced Display Management

#### 4.2 Intelligent Error Handling
- Exponential backoff for failed URLs
- Circuit breaker pattern for repeatedly failing URLs
- Automatic URL health monitoring
- Fallback content for extended outages

## Implementation Specifications

### Flask Application Structure
```
app/
├── __init__.py              # Flask app factory
├── models/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   └── display_state.py    # State management
├── services/
│   ├── __init__.py
│   ├── display_manager.py  # Core display logic
│   ├── mqtt_client.py      # MQTT integration
│   └── browser_manager.py  # Chromium control
├── api/
│   ├── __init__.py
│   ├── routes.py           # REST API endpoints
│   └── schemas.py          # Request/response schemas
├── utils/
│   ├── __init__.py
│   ├── validators.py       # Input validation
│   └── logging.py          # Logging configuration
└── main.py                 # Application entry point
```

### Key Implementation Classes

.. blacken-docs:off
```python  #
class DisplayManager:
    """Core display rotation management"""
    def __init__(self, config_manager, mqtt_client)
    def start_rotation(self)
    def pause_rotation(self)
    def resume_rotation(self)
    def jump_to_url(self, index)
    def add_url(self, url_config)
    def remove_url(self, index)
    def get_status(self)

class MQTTClient:
    """MQTT message handling"""
    def __init__(self, config, display_manager)
    def connect(self)
    def subscribe_to_commands(self)
    def publish_status(self, status)
    def handle_command(self, topic, payload)

class ConfigManager:
    """Configuration and state management"""
    def __init__(self, config_file, state_file)
    def load_config(self)
    def save_config(self, config)
    def validate_config(self, config)
    def get_state(self)
    def update_state(self, state_update)
```
.. blacken-docs:on

### MQTT Integration Requirements

#### Message Queue Monitoring
- Continuous MQTT connection with automatic reconnection
- Message acknowledgment and error handling
- Command validation and sanitization
- Rate limiting for command processing

#### Status Reporting
- Periodic status broadcasts (configurable interval)
- Event-driven status updates (errors, state changes)
- Heartbeat messages for connection monitoring
- Performance metrics reporting

### Production Deployment

#### Docker Configuration
```dockerfile
FROM python:3.9-slim
RUN apt-get update && apt-get install -y chromium-browser chromium-driver
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ /app/
WORKDIR /app
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "main:app"]
```

#### Environment Variables
```bash
FLASK_ENV=production
DISPLAY_CONFIG_FILE=/config/urls.yaml
DISPLAY_STATE_FILE=/data/state.json
MQTT_BROKER=mqtt.company.com
MQTT_PORT=1883
MQTT_USERNAME=display_client
MQTT_PASSWORD=secure_password
DEVICE_ID=display_001
LOG_LEVEL=INFO
```

## Testing Requirements

### Unit Testing
- Flask route testing with test client
- MQTT message handling simulation
- Configuration validation testing
- State management persistence testing

### Integration Testing
- End-to-end MQTT command processing
- Browser automation reliability testing
- Multi-threaded operation stability
- Configuration reload without service interruption

## Security Considerations

### MQTT Security
- Topic-based access control
- Command payload validation and sanitization

### Web API Security
- API key authentication for REST endpoints
- Rate limiting to prevent abuse
- Input validation and sanitization
- CORS configuration for web interface access

### System Security
- Non-privileged user execution
- File system permission restrictions
- Network access limitations
- Audit logging for security events

## Monitoring and Observability

### Application Metrics
- Display rotation statistics
- MQTT message processing rates
- Error rates and types
- Performance indicators (memory, CPU)

### Health Check Integration
- HTTP health endpoint for load balancers
- MQTT connectivity status
- Browser process health monitoring
- Configuration validity checking

### Logging Strategy
- Structured JSON logging
- Configurable log levels
- Centralized log aggregation support
- Error tracking and alerting integration

## Success Criteria for AI Implementation

### Technical Metrics
- **MQTT Response Time**: <500ms for command processing
- **API Response Time**: <200ms for REST endpoints
- **Uptime**: >99.9% availability during operation
- **Command Success Rate**: >99% for valid MQTT commands
