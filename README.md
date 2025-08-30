# Super Simple Kiosk

[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/UpDryTwist/super_simple_kiosk/graphs/commit-activity)
[![PyPI download month](https://img.shields.io/pypi/dm/.svg)](https://pypi.python.org/pypi//)
[![PyPI version fury.io](https://badge.fury.io/py/.svg)](https://pypi.python.org/pypi//)
[![Documentation Status](https://readthedocs.org/projects//badge/?version=latest)](http://.readthedocs.io/?badge=latest)
[![PR welcome issues still open](https://badgen.net/https/pr-welcome-badge.vercel.app/api/badge/UpDryTwist/)](https://github.com/UpDryTwist//issues?q=archived:false+is:issue+is:open+sort:updated-desc+label%3A%22help%20wanted%22%2C%22good%20first%20issue%22)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)
[![buymecoffee](https://img.shields.io/badge/-buy_me_a%C2%A0coffee-gray?logo=buy-me-a-coffee)](https://www.buymeacoffee.com/UpDryTwist)

A Flask-based web service that provides automated fullscreen web content display with MQTT-based remote control capabilities. This system is designed for simple digital signage management, enabling intelligent content orchestration through message queue integration and RESTful API control.

## Features

- **Automated Web Content Rotation**: Seamlessly rotate through multiple URLs in fullscreen mode
- **MQTT Remote Control**: Real-time control via MQTT commands (pause, resume, jump, etc.)
- **RESTful API**: Complete programmatic control and configuration management
- **Persistent State Management**: Maintains display state across restarts
- **Intelligent Error Handling**: Exponential backoff for failed URLs with circuit breaker pattern
- **Docker Deployment**: Containerized deployment with MQTT broker integration
- **Comprehensive Testing**: Full test suite with unit and integration tests

## Quick Start

### Using Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/UpDryTwist/super-simple-kiosk.git
cd super-simple-kiosk

# Start the application with Docker Compose
docker-compose up -d
```

The application will be available at `http://localhost:5000` and the MQTT broker at `localhost:1883`.

### Manual Installation

```bash
# Clone the repository
git clone https://github.com/UpDryTwist/super-simple-kiosk.git
cd super-simple-kiosk

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m super_simple_kiosk
```

## Configuration

The application is configured using a YAML file. By default, it looks for `config/urls.yaml`.

### Example Configuration

```yaml
default_duration: 30
urls:
  - url: https://example.com
    duration: 30
  - url: https://google.com
    duration: 20
  - url: https://github.com
    duration: 45
mqtt:
  broker: localhost
  port: 1883
  username: null
  password: null
  client_id: web_rotator_001
  topics:
    commands: displays/commands
    status: displays/status
    config: displays/config
```

### Configuration Options

- **default_duration**: Default display duration in seconds (1-86400)
- **urls**: List of URLs to rotate through
  - **url**: The web page URL to display
  - **duration**: How long to display this URL (overrides default_duration)
- **mqtt**: MQTT broker configuration
  - **broker**: MQTT broker address
  - **port**: MQTT broker port
  - **username/password**: Authentication credentials (optional)
  - **client_id**: Unique client identifier
  - **topics**: MQTT topics for commands, status, and configuration

## API Endpoints

### Configuration Management

- `GET /api/config` - Get current configuration
- `PUT /api/config` - Update configuration
- `POST /api/config/reload` - Reload configuration from file

### Display Control

- `GET /api/status` - Get current display status
- `POST /api/control/pause` - Pause rotation
- `POST /api/control/resume` - Resume rotation
- `POST /api/control/jump/{index}` - Jump to URL at index
- `POST /api/control/next` - Skip to next URL

### URL Management

- `GET /api/urls` - List all URLs
- `POST /api/urls` - Add new URL
- `PUT /api/urls/{index}` - Update URL at index
- `DELETE /api/urls/{index}` - Remove URL at index

### System Management

- `GET /api/health` - Health check endpoint
- `POST /api/system/restart` - Restart display system

## MQTT Commands

The application subscribes to MQTT topics for remote control. All commands should be sent as JSON to the configured commands topic.

### Command Format

```json
{
  "command": "command_type",
  "timestamp": "2023-01-01T10:30:00Z",
  "device_id": "display_001"
}
```

### Available Commands

#### Pause Rotation
```json
{
  "command": "pause",
  "timestamp": "2023-01-01T10:30:00Z",
  "device_id": "display_001"
}
```

#### Resume Rotation
```json
{
  "command": "resume",
  "timestamp": "2023-01-01T10:31:00Z",
  "device_id": "display_001"
}
```

#### Jump to Specific URL
```json
{
  "command": "jump",
  "index": 2,
  "timestamp": "2023-01-01T10:32:00Z",
  "device_id": "display_001"
}
```

#### Skip to Next URL
```json
{
  "command": "next",
  "timestamp": "2023-01-01T10:33:00Z",
  "device_id": "display_001"
}
```

#### Add URL Dynamically
```json
{
  "command": "add_url",
  "url": "https://example.com",
  "duration": 30,
  "index": null,
  "timestamp": "2023-01-01T10:34:00Z",
  "device_id": "display_001"
}
```

#### Update Configuration
```json
{
  "command": "update_config",
  "config": {
    "default_duration": 45,
    "urls": [...]
  },
  "timestamp": "2023-01-01T10:35:00Z",
  "device_id": "display_001"
}
```

## Status Reporting

The application publishes status updates to the configured status topic every 30 seconds and on state changes.

### Status Format

```json
{
  "device_id": "display_001",
  "status": "running",
  "current_url": "https://example.com",
  "current_index": 1,
  "total_urls": 5,
  "remaining_time": 25,
  "last_error": null,
  "uptime": 3600,
  "timestamp": "2023-01-01T10:35:00Z"
}
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run tests with coverage
pytest --cov=super_simple_kiosk tests/

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
```

### Code Quality

```bash
# Format code
black src/
isort src/

# Lint code
ruff check src/

# Type checking
mypy src/
```

### Environment Variables

- `FLASK_ENV` - Flask environment (development, production)
- `FLASK_DEBUG` - Enable debug mode (true, false)
- `DISPLAY_CONFIG_FILE` - Path to configuration file
- `DISPLAY_STATE_FILE` - Path to state file
- `MQTT_BROKER` - MQTT broker address
- `MQTT_PORT` - MQTT broker port
- `MQTT_USERNAME` - MQTT username
- `MQTT_PASSWORD` - MQTT password
- `DEVICE_ID` - Device identifier
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FORMAT` - Logging format (json, text)

## Architecture

The application follows a modular architecture with clear separation of concerns:

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

### Core Components

- **Flask Web Application**: RESTful API and web service framework
- **Display Manager**: Core rotation logic and state management
- **Browser Manager**: Chromium browser control via Selenium
- **MQTT Client**: Message queue integration for remote control
- **Configuration Manager**: YAML configuration and JSON state persistence

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/super-simple-kiosk.git
cd super-simple-kiosk

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests to ensure everything works
pytest
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Credits and Sources

- Built with [Flask](https://flask.palletsprojects.com/)
- Browser automation with [Selenium](https://selenium-python.readthedocs.io/)
- MQTT integration with [paho-mqtt](https://pypi.org/project/paho-mqtt/)
- Containerized with [Docker](https://www.docker.com/)
