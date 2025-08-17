import firestore from '@react-native-firebase/firestore';
import messaging from '@react-native-firebase/messaging';
import auth from '@react-native-firebase/auth';
import AsyncStorage from '@react-native-async-storage/async-storage';
import AppConfig from '../config/AppConfig';

class FirebaseService {
  constructor() {
    this.listeners = new Map();
    this.unsubscribeFunctions = [];
    this.isInitialized = false;
  }

  async initialize() {
    try {
      if (this.isInitialized) return true;

      // Validate configuration
      if (!AppConfig.validate()) {
        throw new Error('Invalid Firebase configuration');
      }

      if (AppConfig.DEBUG_MODE) {
        console.log('[Firebase] Initializing with config:', AppConfig.FIREBASE_CONFIG);
      }

      // Initialize Firebase Auth (anonymous for device access)
      await this.initializeAuth();
      
      // Request notification permissions
      if (AppConfig.ENABLE_PUSH_NOTIFICATIONS) {
        await this.requestNotificationPermission();
      }
      
      this.isInitialized = true;
      console.log('[Firebase] Service initialized successfully');
      return true;
    } catch (error) {
      console.error('[Firebase] Initialization failed:', error);
      return false;
    }
  }

  async initializeAuth() {
    try {
      // Sign in anonymously for read access to data
      const userCredential = await auth().signInAnonymously();
      console.log('[Firebase] Signed in anonymously:', userCredential.user.uid);
    } catch (error) {
      console.error('[Firebase] Auth failed:', error);
      throw error;
    }
  }

  async requestNotificationPermission() {
    try {
      const authStatus = await messaging().requestPermission();
      const enabled =
        authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;

      if (enabled) {
        const token = await messaging().getToken();
        if (token) {
          await this.saveFCMToken(token);
          console.log('[Firebase] FCM token obtained:', token.substring(0, 20) + '...');
        }
      }
    } catch (error) {
      console.error('[Firebase] Notification permission failed:', error);
    }
  }

  async saveFCMToken(token) {
    try {
      await AsyncStorage.setItem('fcm_token', token);
      
      // Save to Firestore for server-side notifications
      const userId = auth().currentUser?.uid;
      if (userId) {
        await firestore().collection('fcm_tokens').add({
          user_id: userId,
          token: token,
          device_type: Platform.OS,
          device_id: AppConfig.DEFAULT_DEVICE_ID,
          active: true,
          created_at: firestore.FieldValue.serverTimestamp(),
        });
      }
    } catch (error) {
      console.error('[Firebase] Error saving FCM token:', error);
    }
  }

  // Device Management
  async getDevices() {
    try {
      const snapshot = await firestore()
        .collection('devices')
        .where('active', '==', true)
        .get();
      
      const devices = await Promise.all(
        snapshot.docs.map(async (doc) => {
          const deviceData = { id: doc.id, ...doc.data() };
          
          // Get latest data count
          const dataSnapshot = await firestore()
            .collection('speed_data')
            .where('device_id', '==', doc.id)
            .count()
            .get();
          
          deviceData.total_records = dataSnapshot.data().count;
          
          // Get last data received
          const lastDataSnapshot = await firestore()
            .collection('speed_data')
            .where('device_id', '==', doc.id)
            .orderBy('created_at', 'desc')
            .limit(1)
            .get();
          
          if (!lastDataSnapshot.empty) {
            const lastDoc = lastDataSnapshot.docs[0];
            deviceData.last_data_received = lastDoc.data().created_at;
          }
          
          return deviceData;
        })
      );
      
      return devices;
    } catch (error) {
      console.error('[Firebase] Error fetching devices:', error);
      throw error;
    }
  }

