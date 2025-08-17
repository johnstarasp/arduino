# Deployment Guide

This guide covers deploying the IoT Speedometer API system to various cloud platforms.

## 🌊 Heroku Deployment (Recommended for Beginners)

### Prerequisites
- Heroku account
- Heroku CLI installed
- Git repository

### Step 1: Prepare for Deployment

```bash
cd application/api

# Create Procfile
echo "web: node server.js" > Procfile

# Create .gitignore if not exists
cat > .gitignore << EOF
node_modules/
npm-debug.log*
.env
data/
logs/
EOF
```

### Step 2: Initialize Heroku App

```bash
# Login to Heroku
heroku login

# Create app
heroku create your-speedometer-api

# Add PostgreSQL add-on (free tier)
heroku addons:create heroku-postgresql:mini
```

### Step 3: Configure Environment Variables

```bash
# Set production environment
heroku config:set NODE_ENV=production

# Set JWT secret
heroku config:set JWT_SECRET=$(openssl rand -base64 32)

# Set database URL (automatically set by PostgreSQL add-on)
# heroku config:set DATABASE_URL=<automatically-set>

# Optional: Firebase for push notifications
heroku config:set FIREBASE_SERVER_KEY=your-firebase-key
heroku config:set FIREBASE_PROJECT_ID=your-project-id
```

### Step 4: Update Database Configuration

Update `server.js` to use PostgreSQL in production:

```javascript
// Add to server.js
const dbConfig = process.env.NODE_ENV === 'production' 
  ? {
      client: 'postgresql',
      connection: process.env.DATABASE_URL,
      ssl: { rejectUnauthorized: false }
    }
  : {
      client: 'sqlite3',
      connection: { filename: './data/speedometer.db' }
    };
```

### Step 5: Deploy

```bash
# Initialize git (if not already done)
git init
git add .
git commit -m "Initial commit"

# Add Heroku remote
heroku git:remote -a your-speedometer-api

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

### Step 6: Set Up Database

```bash
# Run database migrations
heroku run node -e "
const sqlite3 = require('sqlite3');
// Add your database initialization code here
"
```

Your API will be available at: `https://your-speedometer-api.herokuapp.com`

## 🚀 DigitalOcean Deployment

### Step 1: Create Droplet

1. Create a new Ubuntu 20.04 droplet
2. Choose appropriate size (Basic $6/month is sufficient)
3. Add SSH key for secure access

### Step 2: Server Setup

```bash
# Connect to your droplet
ssh root@your-droplet-ip

# Update system
apt update && apt upgrade -y

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt-get install -y nodejs

# Install PM2 for process management
npm install -g pm2

# Install Nginx for reverse proxy
apt install nginx -y

# Install PostgreSQL
apt install postgresql postgresql-contrib -y
```

### Step 3: Database Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE speedometer;
CREATE USER speedometer_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE speedometer TO speedometer_user;
\q
```

### Step 4: Application Deployment

```bash
# Create app directory
mkdir /var/www/speedometer-api
cd /var/www/speedometer-api

# Clone your repository
git clone https://github.com/your-username/speedometer-api.git .

# Install dependencies
npm install --production

# Create .env file
cat > .env << EOF
NODE_ENV=production
PORT=3000
DB_PATH=postgresql://speedometer_user:secure_password@localhost:5432/speedometer
JWT_SECRET=$(openssl rand -base64 32)
EOF

# Start with PM2
pm2 start server.js --name speedometer-api
pm2 save
pm2 startup
```

### Step 5: Nginx Configuration

```bash
# Create Nginx site config
cat > /etc/nginx/sites-available/speedometer-api << EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/speedometer-api /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

### Step 6: SSL with Let's Encrypt

```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Get SSL certificate
certbot --nginx -d your-domain.com

# Auto-renewal is set up automatically
```

## 🏗️ AWS EC2 + RDS Deployment

### Step 1: Create RDS Instance

1. Go to AWS RDS Console
2. Create PostgreSQL database
3. Choose appropriate instance size
4. Note connection details

### Step 2: Launch EC2 Instance

1. Launch Ubuntu 20.04 instance
2. Configure security groups (ports 22, 80, 443)
3. Create or use existing key pair

### Step 3: Application Setup

Similar to DigitalOcean setup, but use RDS connection string:

```bash
# .env configuration
DB_PATH=postgresql://username:password@rds-endpoint:5432/database
```

### Step 4: Load Balancer (Optional)

For high availability, set up Application Load Balancer with multiple EC2 instances.

## 📦 Docker Deployment

### Step 1: Create Dockerfile

```dockerfile
# application/api/Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

USER node

CMD ["node", "server.js"]
```

### Step 2: Create docker-compose.yml

```yaml
# application/docker-compose.yml
version: '3.8'

services:
  api:
    build: ./api
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DB_PATH=postgresql://postgres:password@db:5432/speedometer
      - JWT_SECRET=your-jwt-secret
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=speedometer
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
```

### Step 3: Deploy with Docker

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Scale API instances
docker-compose up -d --scale api=3
```

## 🔄 CI/CD with GitHub Actions

### Step 1: Create Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Node.js
      uses: actions/setup-node@v2
      with:
        node-version: '18'
        
    - name: Install dependencies
      run: |
        cd application/api
        npm ci
        
    - name: Run tests
      run: |
        cd application/api
        npm test
        
    - name: Deploy to Heroku
      uses: akhileshns/heroku-deploy@v3.12.12
      with:
        heroku_api_key: ${{secrets.HEROKU_API_KEY}}
        heroku_app_name: "your-speedometer-api"
        heroku_email: "your-email@example.com"
        appdir: "application/api"
```

## 📊 Monitoring Setup

### Health Checks

```bash
# Create health check script
cat > /usr/local/bin/check-api.sh << EOF
#!/bin/bash
curl -f http://localhost:3000/health || exit 1
EOF

chmod +x /usr/local/bin/check-api.sh

# Add to crontab for monitoring
crontab -e
# Add: */5 * * * * /usr/local/bin/check-api.sh
```

### Log Management

```bash
# Configure log rotation
cat > /etc/logrotate.d/speedometer-api << EOF
/var/www/speedometer-api/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 0644 www-data www-data
}
EOF
```

## 🔒 Security Checklist

- [ ] Enable firewall (UFW on Ubuntu)
- [ ] Set up SSL certificates
- [ ] Configure secure headers
- [ ] Use environment variables for secrets
- [ ] Enable database connection encryption
- [ ] Set up monitoring and alerting
- [ ] Regular security updates
- [ ] Backup strategy

## 🚨 Backup Strategy

### Database Backups

```bash
# Create backup script
cat > /usr/local/bin/backup-db.sh << EOF
#!/bin/bash
pg_dump speedometer > /backups/speedometer-\$(date +%Y%m%d).sql
# Upload to S3 or other cloud storage
EOF

# Schedule daily backups
crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-db.sh
```

## 🔧 Troubleshooting

### Common Issues

1. **Port binding errors**: Ensure port 3000 is available
2. **Database connection failures**: Check connection string and firewall
3. **Memory issues**: Monitor with `htop` and adjust PM2 settings
4. **SSL certificate issues**: Check certificate expiration

### Useful Commands

```bash
# Check service status
pm2 status
pm2 logs speedometer-api

# Monitor resources
htop
df -h

# Check network connections
netstat -tulpn | grep :3000

# Test API health
curl http://localhost:3000/health
```

This completes the deployment guide. Choose the platform that best fits your needs and technical requirements.