import Config from 'react-native-config';

class AppConfig {
  // App Configuration
  static get APP_NAME() {
    return Config.APP_NAME || 'SpeedometerApp';
  }

  static get APP_VERSION() {
    return Config.APP_VERSION || '1.0.0';
  }

  static get ENVIRONMENT() {
    return Config.ENVIRONMENT || 'development';
  }

  static get IS_DEVELOPMENT() {
    return this.ENVIRONMENT === 'development';
  }

  static get IS_PRODUCTION() {
    return this.ENVIRONMENT === 'production';
  }

  // Firebase Configuration
  static get FIREBASE_CONFIG() {
    return {
      projectId: Config.FIREBASE_PROJECT_ID,
      apiKey: Config.FIREBASE_API_KEY,
      authDomain: Config.FIREBASE_AUTH_DOMAIN,
      databaseURL: Config.FIREBASE_DATABASE_URL,
      storageBucket: Config.FIREBASE_STORAGE_BUCKET,
      messagingSenderId: Config.FIREBASE_MESSAGING_SENDER_ID,
      appId: Config.FIREBASE_APP_ID,
      measurementId: Config.FIREBASE_MEASUREMENT_ID,
    };
  }

  // API Configuration
  static get API_BASE_URL() {
    return Config.API_BASE_URL || 'http://localhost:3000';
  }

  static get API_TIMEOUT() {
    return parseInt(Config.API_TIMEOUT) || 30000;
  }

  static get WEBSOCKET_URL() {
    return Config.WEBSOCKET_URL || 'ws://localhost:3000';
  }

  // Device Configuration
  static get DEFAULT_DEVICE_ID() {
    return Config.DEFAULT_DEVICE_ID || 'speedometer_001';
  }

  static get DEFAULT_WHEEL_CIRCUMFERENCE() {
    return parseFloat(Config.DEFAULT_WHEEL_CIRCUMFERENCE) || 2.1;
  }

  static get DEFAULT_SPEED_THRESHOLD() {
    return parseInt(Config.DEFAULT_SPEED_THRESHOLD) || 50;
  }

  static get DEFAULT_DATA_INTERVAL() {
    return parseInt(Config.DEFAULT_DATA_INTERVAL) || 30;
  }

  // Notification Configuration
  static get ENABLE_PUSH_NOTIFICATIONS() {
    return Config.ENABLE_PUSH_NOTIFICATIONS === 'true';
  }

  static get NOTIFICATION_SOUND() {
    return Config.NOTIFICATION_SOUND || 'default';
  }

  static get VIBRATION_ENABLED() {
    return Config.VIBRATION_ENABLED !== 'false';
  }

  static get SPEED_ALERT_THRESHOLD() {
    return parseInt(Config.SPEED_ALERT_THRESHOLD) || 50;
  }

  static get BATTERY_ALERT_THRESHOLD() {
    return parseInt(Config.BATTERY_ALERT_THRESHOLD) || 20;
  }

  // Chart Configuration
  static get CHART_DATA_POINTS_LIMIT() {
    return parseInt(Config.CHART_DATA_POINTS_LIMIT) || 50;
  }

  static get CHART_REFRESH_INTERVAL() {
    return parseInt(Config.CHART_REFRESH_INTERVAL) || 5000;
  }

  static get CHART_ANIMATION_ENABLED() {
    return Config.CHART_ANIMATION_ENABLED !== 'false';
  }

  // Offline Configuration
  static get CACHE_SIZE_LIMIT() {
    return parseInt(Config.CACHE_SIZE_LIMIT) || 100;
  }

  static get OFFLINE_DATA_RETENTION_DAYS() {
    return parseInt(Config.OFFLINE_DATA_RETENTION_DAYS) || 7;
  }

  static get AUTO_SYNC_ENABLED() {
    return Config.AUTO_SYNC_ENABLED !== 'false';
  }

  // Debug Configuration
  static get DEBUG_MODE() {
    return Config.DEBUG_MODE === 'true';
  }

  static get LOG_LEVEL() {
    return Config.LOG_LEVEL || 'info';
  }

  static get CRASH_REPORTING_ENABLED() {
    return Config.CRASH_REPORTING_ENABLED !== 'false';
  }

  static get ANALYTICS_ENABLED() {
    return Config.ANALYTICS_ENABLED !== 'false';
  }

  // Feature Flags
  static get ENABLE_MAPS() {
    return Config.ENABLE_MAPS !== 'false';
  }

  static get ENABLE_TRIP_DETECTION() {
    return Config.ENABLE_TRIP_DETECTION !== 'false';
  }

  static get ENABLE_GEOFENCING() {
    return Config.ENABLE_GEOFENCING === 'true';
  }

