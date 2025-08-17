const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { body, validationResult } = require('express-validator');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const fs = require('fs');
const http = require('http');
const socketIo = require('socket.io');
const winston = require('winston');
const cron = require('node-cron');

require('dotenv').config();

// Logger configuration
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'speedometer-api' },
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ],
});

// Create logs directory
if (!fs.existsSync('logs')) {
  fs.mkdirSync('logs');
}

class SpeedometerAPI {
  constructor() {
    this.app = express();
    this.server = http.createServer(this.app);
    this.io = socketIo(this.server, {
      cors: {
        origin: "*",
        methods: ["GET", "POST"]
      }
    });
    
    this.port = process.env.PORT || 3000;
    this.dbPath = process.env.DB_PATH || './data/speedometer.db';
    
    this.initDatabase();
    this.setupMiddleware();
    this.setupRoutes();
    this.setupWebSockets();
    this.setupCronJobs();
  }

  initDatabase() {
    // Ensure data directory exists
    const dataDir = path.dirname(this.dbPath);
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }

    this.db = new sqlite3.Database(this.dbPath, (err) => {
      if (err) {
        logger.error('Error opening database:', err);
      } else {
        logger.info('Connected to SQLite database');
      }
    });

    // Create tables
    this.db.serialize(() => {
      // Devices table
      this.db.run(`
        CREATE TABLE IF NOT EXISTS devices (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          description TEXT,
          active BOOLEAN DEFAULT TRUE,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          last_seen DATETIME
        )
      `);

      // Speed data table
      this.db.run(`
        CREATE TABLE IF NOT EXISTS speed_data (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          device_id TEXT NOT NULL,
          timestamp TEXT NOT NULL,
          speed REAL NOT NULL,
          pulse_count INTEGER NOT NULL,
          latitude REAL,
          longitude REAL,
          battery_level REAL,
          signal_strength INTEGER,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (device_id) REFERENCES devices (id)
        )
      `);

      // Alerts table
      this.db.run(`
        CREATE TABLE IF NOT EXISTS alerts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          device_id TEXT NOT NULL,
          alert_type TEXT NOT NULL,
          message TEXT NOT NULL,
          severity TEXT DEFAULT 'info',
          acknowledged BOOLEAN DEFAULT FALSE,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (device_id) REFERENCES devices (id)
        )
      `);

      // API keys table (for device authentication)
      this.db.run(`
        CREATE TABLE IF NOT EXISTS api_keys (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          device_id TEXT NOT NULL,
          api_key TEXT UNIQUE NOT NULL,
          active BOOLEAN DEFAULT TRUE,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (device_id) REFERENCES devices (id)
        )
      `);

      // Create indexes
      this.db.run(`CREATE INDEX IF NOT EXISTS idx_speed_data_device_timestamp ON speed_data(device_id, timestamp)`);
      this.db.run(`CREATE INDEX IF NOT EXISTS idx_speed_data_created_at ON speed_data(created_at)`);
      this.db.run(`CREATE INDEX IF NOT EXISTS idx_alerts_device ON alerts(device_id)`);
    });

