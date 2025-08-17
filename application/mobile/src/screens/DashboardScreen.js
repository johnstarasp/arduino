import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  StyleSheet,
  ScrollView,
  RefreshControl,
  Alert,
  Dimensions,
} from 'react-native';
import {
  Text,
  Card,
  Button,
  Chip,
  FAB,
  Portal,
  Modal,
  List,
  Divider,
} from 'react-native-paper';
import Icon from 'react-native-vector-icons/MaterialIcons';
import LinearGradient from 'react-native-linear-gradient';
import * as Animatable from 'react-native-animatable';

import SpeedChart from '../components/SpeedChart';
import apiService from '../services/ApiService';

const { width: screenWidth } = Dimensions.get('window');

const DashboardScreen = ({ navigation }) => {
  const [devices, setDevices] = useState([]);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [speedData, setSpeedData] = useState([]);
  const [deviceStats, setDeviceStats] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [showDeviceModal, setShowDeviceModal] = useState(false);
  const [realTimeData, setRealTimeData] = useState(null);

  // Load initial data
  useEffect(() => {
    loadInitialData();
    setupWebSocket();
    
    return () => {
      apiService.disconnectWebSocket();
    };
  }, []);

  // Subscribe to selected device updates
  useEffect(() => {
    if (selectedDevice && isConnected) {
      apiService.subscribeToDevice(selectedDevice.id);
      loadDeviceData(selectedDevice.id);
    }
  }, [selectedDevice, isConnected]);

  const loadInitialData = async () => {
    try {
      setIsRefreshing(true);
      
      // Load devices
      const devicesData = await apiService.getDevices();
      setDevices(devicesData);
      
      // Select first device if available
      if (devicesData.length > 0 && !selectedDevice) {
        setSelectedDevice(devicesData[0]);
      }
      
      // Load alerts
      const alertsData = await apiService.getAlerts();
      setAlerts(alertsData);
      
    } catch (error) {
      console.error('Failed to load initial data:', error);
      Alert.alert('Error', 'Failed to load data. Please check your connection.');
    } finally {
      setIsRefreshing(false);
    }
  };

  const loadDeviceData = async (deviceId) => {
    try {
      // Load speed data (last 50 points)
      const speedDataResponse = await apiService.getDeviceData(deviceId, { limit: 50 });
      setSpeedData(speedDataResponse);
      
      // Load device statistics
      const statsResponse = await apiService.getDeviceStats(deviceId, '24h');
      setDeviceStats(statsResponse);
      
    } catch (error) {
      console.error('Failed to load device data:', error);
    }
  };

  const setupWebSocket = async () => {
    try {
      await apiService.connectWebSocket();
      
      apiService.addEventListener('connection', (data) => {
        setIsConnected(data.connected);
      });
      
      apiService.addEventListener('speed_data', (data) => {
        if (selectedDevice && data.device_id === selectedDevice.id) {
          setRealTimeData(data);
          // Update speed data array
          setSpeedData(prev => [...prev.slice(-49), data]);
        }
      });
      
      apiService.addEventListener('alert', (alert) => {
        setAlerts(prev => [alert, ...prev.slice(0, 9)]); // Keep last 10 alerts
        
        // Show notification for critical alerts
        if (alert.severity === 'warning' || alert.severity === 'error') {
          Alert.alert(
            'Alert',
            alert.message,
            [{ text: 'OK' }]
          );
        }
      });
      
    } catch (error) {
      console.error('WebSocket setup failed:', error);
    }
  };

  const onRefresh = useCallback(async () => {
    await loadInitialData();
    if (selectedDevice) {
      await loadDeviceData(selectedDevice.id);
    }
  }, [selectedDevice]);

  const handleDeviceSelect = (device) => {
    setSelectedDevice(device);
    setShowDeviceModal(false);
  };

  const getConnectionStatus = () => {
    if (!selectedDevice) return { color: '#757575', text: 'No Device' };
    if (!isConnected) return { color: '#f44336', text: 'Disconnected' };
    
    const lastSeen = new Date(selectedDevice.last_seen);
    const now = new Date();
    const diffMinutes = (now - lastSeen) / (1000 * 60);
    
    if (diffMinutes < 5) return { color: '#4caf50', text: 'Online' };
    if (diffMinutes < 30) return { color: '#ff9800', text: 'Idle' };
    return { color: '#f44336', text: 'Offline' };
  };

  const renderCurrentSpeed = () => {
    const currentSpeed = realTimeData?.speed || speedData[speedData.length - 1]?.speed || 0;
    
    return (
      <Animatable.View animation="pulse" iterationCount="infinite" duration={2000}>
        <Card style={styles.speedCard}>
          <LinearGradient
            colors={['#2196F3', '#21CBF3']}
            style={styles.speedCardGradient}
          >
            <View style={styles.speedContent}>
              <Icon name="speed" size={40} color="#ffffff" />
              <Text variant="headlineLarge" style={styles.speedValue}>
                {currentSpeed.toFixed(1)}
              </Text>
              <Text variant="titleMedium" style={styles.speedUnit}>
                km/h
              </Text>
            </View>
          </LinearGradient>
        </Card>
      </Animatable.View>
    );
  };

  const renderDeviceInfo = () => {
    const status = getConnectionStatus();
    
    return (
      <Card style={styles.deviceCard}>
        <Card.Content>
          <View style={styles.deviceHeader}>
            <View style={styles.deviceInfo}>
              <Text variant="titleMedium">{selectedDevice?.name || 'No Device Selected'}</Text>
              <Text variant="bodySmall" style={styles.deviceId}>
                {selectedDevice?.id || 'N/A'}
              </Text>
            </View>
            <View style={styles.statusContainer}>
              <Chip 
                mode="outlined" 
                style={[styles.statusChip, { borderColor: status.color }]}
                textStyle={{ color: status.color }}
              >
                {status.text}
              </Chip>
            </View>
          </View>
          
          {deviceStats && (
            <View style={styles.statsRow}>
              <View style={styles.statItem}>
                <Text variant="bodySmall">Max Speed</Text>
                <Text variant="titleMedium" style={styles.statValue}>
                  {deviceStats.stats.max_speed?.toFixed(1) || '0.0'} km/h
                </Text>
              </View>
              <View style={styles.statItem}>
                <Text variant="bodySmall">Avg Speed</Text>
                <Text variant="titleMedium" style={styles.statValue}>
                  {deviceStats.stats.avg_speed?.toFixed(1) || '0.0'} km/h
                </Text>
              </View>
              <View style={styles.statItem}>
                <Text variant="bodySmall">Records</Text>
                <Text variant="titleMedium" style={styles.statValue}>
                  {deviceStats.stats.total_records || 0}
                </Text>
              </View>
            </View>
          )}
        </Card.Content>
      </Card>
    );
  };

  const renderRecentAlerts = () => {
    if (alerts.length === 0) return null;

    return (
      <Card style={styles.alertsCard}>
        <Card.Content>
          <Text variant="titleMedium" style={styles.sectionTitle}>
            Recent Alerts
          </Text>
          {alerts.slice(0, 3).map((alert, index) => (
            <View key={alert.id}>
              <List.Item
                title={alert.message}
                description={new Date(alert.created_at).toLocaleString()}
                left={() => (
                  <Icon 
                    name={alert.severity === 'warning' ? 'warning' : 'info'} 
                    size={24} 
                    color={alert.severity === 'warning' ? '#ff9800' : '#2196F3'} 
                  />
                )}
                titleStyle={styles.alertTitle}
                descriptionStyle={styles.alertDescription}
              />
              {index < 2 && <Divider />}
            </View>
          ))}
          
          {alerts.length > 3 && (
            <Button 
              mode="text" 
              onPress={() => navigation.navigate('Alerts')}
              style={styles.viewAllButton}
            >
              View All Alerts
            </Button>
          )}
        </Card.Content>
      </Card>
    );
  };

  return (
    <View style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        refreshControl={
          <RefreshControl refreshing={isRefreshing} onRefresh={onRefresh} />
        }
      >
        {renderCurrentSpeed()}
        {renderDeviceInfo()}
        
        {speedData.length > 0 && (
          <SpeedChart 
            data={speedData} 
            title="Speed Over Time" 
            period="1h"
          />
        )}
        
        {renderRecentAlerts()}
      </ScrollView>

      <FAB
        icon="swap-horiz"
        style={styles.fab}
        onPress={() => setShowDeviceModal(true)}
        label="Switch Device"
      />

      <Portal>
        <Modal
          visible={showDeviceModal}
          onDismiss={() => setShowDeviceModal(false)}
          contentContainerStyle={styles.modalContent}
        >
          <Text variant="titleLarge" style={styles.modalTitle}>
            Select Device
          </Text>
          {devices.map((device) => (
            <List.Item
              key={device.id}
              title={device.name}
              description={device.id}
              onPress={() => handleDeviceSelect(device)}
              left={() => <Icon name="devices" size={24} />}
              style={[
                styles.deviceItem,
                selectedDevice?.id === device.id && styles.selectedDeviceItem
              ]}
            />
          ))}
          <Button 
            mode="text" 
            onPress={() => setShowDeviceModal(false)}
            style={styles.modalButton}
          >
            Cancel
          </Button>
        </Modal>
      </Portal>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollView: {
    flex: 1,
  },
  speedCard: {
    margin: 16,
    elevation: 8,
    borderRadius: 16,
    overflow: 'hidden',
  },
  speedCardGradient: {
    padding: 24,
    borderRadius: 16,
  },
  speedContent: {
    alignItems: 'center',
  },
  speedValue: {
    color: '#ffffff',
    fontWeight: 'bold',
    marginTop: 8,
  },
  speedUnit: {
    color: '#ffffff',
    opacity: 0.9,
  },
  deviceCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    elevation: 4,
  },
  deviceHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  deviceInfo: {
    flex: 1,
  },
  deviceId: {
    color: '#666',
    marginTop: 4,
  },
  statusContainer: {
    alignItems: 'flex-end',
  },
  statusChip: {
    backgroundColor: 'transparent',
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  statItem: {
    alignItems: 'center',
    flex: 1,
  },
  statValue: {
    color: '#2196F3',
    fontWeight: 'bold',
    marginTop: 4,
  },
  alertsCard: {
    marginHorizontal: 16,
    marginBottom: 16,
    elevation: 4,
  },
  sectionTitle: {
    marginBottom: 16,
    fontWeight: 'bold',
  },
  alertTitle: {
    fontSize: 14,
  },
  alertDescription: {
    fontSize: 12,
    color: '#666',
  },
  viewAllButton: {
    marginTop: 8,
  },
  fab: {
    position: 'absolute',
    margin: 16,
    right: 0,
    bottom: 0,
  },
  modalContent: {
    backgroundColor: 'white',
    padding: 20,
    margin: 20,
    borderRadius: 16,
    maxHeight: '80%',
  },
  modalTitle: {
    textAlign: 'center',
    marginBottom: 16,
    fontWeight: 'bold',
  },
  deviceItem: {
    borderRadius: 8,
    marginBottom: 8,
  },
  selectedDeviceItem: {
    backgroundColor: '#e3f2fd',
  },
  modalButton: {
    marginTop: 16,
  },
});

export default DashboardScreen;