  static get ENABLE_FLEET_MANAGEMENT() {
    return Config.ENABLE_FLEET_MANAGEMENT === 'true';
  }

  // Security Configuration
  static get API_KEY_VALIDATION() {
    return Config.API_KEY_VALIDATION !== 'false';
  }

  static get SSL_PINNING_ENABLED() {
    return Config.SSL_PINNING_ENABLED === 'true';
  }

  static get BIOMETRIC_AUTH_ENABLED() {
    return Config.BIOMETRIC_AUTH_ENABLED === 'true';
  }

  // UI Configuration
  static get THEME_MODE() {
    return Config.THEME_MODE || 'auto';
  }

  static get PRIMARY_COLOR() {
    return Config.PRIMARY_COLOR || '#2196F3';
  }

  static get ACCENT_COLOR() {
    return Config.ACCENT_COLOR || '#21CBF3';
  }

  static get DARK_MODE_ENABLED() {
    return Config.DARK_MODE_ENABLED !== 'false';
  }

  // Performance Configuration
  static get IMAGE_CACHE_SIZE() {
    return parseInt(Config.IMAGE_CACHE_SIZE) || 50;
  }

  static get NETWORK_TIMEOUT() {
    return parseInt(Config.NETWORK_TIMEOUT) || 10000;
  }

  static get RETRY_ATTEMPTS() {
    return parseInt(Config.RETRY_ATTEMPTS) || 3;
  }

  static get RETRY_DELAY() {
    return parseInt(Config.RETRY_DELAY) || 1000;
  }

  // Utility Methods
  static validate() {
    const required = [
      'FIREBASE_PROJECT_ID',
      'FIREBASE_API_KEY',
    ];

    const missing = required.filter(key => !Config[key]);
    
    if (missing.length > 0) {
      console.error('Missing required environment variables:', missing);
      return false;
    }

    return true;
  }

  static getAll() {
    return {
      app: {
        name: this.APP_NAME,
        version: this.APP_VERSION,
        environment: this.ENVIRONMENT,
        isDevelopment: this.IS_DEVELOPMENT,
        isProduction: this.IS_PRODUCTION,
      },
      firebase: this.FIREBASE_CONFIG,
      api: {
        baseUrl: this.API_BASE_URL,
        timeout: this.API_TIMEOUT,
        websocketUrl: this.WEBSOCKET_URL,
      },
      device: {
        defaultDeviceId: this.DEFAULT_DEVICE_ID,
        defaultWheelCircumference: this.DEFAULT_WHEEL_CIRCUMFERENCE,
        defaultSpeedThreshold: this.DEFAULT_SPEED_THRESHOLD,
        defaultDataInterval: this.DEFAULT_DATA_INTERVAL,
      },
      notifications: {
        enabled: this.ENABLE_PUSH_NOTIFICATIONS,
        sound: this.NOTIFICATION_SOUND,
        vibration: this.VIBRATION_ENABLED,
        speedThreshold: this.SPEED_ALERT_THRESHOLD,
        batteryThreshold: this.BATTERY_ALERT_THRESHOLD,
      },
      chart: {
        dataPointsLimit: this.CHART_DATA_POINTS_LIMIT,
        refreshInterval: this.CHART_REFRESH_INTERVAL,
        animationEnabled: this.CHART_ANIMATION_ENABLED,
      },
      debug: {
        debugMode: this.DEBUG_MODE,
        logLevel: this.LOG_LEVEL,
        crashReporting: this.CRASH_REPORTING_ENABLED,
        analytics: this.ANALYTICS_ENABLED,
      },
      features: {
        maps: this.ENABLE_MAPS,
        tripDetection: this.ENABLE_TRIP_DETECTION,
        geofencing: this.ENABLE_GEOFENCING,
        fleetManagement: this.ENABLE_FLEET_MANAGEMENT,
      },
      security: {
        apiKeyValidation: this.API_KEY_VALIDATION,
        sslPinning: this.SSL_PINNING_ENABLED,
        biometricAuth: this.BIOMETRIC_AUTH_ENABLED,
      },
      ui: {
        themeMode: this.THEME_MODE,
        primaryColor: this.PRIMARY_COLOR,
        accentColor: this.ACCENT_COLOR,
        darkMode: this.DARK_MODE_ENABLED,
      },
      performance: {
        imageCacheSize: this.IMAGE_CACHE_SIZE,
        networkTimeout: this.NETWORK_TIMEOUT,
        retryAttempts: this.RETRY_ATTEMPTS,
        retryDelay: this.RETRY_DELAY,
      },
    };
  }

  static log() {
    if (this.DEBUG_MODE) {
      console.log('📱 App Configuration:', JSON.stringify(this.getAll(), null, 2));
    }
  }
}

export default AppConfig;