  // Real-time Speed Data with Configuration
  subscribeToDeviceData(deviceId, callback, limit = null) {
    try {
      const dataLimit = limit || AppConfig.CHART_DATA_POINTS_LIMIT;
      
      const unsubscribe = firestore()
        .collection('speed_data')
        .where('device_id', '==', deviceId)
        .orderBy('created_at', 'desc')
        .limit(dataLimit)
        .onSnapshot(
          (snapshot) => {
            const data = snapshot.docs.map(doc => ({
              id: doc.id,
              ...doc.data(),
              // Convert Firestore timestamp to JavaScript Date
              timestamp: doc.data().timestamp,
              created_at: doc.data().created_at?.toDate(),
            }));
            
            callback(data.reverse()); // Show oldest first for charts
          },
          (error) => {
            console.error('[Firebase] Speed data subscription error:', error);
            callback(null, error);
          }
        );

      this.unsubscribeFunctions.push(unsubscribe);
      return unsubscribe;
    } catch (error) {
      console.error('[Firebase] Error subscribing to device data:', error);
      throw error;
    }
  }

  // Real-time Latest Speed Update
  subscribeToLatestSpeed(deviceId, callback) {
    try {
      const unsubscribe = firestore()
        .collection('speed_data')
        .where('device_id', '==', deviceId)
        .orderBy('created_at', 'desc')
        .limit(1)
        .onSnapshot(
          (snapshot) => {
            if (!snapshot.empty) {
              const latestDoc = snapshot.docs[0];
              const data = {
                id: latestDoc.id,
                ...latestDoc.data(),
                created_at: latestDoc.data().created_at?.toDate(),
              };
              callback(data);

              // Check for speed alerts based on configuration
              if (data.speed > AppConfig.SPEED_ALERT_THRESHOLD) {
                this.notifyListeners('speed_alert', {
                  speed: data.speed,
                  threshold: AppConfig.SPEED_ALERT_THRESHOLD,
                  device_id: deviceId,
                });
              }
            }
          },
          (error) => {
            console.error('[Firebase] Latest speed subscription error:', error);
            callback(null, error);
          }
        );

      this.unsubscribeFunctions.push(unsubscribe);
      return unsubscribe;
    } catch (error) {
      console.error('[Firebase] Error subscribing to latest speed:', error);
      throw error;
    }
  }

