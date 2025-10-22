# Dashcam Management Platform - Backend

A comprehensive multi-tenant dashcam management platform that integrates with manufacturer APIs to provide fleet and consumer dashcam management capabilities.

## 🏗️ Architecture Overview

- **Backend**: FastAPI + MySQL
- **Authentication**: JWT-based with invoice number login
- **Integration**: Manufacturer MDVR API (52 endpoints)
- **Multi-tenancy**: Users only see their assigned devices

## 📋 Features

### Authentication & User Management
- Invoice-based user authentication
- Password change functionality
- JWT token management
- Multi-tenant access control

### Device Management
- Device assignment to users
- Real-time device status
- Device configuration management
- Organization tree structure

### Media & Video
- Live video preview
- Video playback with time ranges
- Stream management (main/sub streams)
- File listing and management

### GPS & Tracking
- Latest GPS location
- Historical track data
- Route analysis and statistics
- Track date availability

### Alarms & Monitoring
- Real-time alarm monitoring
- Alarm history and filtering
- Alarm type descriptions
- Attachment management (images/videos)

### Tasks & Messaging
- Text delivery to devices
- Task creation and management
- Task execution tracking
- Two-way communication

### Reports & Analytics
- Vehicle statistics and performance
- Fleet summary reports
- Comparative analysis
- Fuel efficiency and utilization metrics

### Admin Functions
- User creation and management
- Device assignment
- System configuration
- Forwarding platform setup

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- MySQL server
- Manufacturer API credentials

### Installation

1. **Clone and setup environment**:
```bash
cd pythonProject
pip install -r requirements.txt
```

2. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Set up database**:
- Create MySQL database: `dashcamdb`
- Update DATABASE_URL in .env

4. **Configure manufacturer API**:
```env
MANUFACTURER_API_BASE_URL=http://127.0.0.1:9337
MANUFACTURER_API_USERNAME=your_integrator_username
MANUFACTURER_API_PASSWORD=your_integrator_password
```

5. **Start the server**:
```bash
python start.py
```

### Environment Variables

Create `.env` file with:

```env
# Database Configuration
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/dashcamdb

# JWT Configuration
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Manufacturer API Configuration
MANUFACTURER_API_BASE_URL=http://127.0.0.1:9337
MANUFACTURER_API_USERNAME=your_integrator_username
MANUFACTURER_API_PASSWORD=your_integrator_password

# Server Configuration
HOST=127.0.0.1
PORT=8000
RELOAD=true
```

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔗 API Endpoints Overview

### Authentication (`/auth`)
- `POST /auth/login` - Login with invoice number
- `POST /auth/change-password` - Change password
- `GET /auth/me` - Get current user info

### Devices (`/devices`)
- `GET /devices/` - Get user's assigned devices
- `GET /devices/{device_id}` - Get device details
- `POST /devices/{device_id}/config` - Get device configuration
- `GET /devices/status/all` - Get all device statuses

### Media (`/media`)
- `POST /media/preview` - Start live preview
- `POST /media/preview/close` - Close preview
- `POST /media/playback` - Start video playback
- `POST /media/playback/close` - Close playback
- `GET /media/files/{device_id}` - Get media files

### GPS (`/gps`)
- `GET /gps/latest/{device_id}` - Get latest GPS location
- `POST /gps/track-dates` - Query available track dates
- `POST /gps/history` - Get detailed track history
- `GET /gps/devices` - Get devices with GPS status

### Alarms (`/alarms`)
- `GET /alarms/recent/{device_id}` - Get recent alarms
- `POST /alarms/query` - Query alarms by time range
- `GET /alarms/types` - Get alarm type descriptions
- `POST /alarms/attachment` - Get alarm attachments
- `GET /alarms/summary` - Get alarm summary

### Tasks (`/tasks`)
- `POST /tasks/create` - Create text delivery task
- `GET /tasks/` - Get task list
- `GET /tasks/{task_id}` - Get task details
- `PUT /tasks/{task_id}/status` - Update task status
- `GET /tasks/{task_id}/result` - Get task results
- `DELETE /tasks/{task_id}` - Delete task
- `POST /tasks/send-text` - Send immediate text

### Reports (`/reports`)
- `GET /reports/statistics/{device_id}` - Get vehicle statistics
- `POST /reports/vehicle-details` - Get detailed vehicle info
- `GET /reports/fleet-summary` - Get fleet summary
- `GET /reports/comparison` - Compare multiple devices

### Admin (`/admin`)
- `POST /admin/users` - Create new user
- `GET /admin/users` - List all users
- `POST /admin/devices/assign` - Assign device to user
- `GET /admin/devices/unassigned` - Get unassigned devices
- `POST /admin/config/system` - Manage system config
- `GET /admin/config/system` - Query system config
- `POST /admin/forwarding/platform` - Create forwarding platform
- `POST /admin/forwarding/policy` - Create forwarding policy
- `GET /admin/dashboard/overview` - Get admin dashboard

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Device Access Control**: Users only see assigned devices
- **API Proxy**: Manufacturer credentials never exposed to frontend
- **Input Validation**: Comprehensive request validation
- **Error Handling**: Secure error responses

## 🏢 Multi-Tenant Architecture

- **User Isolation**: Each customer sees only their devices
- **Invoice-based Login**: Customers log in with invoice numbers
- **Device Assignment**: Admin assigns devices to customers
- **API Filtering**: All manufacturer API calls filtered by user access

## 🔧 Integration Details

### Manufacturer API Integration
- **Authentication**: Token-based with automatic refresh
- **Error Handling**: Comprehensive error handling and logging
- **Rate Limiting**: Built-in request management
- **Stub Implementation**: All 40+ endpoints implemented

### Supported Manufacturer Endpoints
- User authentication and management
- Organization tree structure
- Device management and configuration
- GPS tracking and history
- Video streaming (preview/playback)
- Alarm monitoring and attachments
- Task creation and messaging
- System configuration
- Forwarding and integration
- Statistics and reporting

## 🚀 Production Deployment

### Database Setup
1. Set up MySQL with proper user permissions
2. Create database and run initial migration
3. Configure connection pooling

### Security Hardening
1. Use environment variables for all secrets
2. Enable HTTPS/TLS
3. Set up proper CORS policies
4. Implement rate limiting
5. Add request logging

### Performance Optimization
1. Enable database connection pooling
2. Implement caching for frequent API calls
3. Set up monitoring and logging
4. Configure load balancing if needed

## 📞 API Error Codes

The system uses manufacturer API error codes plus custom codes:

- `1001` - Parameter validation error
- `1002` - Unauthorized (missing header)
- `1003` - User does not exist
- `1006` - Incorrect password
- `1008` - Token expired
- `1009` - Insufficient permissions
- `1100` - Query exceeds maximum time range
- `1102` - Device offline
- `1200` - Task does not exist

## 🤝 Development

### Project Structure
```
pythonProject/
├── main.py              # FastAPI application
├── start.py             # Startup script
├── database.py          # Database configuration
├── requirements.txt     # Dependencies
├── .env.example         # Environment template
├── models/              # Pydantic and SQLAlchemy models
├── routers/             # API route handlers
├── services/            # Business logic and external API integration
└── README.md           # This file
```

### Adding New Features
1. Define models in `models/`
2. Create service functions in `services/`
3. Add routes in `routers/`
4. Update main.py to include new router
5. Add tests and documentation

## 📝 License

This project is proprietary software for dashcam fleet management.


