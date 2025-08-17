import messaging from '@react-native-firebase/messaging';
import PushNotification from 'react-native-push-notification';
import { Platform, Alert, PermissionsAndroid } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

class NotificationService {
  constructor() {
    this.isInitialized = false;
    this.setupNotificationChannels();
  }

  setupNotificationChannels() {
    // Create notification channels for Android
    PushNotification.createChannel(
      {
        channelId: 'speedometer-alerts',
        channelName: 'Speedometer Alerts',
        channelDescription: 'Important alerts from your speedometer device',
        importance: 4, // HIGH
        vibrate: true,
        sound: 'default',
      },
      (created) => console.log(`Speedometer alerts channel created: ${created}`)
    );

    PushNotification.createChannel(
      {
        channelId: 'speedometer-updates',
        channelName: 'Speedometer Updates',
        channelDescription: 'Regular updates from your speedometer device',
        importance: 3, // DEFAULT
        vibrate: false,
        sound: 'default',
      },
      (created) => console.log(`Speedometer updates channel created: ${created}`)
    );

    // Configure PushNotification
    PushNotification.configure({
      onRegister: (token) => {
        console.log('Local notification token:', token);
        this.saveLocalToken(token.token);
      },

      onNotification: (notification) => {
        console.log('Local notification received:', notification);
        
        if (notification.userInteraction) {
          // User tapped notification
          this.handleNotificationTap(notification);
        }

        // Required on iOS for local notifications
        if (Platform.OS === 'ios') {
          notification.finish();
        }
      },

      onAction: (notification) => {
        console.log('Notification action received:', notification.action);
      },

      onRegistrationError: (err) => {
        console.error('Local notification registration error:', err);
      },

      permissions: {
        alert: true,
        badge: true,
        sound: true,
      },

      popInitialNotification: true,
      requestPermissions: Platform.OS === 'ios',
    });
  }

  async requestUserPermission() {
    try {
      // Request Firebase messaging permission
      const authStatus = await messaging().requestPermission();
      const enabled =
        authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;

      if (enabled) {
        console.log('Firebase messaging permission granted');
        await this.getFCMToken();
        return true;
      } else {
        console.log('Firebase messaging permission denied');
        return false;
      }
    } catch (error) {
      console.error('Error requesting notification permission:', error);
      return false;
    }
  }

  async getFCMToken() {
    try {
      const fcmToken = await messaging().getToken();
      if (fcmToken) {
        console.log('FCM Token:', fcmToken);
        await this.saveFCMToken(fcmToken);
        return fcmToken;
      }
    } catch (error) {
      console.error('Error getting FCM token:', error);
    }
    return null;
  }

  async saveFCMToken(token) {
    try {
      await AsyncStorage.setItem('fcm_token', token);
      // TODO: Send token to your server
      // await apiService.registerFCMToken(token);
    } catch (error) {
      console.error('Error saving FCM token:', error);
    }
  }

  async saveLocalToken(token) {
    try {
      await AsyncStorage.setItem('local_notification_token', token);
    } catch (error) {
      console.error('Error saving local notification token:', error);
    }
  }

  setupNotificationListeners() {
    // Listen for FCM messages when app is in foreground
    const unsubscribeOnMessage = messaging().onMessage(async (remoteMessage) => {
      console.log('FCM message received in foreground:', remoteMessage);
      
      // Show local notification when app is in foreground
      this.showLocalNotification({
        title: remoteMessage.notification?.title || 'Speedometer Alert',
        message: remoteMessage.notification?.body || 'New alert from your device',
        data: remoteMessage.data,
        channelId: this.getChannelIdFromData(remoteMessage.data),
      });
    });

    // Listen for background/quit state messages
    messaging().onNotificationOpenedApp((remoteMessage) => {
      console.log('Notification caused app to open from background:', remoteMessage);
      this.handleNotificationTap(remoteMessage);
    });

    // Check if app was opened by a notification when it was quit
    messaging()
      .getInitialNotification()
      .then((remoteMessage) => {
        if (remoteMessage) {
          console.log('Notification caused app to open from quit state:', remoteMessage);
          this.handleNotificationTap(remoteMessage);
        }
      });

    // Listen for token refresh
    const unsubscribeOnTokenRefresh = messaging().onTokenRefresh((token) => {
      console.log('FCM token refreshed:', token);
      this.saveFCMToken(token);
    });

    return () => {
      unsubscribeOnMessage();
      unsubscribeOnTokenRefresh();
    };
  }

  showLocalNotification({ title, message, data = {}, channelId = 'speedometer-alerts' }) {
    PushNotification.localNotification({
      channelId,
      title,
      message,
      playSound: true,
      soundName: 'default',
      vibrate: channelId === 'speedometer-alerts',
      vibration: 300,
      userInfo: data,
      actions: this.getNotificationActions(data),
    });
  }