    logger.info('Database tables initialized');
  }

  setupMiddleware() {
    // Security
    this.app.use(helmet());
    
    // Rate limiting
    const limiter = rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 1000, // limit each IP to 1000 requests per windowMs
      message: 'Too many requests from this IP'
    });
    this.app.use('/api/', limiter);

    // Data limiting for IoT devices
    const iotLimiter = rateLimit({
      windowMs: 60 * 1000, // 1 minute
      max: 10, // 10 requests per minute per device
      message: 'Rate limit exceeded for IoT device'
    });
    this.app.use('/api/data', iotLimiter);

    // CORS
    this.app.use(cors());
    
    // Compression
    this.app.use(compression());
    
    // Body parsing
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true }));
    
    // Logging
    this.app.use(morgan('combined', {
      stream: {
        write: (message) => logger.info(message.trim())
      }
    }));

    // API key authentication middleware
    this.authenticateApiKey = (req, res, next) => {
      const apiKey = req.headers['x-api-key'] || req.headers['authorization']?.replace('Bearer ', '');
      
      if (!apiKey) {
        return res.status(401).json({ error: 'API key required' });
      }

      this.db.get(
        'SELECT device_id FROM api_keys WHERE api_key = ? AND active = TRUE',
        [apiKey],
        (err, row) => {
          if (err) {
            logger.error('API key validation error:', err);
            return res.status(500).json({ error: 'Internal server error' });
          }
          
          if (!row) {
            return res.status(401).json({ error: 'Invalid API key' });
          }
          
          req.deviceId = row.device_id;
          next();
        }
      );
    };
  }

  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({ 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        uptime: process.uptime()
      });
    });

    // API Routes
    
    // POST /api/data - Receive data from IoT devices
    this.app.post('/api/data', 
      this.authenticateApiKey,
      [
        body('timestamp').isISO8601(),
        body('speed').isFloat({ min: 0 }),
        body('pulse_count').isInt({ min: 0 }),
        body('latitude').optional().isFloat(),
        body('longitude').optional().isFloat(),
        body('battery_level').optional().isFloat({ min: 0, max: 100 }),
        body('signal_strength').optional().isInt()
      ],
      (req, res) => {
        const errors = validationResult(req);
        if (!errors.isEmpty()) {
          return res.status(400).json({ errors: errors.array() });
        }

        const data = {
          device_id: req.deviceId,
          timestamp: req.body.timestamp,
          speed: req.body.speed,
          pulse_count: req.body.pulse_count,
          latitude: req.body.latitude || null,
          longitude: req.body.longitude || null,
          battery_level: req.body.battery_level || null,
          signal_strength: req.body.signal_strength || null
        };

        // Insert data
        this.db.run(`
          INSERT INTO speed_data 
          (device_id, timestamp, speed, pulse_count, latitude, longitude, battery_level, signal_strength)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        `, [
          data.device_id, data.timestamp, data.speed, data.pulse_count,
          data.latitude, data.longitude, data.battery_level, data.signal_strength
        ], function(err) {
          if (err) {
            logger.error('Error inserting speed data:', err);
            return res.status(500).json({ error: 'Failed to store data' });
          }

          // Update device last_seen
          this.db.run(
            'UPDATE devices SET last_seen = CURRENT_TIMESTAMP WHERE id = ?',
            [data.device_id]
          );

          // Emit real-time data to connected clients
          this.io.emit('speed_data', {
            id: this.lastID,
            ...data,
            created_at: new Date().toISOString()
          });

          // Check for alerts (speed thresholds, etc.)
          this.checkAlerts(data);

          logger.info(`Data received from device ${data.device_id}: ${data.speed} km/h`);
          res.status(201).json({ 
            message: 'Data received successfully',
            id: this.lastID,
            timestamp: new Date().toISOString()
          });
        }.bind(this));
      }
    );

    // GET /api/devices - List all devices
    this.app.get('/api/devices', (req, res) => {
      this.db.all(`
        SELECT d.*, 
               COUNT(sd.id) as total_records,
               MAX(sd.created_at) as last_data_received
        FROM devices d
        LEFT JOIN speed_data sd ON d.id = sd.device_id
        GROUP BY d.id
        ORDER BY d.created_at DESC
      `, (err, rows) => {
        if (err) {
          logger.error('Error fetching devices:', err);
          return res.status(500).json({ error: 'Failed to fetch devices' });
        }
        res.json(rows);
      });
    });

    // GET /api/devices/:deviceId/data - Get speed data for a device
    this.app.get('/api/devices/:deviceId/data', (req, res) => {
      const { deviceId } = req.params;
      const { limit = 100, offset = 0, from, to } = req.query;

      let query = `
        SELECT * FROM speed_data 
        WHERE device_id = ?
      `;
      let params = [deviceId];

      if (from) {
        query += ' AND timestamp >= ?';
        params.push(from);
      }
      
      if (to) {
        query += ' AND timestamp <= ?';
        params.push(to);
      }

      query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?';
      params.push(parseInt(limit), parseInt(offset));

      this.db.all(query, params, (err, rows) => {
        if (err) {
          logger.error('Error fetching speed data:', err);
          return res.status(500).json({ error: 'Failed to fetch data' });
        }
        res.json(rows);
      });
    });

    // GET /api/devices/:deviceId/stats - Get statistics for a device
    this.app.get('/api/devices/:deviceId/stats', (req, res) => {
      const { deviceId } = req.params;
      const { period = '24h' } = req.query;

      // Calculate time range
      const now = new Date();
      let since;
      switch (period) {
        case '1h':
          since = new Date(now.getTime() - 60 * 60 * 1000);
          break;
        case '24h':
          since = new Date(now.getTime() - 24 * 60 * 60 * 1000);
          break;
        case '7d':
          since = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          break;
        default:
          since = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      }

      this.db.get(`
        SELECT 
          COUNT(*) as total_records,
          AVG(speed) as avg_speed,
          MAX(speed) as max_speed,
          MIN(speed) as min_speed,
          SUM(pulse_count) as total_pulses
        FROM speed_data 
        WHERE device_id = ? AND timestamp >= ?
      `, [deviceId, since.toISOString()], (err, row) => {
        if (err) {
          logger.error('Error fetching statistics:', err);
          return res.status(500).json({ error: 'Failed to fetch statistics' });
        }
        
        res.json({
          period,
          since: since.toISOString(),
          stats: row || {
            total_records: 0,
            avg_speed: 0,
            max_speed: 0,
            min_speed: 0,
            total_pulses: 0
          }
        });
      });
    });

    // GET /api/alerts - Get alerts
    this.app.get('/api/alerts', (req, res) => {
      const { device_id, acknowledged = 'false' } = req.query;
      
      let query = 'SELECT * FROM alerts WHERE 1=1';
      let params = [];
      
      if (device_id) {
        query += ' AND device_id = ?';
        params.push(device_id);
      }
      
      if (acknowledged === 'false') {
        query += ' AND acknowledged = FALSE';
      }
      
      query += ' ORDER BY created_at DESC LIMIT 100';
      
      this.db.all(query, params, (err, rows) => {
        if (err) {
          logger.error('Error fetching alerts:', err);
          return res.status(500).json({ error: 'Failed to fetch alerts' });
        }
        res.json(rows);
      });
    });

    // PUT /api/alerts/:alertId/acknowledge - Acknowledge an alert
    this.app.put('/api/alerts/:alertId/acknowledge', (req, res) => {
      const { alertId } = req.params;
      
      this.db.run(
        'UPDATE alerts SET acknowledged = TRUE WHERE id = ?',
        [alertId],
        function(err) {
          if (err) {
            logger.error('Error acknowledging alert:', err);
            return res.status(500).json({ error: 'Failed to acknowledge alert' });
          }
          
          if (this.changes === 0) {
            return res.status(404).json({ error: 'Alert not found' });
          }
          
          res.json({ message: 'Alert acknowledged' });
        }
      );
    });

    // Serve static files for mobile app (if needed)
    this.app.use('/static', express.static(path.join(__dirname, 'public')));

    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({ error: 'Endpoint not found' });
    });

    // Error handler
    this.app.use((err, req, res, next) => {
      logger.error('Unhandled error:', err);
      res.status(500).json({ error: 'Internal server error' });
    });
  }

  setupWebSockets() {
    this.io.on('connection', (socket) => {
      logger.info(`Client connected: ${socket.id}`);

      // Join device-specific room
      socket.on('subscribe_device', (deviceId) => {
        socket.join(`device_${deviceId}`);
        logger.info(`Client ${socket.id} subscribed to device ${deviceId}`);
      });

      socket.on('disconnect', () => {
        logger.info(`Client disconnected: ${socket.id}`);
      });
    });
  }

  setupCronJobs() {
    // Clean up old data (keep last 30 days)
    cron.schedule('0 0 * * *', () => {
      const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
      
      this.db.run(
        'DELETE FROM speed_data WHERE created_at < ?',
        [thirtyDaysAgo],
        function(err) {
          if (err) {
            logger.error('Error cleaning up old data:', err);
          } else {
            logger.info(`Cleaned up ${this.changes} old records`);
          }
        }
      );
    });
  }

  checkAlerts(data) {
    // Example: High speed alert
    if (data.speed > 50) { // km/h
      this.createAlert(data.device_id, 'high_speed', `High speed detected: ${data.speed} km/h`, 'warning');
    }

    // Example: Low battery alert
    if (data.battery_level && data.battery_level < 20) {
      this.createAlert(data.device_id, 'low_battery', `Low battery: ${data.battery_level}%`, 'warning');
    }

    // Example: Poor signal alert
    if (data.signal_strength && data.signal_strength < -90) {
      this.createAlert(data.device_id, 'poor_signal', `Poor signal strength: ${data.signal_strength} dBm`, 'info');
    }
  }

  createAlert(deviceId, alertType, message, severity = 'info') {
    this.db.run(`
      INSERT INTO alerts (device_id, alert_type, message, severity)
      VALUES (?, ?, ?, ?)
    `, [deviceId, alertType, message, severity], function(err) {
      if (err) {
        logger.error('Error creating alert:', err);
      } else {
        // Emit alert to connected clients
        this.io.emit('alert', {
          id: this.lastID,
          device_id: deviceId,
          alert_type: alertType,
          message,
          severity,
          created_at: new Date().toISOString()
        });
        
        logger.info(`Alert created for device ${deviceId}: ${message}`);
      }
    }.bind(this));
  }

  start() {
    this.server.listen(this.port, () => {
      logger.info(`Speedometer API server running on port ${this.port}`);
      console.log(`🚀 Server running on http://localhost:${this.port}`);
      console.log(`📡 WebSocket support enabled`);
      console.log(`📊 Health check: http://localhost:${this.port}/health`);
    });
  }

  stop() {
    this.server.close(() => {
      this.db.close((err) => {
        if (err) {
          logger.error('Error closing database:', err);
        } else {
          logger.info('Database connection closed');
        }
      });
      logger.info('Server stopped');
    });
  }
}

// Handle graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  if (global.apiServer) {
    global.apiServer.stop();
  }
  process.exit(0);
});

process.on('SIGINT', () => {
  logger.info('SIGINT received, shutting down gracefully');
  if (global.apiServer) {
    global.apiServer.stop();
  }
  process.exit(0);
});

// Start server
const apiServer = new SpeedometerAPI();
global.apiServer = apiServer;
apiServer.start();

module.exports = SpeedometerAPI;