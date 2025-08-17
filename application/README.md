# IoT Speedometer with Firebase

Complete IoT speedometer system using Firebase Firestore for real-time data synchronization and React Native mobile app.

## 🚀 System Overview

This project transforms the SMS-based speedometer into a modern cloud-connected IoT system with:

- **Raspberry Pi Client**: SIM7070G cellular data communication with Firebase integration
- **Firebase Firestore**: Real-time cloud database with offline support
- **Node.js API Server**: Optional REST API layer for additional features
- **React Native Mobile App**: Cross-platform app with real-time updates and push notifications
- **Firebase Cloud Messaging**: Push notifications for alerts and updates

## 🔥 Why Firebase?

**Real-time Synchronization**: Firestore provides instant data updates across all devices

**Offline Support**: Mobile app works offline and syncs when reconnected

**Scalability**: Auto-scaling cloud infrastructure handles any load

**Security**: Built-in authentication and granular security rules

**Cost-Effective**: Pay only for what you use, free tier available

**Easy Deployment**: No server management required

## 📁 Project Structure

```
application/
├── raspberry-pi/          # IoT device code
│   ├── firebase_client.py         # Firebase-integrated client
│   ├── cellular_data_client.py    # Alternative API client
│   ├── firebase-config.json       # Firebase configuration
│   └── requirements.txt           # Python dependencies
├── api/                   # Optional Node.js API server
│   ├── server-firebase.js         # Firebase-integrated server
│   ├── package.json               # Dependencies with Firebase Admin
│   └── scripts/                   # Utility scripts
├── mobile/                # React Native mobile app
│   ├── src/
│   │   ├── services/
│   │   │   ├── FirebaseService.js  # Firebase integration
│   │   │   └── NotificationService.js
│   │   ├── components/            # UI components
│   │   └── screens/               # App screens
│   ├── App.js                     # Firebase-enabled app
│   └── package.json               # Dependencies with Firebase SDK
├── firebase/              # Firebase configuration
│   ├── firestore.rules            # Security rules
│   ├── firestore.indexes.json     # Database indexes
│   └── firebase.json              # Firebase project config
└── docs/                  # Documentation
    ├── firebase-setup.md          # Complete Firebase setup guide
    └── deployment.md              # Deployment options
```

## ⚡ Quick Start

### 1. Set Up Firebase Project

1. **Create Firebase Project**:
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Create new project: `speedometer-iot`
   - Enable Firestore Database
   - Enable Authentication (Anonymous)
   - Enable Cloud Messaging

2. **Download Configuration**:
   - Service Account Key → `application/api/firebase-service-account-key.json`
   - Android `google-services.json` → `application/mobile/android/app/`
   - iOS `GoogleService-Info.plist` → `application/mobile/ios/`

3. **Deploy Security Rules**:
```bash
cd application/firebase
firebase login
firebase init firestore
firebase deploy --only firestore:rules,firestore:indexes
```

### 2. Configure Raspberry Pi

1. **Update Firebase configuration**:
```json
{
  "firebase_project_id": "your-project-id",
  "firebase_url": "https://your-project-default-rtdb.firebaseio.com",
  "device_id": "speedometer_001",
  "api_key": "your-firebase-web-api-key"
}
```

2. **Install dependencies**:
```bash
cd application/raspberry-pi
pip3 install -r requirements.txt
```

3. **Run Firebase client**:
```bash
sudo python3 firebase_client.py
```

### 3. Set Up Mobile App

1. **Install dependencies**:
```bash
cd application/mobile
npm install
```

2. **Configure Firebase**:
   - Place configuration files in correct directories
   - Update bundle/package identifiers to match Firebase

3. **Run the app**:
```bash
# iOS
cd ios && pod install && cd ..
npx react-native run-ios

# Android
npx react-native run-android
```

### 4. Optional: API Server

For additional features like analytics and admin operations:

```bash
cd application/api
npm install
cp .env.example .env
# Configure Firebase credentials in .env
npm start
```

## 🌊 Data Flow Architecture

```
📱 Raspberry Pi
    ↓ (Cellular Data)
🔥 Firebase Firestore
    ↓ (Real-time Sync)
📱 Mobile App + 🔔 Push Notifications
```

**Direct Firebase Integration**:
1. Raspberry Pi sends data directly to Firestore via REST API
2. Mobile app receives real-time updates via Firebase SDK
3. Push notifications triggered by Firebase Cloud Functions
4. All data synchronized in real-time across devices

## 📊 Firebase Collections

### Core Collections

```javascript
// Devices
devices/{deviceId} {
  name: "Primary Speedometer",
  description: "Main device",
  active: true,
  created_at: timestamp,
  last_seen: timestamp
}

// Speed Data (Real-time)
speed_data/{docId} {
  device_id: "speedometer_001",
  timestamp: "2023-08-17T10:30:00Z",
  speed: 25.3,
  pulse_count: 12,
  battery_level: 85,
  signal_strength: -65,
  created_at: timestamp
}

// Alerts
alerts/{alertId} {
  device_id: "speedometer_001",
  alert_type: "high_speed",
  message: "Speed 55 km/h exceeds limit",
  severity: "warning",
  acknowledged: false,
  created_at: timestamp
}
```

## 📱 Mobile App Features

### Real-time Dashboard
- **Live Speed Display**: Current speed with animated gauge
- **Speed Charts**: Historical data with interactive charts
- **Device Status**: Battery, signal strength, connection status
- **Real-time Updates**: Instant data synchronization

### Push Notifications
- **Speed Alerts**: Customizable speed thresholds
- **Device Alerts**: Low battery, poor signal, offline status
- **Trip Summaries**: Automatic trip detection and statistics