  getChannelIdFromData(data) {
    if (data?.alert_type === 'high_speed' || data?.severity === 'warning') {
      return 'speedometer-alerts';
    }
    return 'speedometer-updates';
  }

  getNotificationActions(data) {
    const actions = ['View'];
    
    if (data?.alert_id) {
      actions.push('Acknowledge');
    }
    
    return actions;
  }

  handleNotificationTap(notification) {
    // Navigate to appropriate screen based on notification data
    const data = notification.data || notification.userInfo || {};
    
    if (data.alert_id) {
      // Navigate to alerts screen
      // navigation.navigate('Alerts', { alertId: data.alert_id });
    } else if (data.device_id) {
      // Navigate to device dashboard
      // navigation.navigate('Dashboard', { deviceId: data.device_id });
    }
  }

  // Speed-specific notifications
  showSpeedAlert(speed, threshold) {
    this.showLocalNotification({
      title: '⚠️ High Speed Alert',
      message: `Speed ${speed} km/h exceeds limit of ${threshold} km/h`,
      channelId: 'speedometer-alerts',
      data: {
        type: 'speed_alert',
        speed,
        threshold,
      },
    });
  }

  showBatteryAlert(batteryLevel) {
    this.showLocalNotification({
      title: '🔋 Low Battery',
      message: `Device battery at ${batteryLevel}%`,
      channelId: 'speedometer-alerts',
      data: {
        type: 'battery_alert',
        battery_level: batteryLevel,
      },
    });
  }

  showConnectionAlert(deviceName) {
    this.showLocalNotification({
      title: '📡 Device Offline',
      message: `${deviceName} has gone offline`,
      channelId: 'speedometer-alerts',
      data: {
        type: 'connection_alert',
        device_name: deviceName,
      },
    });
  }

  showTripSummary(distance, avgSpeed, maxSpeed, duration) {
    this.showLocalNotification({
      title: '🏁 Trip Completed',
      message: `${distance.toFixed(1)} km, avg ${avgSpeed.toFixed(1)} km/h, max ${maxSpeed.toFixed(1)} km/h`,
      channelId: 'speedometer-updates',
      data: {
        type: 'trip_summary',
        distance,
        avg_speed: avgSpeed,
        max_speed: maxSpeed,
        duration,
      },
    });
  }

  // Scheduled notifications
  scheduleSpeedReminder(intervalMinutes = 60) {
    PushNotification.localNotificationSchedule({
      channelId: 'speedometer-updates',
      title: '📊 Speed Check',
      message: 'Check your current speed and statistics',
      date: new Date(Date.now() + intervalMinutes * 60 * 1000),
      repeatType: 'time',
      repeatTime: intervalMinutes * 60 * 1000,
      userInfo: {
        type: 'speed_reminder',
      },
    });
  }

  cancelAllLocalNotifications() {
    PushNotification.cancelAllLocalNotifications();
  }

  cancelNotification(id) {
    PushNotification.cancelLocalNotifications({ id });
  }

  // Settings
  async getNotificationSettings() {
    try {
      const settings = await AsyncStorage.getItem('notification_settings');
      return settings ? JSON.parse(settings) : {
        speedAlerts: true,
        batteryAlerts: true,
        connectionAlerts: true,
        tripSummaries: true,
        regularUpdates: false,
        speedThreshold: 50, // km/h
        batteryThreshold: 20, // %
      };
    } catch (error) {
      console.error('Error getting notification settings:', error);
      return {};
    }
  }

  async updateNotificationSettings(settings) {
    try {
      await AsyncStorage.setItem('notification_settings', JSON.stringify(settings));
      return true;
    } catch (error) {
      console.error('Error updating notification settings:', error);
      return false;
    }
  }

  async checkNotificationPermissions() {
    if (Platform.OS === 'android') {
      const granted = await PermissionsAndroid.check(
        PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS
      );
      return granted;
    } else {
      const authStatus = await messaging().hasPermission();
      return authStatus === messaging.AuthorizationStatus.AUTHORIZED;
    }
  }
}

// Singleton instance
const notificationService = new NotificationService();

// Exported functions for easy use
export const requestUserPermission = () => notificationService.requestUserPermission();
export const notificationListener = () => notificationService.setupNotificationListeners();
export const showSpeedAlert = (speed, threshold) => notificationService.showSpeedAlert(speed, threshold);
export const showBatteryAlert = (batteryLevel) => notificationService.showBatteryAlert(batteryLevel);
export const showConnectionAlert = (deviceName) => notificationService.showConnectionAlert(deviceName);
export const showTripSummary = (distance, avgSpeed, maxSpeed, duration) => 
  notificationService.showTripSummary(distance, avgSpeed, maxSpeed, duration);

export default notificationService;