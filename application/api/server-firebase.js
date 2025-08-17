const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const morgan = require('morgan');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { body, validationResult } = require('express-validator');
const admin = require('firebase-admin');
const path = require('path');
const fs = require('fs');
const http = require('http');
const socketIo = require('socket.io');
const winston = require('winston');
const cron = require('node-cron');
const { v4: uuidv4 } = require('uuid');

require('dotenv').config();

// Logger configuration
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.errors({ stack: true }),
    winston.format.json()
  ),
  defaultMeta: { service: 'speedometer-firebase-api' },
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

class SpeedometerFirebaseAPI {
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
    
    this.initFirebase();
    this.setupMiddleware();
    this.setupRoutes();
    this.setupWebSockets();
    this.setupCronJobs();
  }

  initFirebase() {
    try {
      // Initialize Firebase Admin SDK
      const serviceAccount = process.env.FIREBASE_SERVICE_ACCOUNT_KEY 
        ? JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT_KEY)
        : require('./firebase-service-account-key.json');

      admin.initializeApp({
        credential: admin.credential.cert(serviceAccount),
        databaseURL: process.env.FIREBASE_DATABASE_URL,
        projectId: process.env.FIREBASE_PROJECT_ID
      });

      this.db = admin.firestore();
      this.messaging = admin.messaging();
      
      // Configure Firestore settings
      this.db.settings({
        timestampsInSnapshots: true
      });

      logger.info('Firebase initialized successfully');
    } catch (error) {
      logger.error('Firebase initialization failed:', error);
      process.exit(1);
    }
  }

  setupMiddleware() {
    // Security
    this.app.use(helmet());
    
    // Rate limiting
    const limiter = rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 1000,
      message: 'Too many requests from this IP'
    });
    this.app.use('/api/', limiter);

    // IoT device rate limiting
    const iotLimiter = rateLimit({
      windowMs: 60 * 1000, // 1 minute
      max: 10,
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
    this.authenticateApiKey = async (req, res, next) => {
      try {
        const apiKey = req.headers['x-api-key'] || req.headers['authorization']?.replace('Bearer ', '');
        
        if (!apiKey) {
          return res.status(401).json({ error: 'API key required' });
        }

        // Query Firestore for API key
        const apiKeyDoc = await this.db.collection('api_keys')
          .where('api_key', '==', apiKey)
          .where('active', '==', true)
          .limit(1)
          .get();

        if (apiKeyDoc.empty) {
          return res.status(401).json({ error: 'Invalid API key' });
        }

        const keyData = apiKeyDoc.docs[0].data();
        req.deviceId = keyData.device_id;
        next();
      } catch (error) {
        logger.error('API key validation error:', error);
        res.status(500).json({ error: 'Internal server error' });
      }
    };
  }

  setupRoutes() {
    // Health check
    this.app.get('/health', (req, res) => {
      res.json({ 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        firebase: 'connected'
      });
    });

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
      async (req, res) => {
        try {
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
            signal_strength: req.body.signal_strength || null,
            created_at: admin.firestore.FieldValue.serverTimestamp()
          };

          // Add to Firestore
          const docRef = await this.db.collection('speed_data').add(data);

          // Update device last_seen
          await this.db.collection('devices').doc(req.deviceId).update({
            last_seen: admin.firestore.FieldValue.serverTimestamp()
          });

          // Emit real-time data to connected clients
          this.io.emit('speed_data', {
            id: docRef.id,
            ...data,
            created_at: new Date().toISOString()
          });

          // Check for alerts
          await this.checkAlerts(data);

          logger.info(`Data received from device ${data.device_id}: ${data.speed} km/h`);
          res.status(201).json({ 
            message: 'Data received successfully',
            id: docRef.id,
            timestamp: new Date().toISOString()
          });

        } catch (error) {
          logger.error('Error storing speed data:', error);
          res.status(500).json({ error: 'Failed to store data' });
        }
      }
    );

    // GET /api/devices - List all devices
    this.app.get('/api/devices', async (req, res) => {
      try {
        const devicesSnapshot = await this.db.collection('devices').get();
        const devices = [];

        for (const doc of devicesSnapshot.docs) {
          const deviceData = { id: doc.id, ...doc.data() };
          
          // Get record count for each device
          const dataSnapshot = await this.db.collection('speed_data')
            .where('device_id', '==', doc.id)
            .count()
            .get();
          
          deviceData.total_records = dataSnapshot.data().count;
          
          // Get last data received
          const lastDataSnapshot = await this.db.collection('speed_data')
            .where('device_id', '==', doc.id)
            .orderBy('created_at', 'desc')
            .limit(1)
            .get();
          
          if (!lastDataSnapshot.empty) {
            deviceData.last_data_received = lastDataSnapshot.docs[0].data().created_at;
          }
          
          devices.push(deviceData);
        }

        res.json(devices);
      } catch (error) {
        logger.error('Error fetching devices:', error);
        res.status(500).json({ error: 'Failed to fetch devices' });
      }
    });

    // GET /api/devices/:deviceId/data - Get speed data for a device
    this.app.get('/api/devices/:deviceId/data', async (req, res) => {
      try {
        const { deviceId } = req.params;
        const { limit = 100, from, to } = req.query;

        let query = this.db.collection('speed_data')
          .where('device_id', '==', deviceId);

        if (from) {
          query = query.where('timestamp', '>=', from);
        }
        
        if (to) {
          query = query.where('timestamp', '<=', to);
        }

        query = query.orderBy('timestamp', 'desc').limit(parseInt(limit));

        const snapshot = await query.get();
        const data = snapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        }));

        res.json(data);
      } catch (error) {
        logger.error('Error fetching speed data:', error);
        res.status(500).json({ error: 'Failed to fetch data' });
      }
    });

    // GET /api/devices/:deviceId/stats - Get statistics for a device
    this.app.get('/api/devices/:deviceId/stats', async (req, res) => {
      try {
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

        const snapshot = await this.db.collection('speed_data')
          .where('device_id', '==', deviceId)
          .where('timestamp', '>=', since.toISOString())
          .get();

        let totalRecords = 0;
        let totalSpeed = 0;
        let maxSpeed = 0;
        let minSpeed = Infinity;
        let totalPulses = 0;

        snapshot.docs.forEach(doc => {
          const data = doc.data();
          totalRecords++;
          totalSpeed += data.speed;
          maxSpeed = Math.max(maxSpeed, data.speed);
          minSpeed = Math.min(minSpeed, data.speed);
          totalPulses += data.pulse_count;
        });

        const stats = {
          total_records: totalRecords,
          avg_speed: totalRecords > 0 ? totalSpeed / totalRecords : 0,
          max_speed: totalRecords > 0 ? maxSpeed : 0,
          min_speed: totalRecords > 0 && minSpeed !== Infinity ? minSpeed : 0,
          total_pulses: totalPulses
        };

        res.json({
          period,
          since: since.toISOString(),
          stats
        });
      } catch (error) {
        logger.error('Error fetching statistics:', error);
        res.status(500).json({ error: 'Failed to fetch statistics' });
      }
    });

    // GET /api/alerts - Get alerts
    this.app.get('/api/alerts', async (req, res) => {
      try {
        const { device_id, acknowledged = 'false' } = req.query;
        
        let query = this.db.collection('alerts');
        
        if (device_id) {
          query = query.where('device_id', '==', device_id);
        }
        
        if (acknowledged === 'false') {
          query = query.where('acknowledged', '==', false);
        }
        
        query = query.orderBy('created_at', 'desc').limit(100);
        
        const snapshot = await query.get();
        const alerts = snapshot.docs.map(doc => ({
          id: doc.id,
          ...doc.data()
        }));

        res.json(alerts);
      } catch (error) {
        logger.error('Error fetching alerts:', error);
        res.status(500).json({ error: 'Failed to fetch alerts' });
      }
    });

    // PUT /api/alerts/:alertId/acknowledge - Acknowledge an alert
    this.app.put('/api/alerts/:alertId/acknowledge', async (req, res) => {
      try {
        const { alertId } = req.params;
        
        await this.db.collection('alerts').doc(alertId).update({
          acknowledged: true,
          acknowledged_at: admin.firestore.FieldValue.serverTimestamp()
        });
        
        res.json({ message: 'Alert acknowledged' });
      } catch (error) {
        logger.error('Error acknowledging alert:', error);
        res.status(500).json({ error: 'Failed to acknowledge alert' });
      }
    });

    // POST /api/devices - Register new device
    this.app.post('/api/devices', 
      [
        body('name').isLength({ min: 1 }),
        body('description').optional().isString()
      ],
      async (req, res) => {
        try {
          const errors = validationResult(req);
          if (!errors.isEmpty()) {
            return res.status(400).json({ errors: errors.array() });
          }

          const deviceId = uuidv4();
          const apiKey = this.generateApiKey();

          // Create device
          await this.db.collection('devices').doc(deviceId).set({
            name: req.body.name,
            description: req.body.description || '',
            active: true,
            created_at: admin.firestore.FieldValue.serverTimestamp()
          });

          // Create API key
          await this.db.collection('api_keys').add({
            device_id: deviceId,
            api_key: apiKey,
            active: true,
            created_at: admin.firestore.FieldValue.serverTimestamp()
          });

          res.status(201).json({
            device_id: deviceId,
            api_key: apiKey,
            message: 'Device registered successfully'
          });

        } catch (error) {
          logger.error('Error registering device:', error);
          res.status(500).json({ error: 'Failed to register device' });
        }
      }
    );

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
    cron.schedule('0 0 * * *', async () => {
      try {
        const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
        
        const oldDataSnapshot = await this.db.collection('speed_data')
          .where('created_at', '<', thirtyDaysAgo)
          .get();

        const batch = this.db.batch();
        oldDataSnapshot.docs.forEach(doc => {
          batch.delete(doc.ref);
        });

        await batch.commit();
        logger.info(`Cleaned up ${oldDataSnapshot.docs.length} old records`);
      } catch (error) {
        logger.error('Error cleaning up old data:', error);
      }
    });
  }

  async checkAlerts(data) {
    try {
      const alerts = [];

      // High speed alert
      if (data.speed > 50) {
        alerts.push({
          device_id: data.device_id,
          alert_type: 'high_speed',
          message: `High speed detected: ${data.speed} km/h`,
          severity: 'warning',
          data: { speed: data.speed, threshold: 50 }
        });
      }

      // Low battery alert
      if (data.battery_level && data.battery_level < 20) {
        alerts.push({
          device_id: data.device_id,
          alert_type: 'low_battery',
          message: `Low battery: ${data.battery_level}%`,
          severity: 'warning',
          data: { battery_level: data.battery_level, threshold: 20 }
        });
      }

      // Poor signal alert
      if (data.signal_strength && data.signal_strength < -90) {
        alerts.push({
          device_id: data.device_id,
          alert_type: 'poor_signal',
          message: `Poor signal strength: ${data.signal_strength} dBm`,
          severity: 'info',
          data: { signal_strength: data.signal_strength, threshold: -90 }
        });
      }

      // Create alerts in Firestore
      for (const alert of alerts) {
        await this.createAlert(alert);
      }
    } catch (error) {
      logger.error('Error checking alerts:', error);
    }
  }

  async createAlert(alertData) {
    try {
      const alert = {
        ...alertData,
        acknowledged: false,
        created_at: admin.firestore.FieldValue.serverTimestamp()
      };

      const docRef = await this.db.collection('alerts').add(alert);

      // Emit alert to connected clients
      this.io.emit('alert', {
        id: docRef.id,
        ...alert,
        created_at: new Date().toISOString()
      });

      // Send push notification
      await this.sendPushNotification(alert);

      logger.info(`Alert created for device ${alertData.device_id}: ${alertData.message}`);
    } catch (error) {
      logger.error('Error creating alert:', error);
    }
  }

  async sendPushNotification(alert) {
    try {
      // Get device FCM tokens
      const tokensSnapshot = await this.db.collection('fcm_tokens')
        .where('device_id', '==', alert.device_id)
        .where('active', '==', true)
        .get();

      if (tokensSnapshot.empty) {
        return;
      }

      const tokens = tokensSnapshot.docs.map(doc => doc.data().token);

      const message = {
        notification: {
          title: this.getAlertTitle(alert.alert_type),
          body: alert.message
        },
        data: {
          alert_id: alert.id || '',
          device_id: alert.device_id,
          alert_type: alert.alert_type,
          severity: alert.severity
        }
      };

      // Send to multiple tokens
      const response = await this.messaging.sendToDevice(tokens, message);
      logger.info(`Push notification sent: ${response.successCount} successful, ${response.failureCount} failed`);

    } catch (error) {
      logger.error('Error sending push notification:', error);
    }
  }

  getAlertTitle(alertType) {
    const titles = {
      high_speed: '⚠️ High Speed Alert',
      low_battery: '🔋 Low Battery',
      poor_signal: '📡 Poor Signal',
      connection_lost: '🔴 Device Offline'
    };
    return titles[alertType] || '📢 Alert';
  }

  generateApiKey() {
    const crypto = require('crypto');
    return crypto.randomBytes(32).toString('hex');
  }

  start() {
    this.server.listen(this.port, () => {
      logger.info(`Speedometer Firebase API server running on port ${this.port}`);
      console.log(`🚀 Server running on http://localhost:${this.port}`);
      console.log(`🔥 Firebase Firestore connected`);
      console.log(`📡 WebSocket support enabled`);
      console.log(`📊 Health check: http://localhost:${this.port}/health`);
    });
  }

  stop() {
    this.server.close(() => {
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
const apiServer = new SpeedometerFirebaseAPI();
global.apiServer = apiServer;
apiServer.start();

module.exports = SpeedometerFirebaseAPI;