  // Historical Data with Pagination
  async getDeviceDataPaginated(deviceId, options = {}) {
    try {
      const { 
        limit = AppConfig.CHART_DATA_POINTS_LIMIT, 
        startAfter = null, 
        from = null, 
        to = null 
      } = options;

      let query = firestore()
        .collection('speed_data')
        .where('device_id', '==', deviceId);

      // Date range filtering
      if (from) {
        query = query.where('timestamp', '>=', from);
      }
      if (to) {
        query = query.where('timestamp', '<=', to);
      }

      // Ordering and pagination
      query = query.orderBy('created_at', 'desc');
      
      if (startAfter) {
        query = query.startAfter(startAfter);
      }
      
      query = query.limit(limit);

      const snapshot = await query.get();
      const data = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data(),
        created_at: doc.data().created_at?.toDate(),
      }));

      return {
        data,
        lastDoc: snapshot.docs[snapshot.docs.length - 1] || null,
        hasMore: snapshot.docs.length === limit,
      };
    } catch (error) {
      console.error('[Firebase] Error fetching paginated data:', error);
      throw error;
    }
  }

  // Device Statistics with Configuration
  async getDeviceStats(deviceId, period = '24h') {
    try {
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

      const snapshot = await firestore()
        .collection('speed_data')
        .where('device_id', '==', deviceId)
        .where('created_at', '>=', since)
        .get();

      let totalRecords = 0;
      let totalSpeed = 0;
      let maxSpeed = 0;
      let minSpeed = Infinity;
      let totalPulses = 0;

      snapshot.docs.forEach(doc => {
        const data = doc.data();
        totalRecords++;
        totalSpeed += data.speed || 0;
        maxSpeed = Math.max(maxSpeed, data.speed || 0);
        minSpeed = Math.min(minSpeed, data.speed || 0);
        totalPulses += data.pulse_count || 0;
      });

      const wheelCircumference = AppConfig.DEFAULT_WHEEL_CIRCUMFERENCE;
      const stats = {
        total_records: totalRecords,
        avg_speed: totalRecords > 0 ? totalSpeed / totalRecords : 0,
        max_speed: totalRecords > 0 ? maxSpeed : 0,
        min_speed: totalRecords > 0 && minSpeed !== Infinity ? minSpeed : 0,
        total_pulses: totalPulses,
        distance_km: (totalPulses * wheelCircumference) / 1000,
      };

      return {
        period,
        since: since.toISOString(),
        stats,
        config: {
          wheel_circumference: wheelCircumference,
          speed_threshold: AppConfig.SPEED_ALERT_THRESHOLD,
        },
      };
    } catch (error) {
      console.error('[Firebase] Error fetching statistics:', error);
      throw error;
    }
  }

  // Alerts Management with Configuration
  subscribeToAlerts(deviceId = null, callback) {
    try {
      let query = firestore().collection('alerts');
      
      if (deviceId) {
        query = query.where('device_id', '==', deviceId);
      }
      
      query = query
        .where('acknowledged', '==', false)
        .orderBy('created_at', 'desc')
        .limit(50);

      const unsubscribe = query.onSnapshot(
        (snapshot) => {
          const alerts = snapshot.docs.map(doc => ({
            id: doc.id,
            ...doc.data(),
            created_at: doc.data().created_at?.toDate(),
          }));

          callback(alerts);

          // Send local notifications for new alerts
          if (AppConfig.ENABLE_PUSH_NOTIFICATIONS) {
            alerts.forEach(alert => {
              if (alert.severity === 'warning' || alert.severity === 'error') {
                this.notifyListeners('new_alert', alert);
              }
            });
          }
        },
        (error) => {
          console.error('[Firebase] Alerts subscription error:', error);
          callback(null, error);
        }
      );

      this.unsubscribeFunctions.push(unsubscribe);
      return unsubscribe;
    } catch (error) {
      console.error('[Firebase] Error subscribing to alerts:', error);
      throw error;
    }
  }

  async acknowledgeAlert(alertId) {
    try {
      await firestore().collection('alerts').doc(alertId).update({
        acknowledged: true,
        acknowledged_at: firestore.FieldValue.serverTimestamp(),
      });
      
      console.log('[Firebase] Alert acknowledged:', alertId);
      return true;
    } catch (error) {
      console.error('[Firebase] Error acknowledging alert:', error);
      throw error;
    }
  }

  // Configuration-aware data processing
  processSpeedData(rawData) {
    return rawData.map(item => ({
      ...item,
      timestamp: new Date(item.timestamp),
      created_at: new Date(item.created_at),
      isHighSpeed: item.speed > AppConfig.SPEED_ALERT_THRESHOLD,
      isLowBattery: item.battery_level && item.battery_level < AppConfig.BATTERY_ALERT_THRESHOLD,
    }));
  }

  calculateDistanceTraveled(speedData) {
    const wheelCircumference = AppConfig.DEFAULT_WHEEL_CIRCUMFERENCE;
    return speedData.reduce((total, item) => {
      return total + (item.pulse_count * wheelCircumference);
    }, 0);
  }

  // Event Listeners
  addEventListener(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
  }

  removeEventListener(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback);
    }
  }

  notifyListeners(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          console.error('[Firebase] Event listener error:', error);
        }
      });
    }
  }

  // Connection monitoring
  async checkConnectionHealth() {
    try {
      // Test Firestore connection
      await firestore().enableNetwork();
      
      // Try a simple read operation
      await firestore().collection('devices').limit(1).get();
      
      return {
        status: 'healthy',
        timestamp: new Date().toISOString(),
        firebase_connected: true,
        config: AppConfig.getAll(),
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        error: error.message,
        timestamp: new Date().toISOString(),
        firebase_connected: false,
      };
    }
  }

  // Cleanup
  unsubscribeAll() {
    this.unsubscribeFunctions.forEach(unsubscribe => {
      try {
        unsubscribe();
      } catch (error) {
        console.error('[Firebase] Error unsubscribing:', error);
      }
    });
    this.unsubscribeFunctions = [];
  }

  async signOut() {
    try {
      await auth().signOut();
      this.unsubscribeAll();
      this.isInitialized = false;
      console.log('[Firebase] Signed out successfully');
    } catch (error) {
      console.error('[Firebase] Sign out error:', error);
    }
  }
}

// Singleton instance
const firebaseService = new FirebaseService();

export default firebaseService;