### Multi-device Support
- **Device Switching**: Manage multiple speedometer devices
- **Device History**: Per-device statistics and trends
- **Offline Mode**: Cached data when network unavailable

## 🔐 Security Features

### Firebase Security Rules
```javascript
// Read access for authenticated users
allow read: if request.auth != null;

// Validated data creation
allow create: if request.auth != null 
  && request.resource.data.keys().hasAll(['device_id', 'speed'])
  && request.resource.data.speed is number;
```

### Authentication Strategy
- **Anonymous Auth**: Mobile app users (read-only access)
- **Service Accounts**: Raspberry Pi devices (write access)
- **Admin SDK**: Server operations (full access)

## 🚀 Deployment Options

### 1. Firebase-Only Deployment (Recommended)
```bash
# Deploy Firestore rules and indexes
firebase deploy --only firestore

# Optional: Deploy Cloud Functions for advanced features
firebase deploy --only functions

# Optional: Deploy hosting for web dashboard
firebase deploy --only hosting
```

**Advantages**:
- ✅ Fully managed infrastructure
- ✅ Auto-scaling
- ✅ Built-in security
- ✅ Real-time synchronization
- ✅ Offline support

### 2. Hybrid Deployment
- **Firebase**: Real-time data and mobile app backend
- **Custom Server**: Additional analytics and integrations
- **Best of Both**: Firebase features + custom logic

### 3. Traditional Server + Firebase
- **API Server**: Heroku/AWS/DigitalOcean
- **Database**: Firebase Firestore
- **Mobile**: Firebase SDK for real-time features

## 💰 Cost Estimation

### Firebase Pricing (Free Tier Included)

**Firestore Operations** (Free: 50K reads, 20K writes/day):
- 1 device, 30-second intervals = ~2,880 writes/day
- Well within free tier for single device

**Cloud Messaging** (Free):
- Unlimited notifications

**Hosting** (Free: 10GB storage, 360MB/day transfer):
- More than sufficient for documentation/dashboard

**Estimated Monthly Cost**:
- **Single Device**: Free
- **10 Devices**: ~$5-10/month
- **100 Devices**: ~$50-100/month

## 🧪 Testing

### Firebase Emulator Suite
```bash
# Start local Firebase emulators
firebase emulators:start

# Test with local Firestore
export FIRESTORE_EMULATOR_HOST=localhost:8080
npm test
```

### End-to-End Testing
1. **Raspberry Pi**: Send test data to Firebase
2. **Mobile App**: Verify real-time updates
3. **Notifications**: Test alert triggers
4. **Offline Mode**: Test app offline functionality

## 📈 Monitoring & Analytics

### Firebase Console
- **Real-time Database Activity**: Monitor reads/writes
- **Performance**: App performance metrics
- **Crashlytics**: Error tracking and reporting
- **Analytics**: User engagement and app usage

### Custom Analytics
```javascript
// Track custom events
await analytics().logEvent('speed_alert_triggered', {
  device_id: 'speedometer_001',
  speed: 55.2,
  threshold: 50
});
```

## 🔧 Advanced Features

### 1. Cloud Functions for Server Logic
```javascript
// Trigger on new speed data
exports.processSpeedData = functions.firestore
  .document('speed_data/{docId}')
  .onCreate(async (snap, context) => {
    const data = snap.data();
    
    // Check for alerts
    if (data.speed > 50) {
      await sendSpeedAlert(data);
    }
    
    // Update trip statistics
    await updateTripStats(data);
  });
```

### 2. Real-time Trip Detection
- Automatic trip start/stop detection
- Distance and duration calculation
- Trip summaries and statistics

### 3. Geofencing (with GPS module)
- Speed zone alerts
- Location-based notifications
- Route tracking and analysis

### 4. Fleet Management
- Multiple device monitoring
- Device health monitoring
- Centralized alert management

## 🆘 Troubleshooting

### Common Issues

**1. Firestore Permission Denied**
```bash
# Check security rules
firebase firestore:rules

# Verify authentication
console.log(auth().currentUser);
```

**2. Real-time Updates Not Working**
- Verify internet connection
- Check Firestore listeners setup
- Ensure proper authentication

**3. Push Notifications Not Received**
- Check FCM token registration
- Verify notification permissions
- Test with Firebase Console

### Debug Tools
```javascript
// Enable Firestore debug logging
firestore().settings({
  persistence: true,
  cacheSizeBytes: firestore.CACHE_SIZE_UNLIMITED,
});

// Monitor connection state
firestore().enableNetwork();
firestore().disableNetwork();
```

## 📚 Documentation

- **[Complete Firebase Setup Guide](docs/firebase-setup.md)**: Step-by-step Firebase configuration
- **[Deployment Guide](docs/deployment.md)**: Various deployment options
- **[API Reference](docs/api-reference.md)**: Firebase service methods
- **[Security Guide](docs/security.md)**: Authentication and security rules

## 🎯 Next Steps

1. **Create Firebase Project**: Follow [firebase-setup.md](docs/firebase-setup.md)
2. **Deploy Security Rules**: Configure access permissions
3. **Set Up Mobile App**: Install Firebase SDK and configure
4. **Configure Raspberry Pi**: Direct Firebase integration
5. **Test Real-time Flow**: End-to-end testing
6. **Enable Push Notifications**: Configure FCM
7. **Monitor Performance**: Use Firebase Analytics

---

**Firebase Powers Everything** 🔥
- ⚡ Real-time data synchronization
- 📱 Native mobile SDK integration  
- 🔐 Built-in security and authentication
- 📊 Automatic scaling and performance
- 💰 Cost-effective pay-as-you-scale pricing
- 🌍 Global CDN and edge locations

Your Firebase-powered IoT speedometer system is ready for global deployment! 🚀