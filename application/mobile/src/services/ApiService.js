import AsyncStorage from '@react-native-async-storage/async-storage';
import io from 'socket.io-client';

class ApiService {
  constructor() {
    this.baseUrl = 'http://localhost:3000'; // Update with your server URL
    this.socket = null;
    this.listeners = new Map();
  }

  async setBaseUrl(url) {
    this.baseUrl = url;
    await AsyncStorage.setItem('api_base_url', url);
  }

  async getBaseUrl() {
    const stored = await AsyncStorage.getItem('api_base_url');
    return stored || this.baseUrl;
  }

  async makeRequest(endpoint, options = {}) {
    try {
      const baseUrl = await this.getBaseUrl();
      const url = `${baseUrl}${endpoint}`;
      
      const defaultOptions = {
        headers: {
          'Content-Type': 'application/json',
        },
      };

      const response = await fetch(url, {
        ...defaultOptions,
        ...options,
        headers: {
          ...defaultOptions.headers,
          ...options.headers,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Device Management
  async getDevices() {
    return this.makeRequest('/api/devices');
  }

  async getDeviceData(deviceId, options = {}) {
    const { limit = 100, offset = 0, from, to } = options;
    let query = `?limit=${limit}&offset=${offset}`;
    
    if (from) query += `&from=${from}`;
    if (to) query += `&to=${to}`;
    
    return this.makeRequest(`/api/devices/${deviceId}/data${query}`);
  }

  async getDeviceStats(deviceId, period = '24h') {
    return this.makeRequest(`/api/devices/${deviceId}/stats?period=${period}`);
  }

  // Alerts
  async getAlerts(deviceId = null, acknowledged = false) {
    let query = `?acknowledged=${acknowledged}`;
    if (deviceId) query += `&device_id=${deviceId}`;
    
    return this.makeRequest(`/api/alerts${query}`);
  }

  async acknowledgeAlert(alertId) {
    return this.makeRequest(`/api/alerts/${alertId}/acknowledge`, {
      method: 'PUT',
    });
  }

  // Real-time WebSocket Connection
  async connectWebSocket() {
    try {
      const baseUrl = await this.getBaseUrl();
      this.socket = io(baseUrl, {
        transports: ['websocket'],
        autoConnect: true,
      });

      this.socket.on('connect', () => {
        console.log('WebSocket connected');
        this.notifyListeners('connection', { connected: true });
      });

      this.socket.on('disconnect', () => {
        console.log('WebSocket disconnected');
        this.notifyListeners('connection', { connected: false });
      });

      this.socket.on('speed_data', (data) => {
        this.notifyListeners('speed_data', data);
      });

      this.socket.on('alert', (alert) => {
        this.notifyListeners('alert', alert);
      });

      return this.socket;
    } catch (error) {
      console.error('WebSocket connection failed:', error);
      throw error;
    }
  }

  disconnectWebSocket() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  subscribeToDevice(deviceId) {
    if (this.socket) {
      this.socket.emit('subscribe_device', deviceId);
    }
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
          console.error('Event listener error:', error);
        }
      });
    }
  }

  // Data Processing Utilities
  processSpeedData(rawData) {
    return rawData.map(item => ({
      ...item,
      timestamp: new Date(item.timestamp),
      created_at: new Date(item.created_at),
    }));
  }

  calculateDistanceTraveled(speedData, wheelCircumference = 2.1) {
    return speedData.reduce((total, item) => {
      return total + (item.pulse_count * wheelCircumference);
    }, 0);
  }

  groupDataByHour(speedData) {
    const grouped = {};
    
    speedData.forEach(item => {
      const hour = new Date(item.timestamp).getHours();
      if (!grouped[hour]) {
        grouped[hour] = [];
      }
      grouped[hour].push(item);
    });

    return Object.keys(grouped).map(hour => ({
      hour: parseInt(hour),
      avgSpeed: grouped[hour].reduce((sum, item) => sum + item.speed, 0) / grouped[hour].length,
      maxSpeed: Math.max(...grouped[hour].map(item => item.speed)),
      count: grouped[hour].length,
    }));
  }

  // Health Check
  async checkServerHealth() {
    try {
      const response = await this.makeRequest('/health');
      return response;
    } catch (error) {
      return { status: 'unhealthy', error: error.message };
    }
  }
}

// Singleton instance
const apiService = new ApiService();
export default apiService;