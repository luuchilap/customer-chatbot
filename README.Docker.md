# Docker Setup for MongoDB Product Chatbot

This document explains how to run the MongoDB Product Chatbot using Docker and Docker Compose.

## 🐳 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- MongoDB Atlas cluster (cloud database)
- OpenAI API key

### 1. Environment Setup

Your `.env` file is already configured with MongoDB Atlas and OpenAI API key:

```bash
# Your .env file already contains:
# MONGO_URI=mongodb+srv://luuchilap:zkc0pDqzsBYw5Lpz@cluster0.432k5df.mongodb.net/product-management
# OPENAI_API_KEY=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
```

### 2. Start All Services

```bash
# Start all services (API, Frontend)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

### 3. Access the Application

- **Frontend**: http://localhost:4000
- **API Documentation**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health
- **MongoDB Atlas**: Use MongoDB Compass or Atlas web interface

## 🏗️ Architecture

The Docker setup includes:

### Services

1. **MongoDB Atlas** - Cloud database
   - Connection: mongodb+srv://luuchilap:zkc0pDqzsBYw5Lpz@cluster0.432k5df.mongodb.net/product-management
   - Database: product-management
   - Managed by MongoDB Atlas

2. **api** - FastAPI web server
   - Port: 8000
   - Health checks enabled
   - Auto-restart on failure
   - Connects to MongoDB Atlas
   - Includes AI chatbot with LangChain

3. **frontend** - Nginx static file server
   - Port: 4000
   - Serves HTML/CSS/JS files
   - Gzip compression enabled

### Networks
- **chatbot-network**: Internal network for service communication

### Database
- **MongoDB Atlas**: Cloud-hosted database with automatic backups and scaling

## 🔧 Development

### Development Mode
```bash
# Use override file for development
docker-compose -f docker-compose.yml -f docker-compose.override.yml up

# This enables:
# - Hot reload for Python code
# - Volume mounting for live code changes
# - Debug mode enabled
```

### Individual Services
```bash
# Start only MongoDB
docker-compose up mongodb

# Start API and dependencies
docker-compose up api

# Rebuild and start
docker-compose up --build
```

### Database Management
```bash
# Connect to MongoDB
docker-compose exec mongodb mongosh

# View MongoDB logs
docker-compose logs mongodb

# Reset database
docker-compose down -v  # Removes volumes
docker-compose up -d
```

## 📊 Monitoring

### Health Checks
All services include health checks:
```bash
# Check service health
docker-compose ps

# View health status
docker inspect chatbot-api | grep Health -A 10
```

### Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f mongodb
```

## 🛠️ Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   # Check if ports are in use
   netstat -tulpn | grep :8000
   netstat -tulpn | grep :27017
   ```

2. **MongoDB connection issues**
   ```bash
   # Check MongoDB logs
   docker-compose logs mongodb
   
   # Test connection
   docker-compose exec api python -c "from backend.chatbot_service import MongoDBChatbotService; print('MongoDB connection test')"
   ```

3. **OpenAI API key issues**
   ```bash
   # Check environment variables
   docker-compose exec api env | grep OPENAI
   ```

4. **Permission issues**
   ```bash
   # Fix file permissions
   sudo chown -R $USER:$USER .
   ```

### Reset Everything
```bash
# Stop and remove everything
docker-compose down -v --remove-orphans

# Remove images
docker-compose down --rmi all

# Clean up
docker system prune -f
```

## 🔒 Security Notes

- Change default passwords in production
- Use secrets management for API keys
- Enable MongoDB authentication
- Configure firewall rules
- Use HTTPS in production

## 📝 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URI` | MongoDB connection string | `mongodb://admin:password123@mongodb:27017/product-management?authSource=admin` |
| `OPENAI_API_KEY` | OpenAI API key | **Required** |
| `PORT` | API server port | `8000` |
| `DEBUG` | Debug mode | `false` |

## 🚀 Production Deployment

For production deployment:

1. Use environment-specific compose files
2. Set up proper secrets management
3. Configure reverse proxy (nginx/traefik)
4. Enable SSL/TLS
5. Set up monitoring and logging
6. Configure backup strategies

```bash
# Production example
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```
