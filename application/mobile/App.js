import React, { useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Provider as PaperProvider, DefaultTheme } from 'react-native-paper';
import { Provider as ReduxProvider } from 'react-redux';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { StatusBar } from 'react-native';

// Screens
import DashboardScreen from './src/screens/DashboardScreen';
import HistoryScreen from './src/screens/HistoryScreen';
import AlertsScreen from './src/screens/AlertsScreen';
import SettingsScreen from './src/screens/SettingsScreen';

// Services
import { requestUserPermission, notificationListener } from './src/services/NotificationService';

const Tab = createBottomTabNavigator();

// Custom theme
const theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: '#2196F3',
    accent: '#21CBF3',
    background: '#f5f5f5',
    surface: '#ffffff',
  },
};

const App = () => {
  useEffect(() => {
    // Request notification permissions and setup listeners
    requestUserPermission();
    const unsubscribe = notificationListener();
    
    return unsubscribe;
  }, []);

  return (
    <PaperProvider theme={theme}>
      <StatusBar barStyle="dark-content" backgroundColor="#ffffff" />
      <NavigationContainer>
        <Tab.Navigator
          screenOptions={({ route }) => ({
            tabBarIcon: ({ focused, color, size }) => {
              let iconName;

              switch (route.name) {
                case 'Dashboard':
                  iconName = 'dashboard';
                  break;
                case 'History':
                  iconName = 'history';
                  break;
                case 'Alerts':
                  iconName = 'notifications';
                  break;
                case 'Settings':
                  iconName = 'settings';
                  break;
                default:
                  iconName = 'circle';
              }

              return <Icon name={iconName} size={size} color={color} />;
            },
            tabBarActiveTintColor: theme.colors.primary,
            tabBarInactiveTintColor: 'gray',
            tabBarStyle: {
              backgroundColor: theme.colors.surface,
              elevation: 8,
              shadowOpacity: 0.1,
              shadowRadius: 4,
              shadowOffset: {
                width: 0,
                height: -2,
              },
            },
            headerStyle: {
              backgroundColor: theme.colors.surface,
              elevation: 4,
              shadowOpacity: 0.1,
              shadowRadius: 4,
              shadowOffset: {
                width: 0,
                height: 2,
              },
            },
            headerTitleStyle: {
              fontWeight: 'bold',
              color: theme.colors.onSurface,
            },
          })}
        >
          <Tab.Screen 
            name="Dashboard" 
            component={DashboardScreen}
            options={{
              headerTitle: 'Speedometer Dashboard',
            }}
          />
          <Tab.Screen 
            name="History" 
            component={HistoryScreen}
            options={{
              headerTitle: 'Speed History',
            }}
          />
          <Tab.Screen 
            name="Alerts" 
            component={AlertsScreen}
            options={{
              headerTitle: 'Alerts & Notifications',
            }}
          />
          <Tab.Screen 
            name="Settings" 
            component={SettingsScreen}
            options={{
              headerTitle: 'Settings',
            }}
          />
        </Tab.Navigator>
      </NavigationContainer>
    </PaperProvider>
  );
};

export default App;