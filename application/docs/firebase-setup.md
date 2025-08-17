# Firebase Setup Guide

Complete guide for setting up Firebase Firestore with the IoT Speedometer system.

## 🔥 Firebase Project Setup

### Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Create a project"
3. Enter project name: `speedometer-iot`
4. Enable Google Analytics (recommended)
5. Select or create Analytics account
6. Click "Create project"

### Step 2: Enable Firestore Database

1. In Firebase Console, go to "Firestore Database"
2. Click "Create database"
3. Choose "Start in test mode" (we'll configure rules later)
4. Select your preferred location (choose closest to your users)
5. Click "Done"

### Step 3: Enable Authentication

1. Go to "Authentication" in Firebase Console
2. Click "Get started"
3. Go to "Sign-in method" tab
4. Enable "Anonymous" authentication (for mobile app)
5. Optionally enable other methods for admin access

### Step 4: Set Up Cloud Messaging

1. Go to "Cloud Messaging" in Firebase Console
2. No additional setup needed - FCM is enabled by default
3. Note down your Server Key for backend notifications

## 🔧 Configuration Files

### Step 5: Generate Service Account Key

1. Go to Project Settings → Service Accounts
2. Click "Generate new private key"
3. Download the JSON file
4. Rename it to `firebase-service-account-key.json`
5. Place it in your API server directory (`application/api/`)

**⚠️ Security Warning**: Never commit this file to version control!

### Step 6: Get Configuration Keys

#### For Node.js API Server:
```bash
# In Firebase Console → Project Settings → General
PROJECT_ID="your-project-id"
WEB_API_KEY="your-web-api-key"
DATABASE_URL="https://your-project-default-rtdb.firebaseio.com"
```

#### For Mobile App:
1. Add Android app: Package name (e.g., `com.speedometerapp`)
2. Download `google-services.json` → place in `android/app/`
3. Add iOS app: Bundle ID (e.g., `com.speedometerapp`)
4. Download `GoogleService-Info.plist` → place in `ios/`

## 📱 Mobile App Setup

### Step 7: Configure React Native Firebase

1. **Install dependencies** (already in package.json):
```bash
cd application/mobile
npm install
```

2. **Android Configuration**:
```bash
# Add to android/build.gradle (project level)
classpath 'com.google.gms:google-services:4.3.15'

# Add to android/app/build.gradle
apply plugin: 'com.google.gms.google-services'
```

3. **iOS Configuration**:
```bash
cd ios
pod install
```

4. **Update App.js** to initialize Firebase:
```javascript
import '@react-native-firebase/app';
```

## 🖥️ API Server Setup

### Step 8: Configure Node.js Server

1. **Install dependencies**:
```bash
cd application/api
npm install
```

2. **Create .env file**:
```bash
# Server Configuration
PORT=3000
NODE_ENV=production

# Firebase Configuration
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com
FIREBASE_SERVICE_ACCOUNT_KEY=./firebase-service-account-key.json

# Or alternatively, as JSON string:
# FIREBASE_SERVICE_ACCOUNT_KEY={"type":"service_account",...}
```

3. **Start the server**:
```bash
# Development
npm run dev

# Production
npm start
```

## 🛡️ Security Rules Setup

### Step 9: Deploy Firestore Security Rules

1. **Install Firebase CLI**:
```bash
npm install -g firebase-tools
```

2. **Login to Firebase**:
```bash
firebase login
```

3. **Initialize Firebase in project**:
```bash
cd application/firebase
firebase init firestore
```

4. **Deploy rules and indexes**:
```bash
firebase deploy --only firestore:rules
firebase deploy --only firestore:indexes
```

### Step 10: Test Security Rules

Test the rules in Firebase Console:
```javascript
// Test data creation
match /speed_data/test123 {
  // Should allow: authenticated users creating valid data
  allow create: if request.auth != null 
    && request.resource.data.keys().hasAll(['device_id', 'speed']);
}
```

## 🏗️ Database Structure

### Collections Overview

```
📁 devices/
  └── {deviceId}
      ├── id: string
      ├── name: string
      ├── description: string
      ├── active: boolean
      ├── created_at: timestamp
      └── last_seen: timestamp

📁 speed_data/
  └── {documentId}
      ├── device_id: string
      ├── timestamp: string (ISO 8601)
      ├── speed: number (km/h)
      ├── pulse_count: number
      ├── latitude?: number
      ├── longitude?: number
      ├── battery_level?: number
      ├── signal_strength?: number
      └── created_at: timestamp

📁 alerts/
  └── {alertId}
      ├── device_id: string
      ├── alert_type: string
      ├── message: string
      ├── severity: string (info|warning|error)
      ├── acknowledged: boolean
      ├── acknowledged_at?: timestamp
      ├── data?: object
      └── created_at: timestamp

📁 api_keys/
  └── {keyId}
      ├── device_id: string
      ├── api_key: string
      ├── active: boolean
      └── created_at: timestamp

📁 fcm_tokens/
  └── {tokenId}
      ├── user_id: string
      ├── device_id?: string
      ├── token: string
      ├── device_type: string (ios|android)
      ├── active: boolean
      └── created_at: timestamp
```

## 🔌 Raspberry Pi Configuration

### Step 11: Configure Pi Client

1. **Update firebase-config.json**:
```json
{
  "firebase_url": "https://your-project-default-rtdb.firebaseio.com",
  "firebase_project_id": "your-project-id",
  "device_id": "speedometer_001",
  "api_key": "your-web-api-key"
}
```

2. **Install Python dependencies**:
```bash
pip3 install firebase-admin
```

3. **Run the client**:
```bash
sudo python3 firebase_client.py
```

## 🚀 Deployment Options

### Option 1: Firebase Hosting + Cloud Functions

1. **Set up hosting**:
```bash
firebase init hosting
firebase deploy --only hosting
```

2. **Deploy Cloud Functions** (for advanced features):
```bash
firebase init functions
firebase deploy --only functions
```

### Option 2: Traditional Server + Firebase Backend

- Deploy API server to Heroku/AWS/DigitalOcean
- Use Firestore as database backend
- Keep Firebase for real-time features and mobile SDK

## 📊 Monitoring & Analytics

### Step 12: Enable Firebase Analytics

1. **Performance Monitoring**:
```bash
# Add to mobile app
npm install @react-native-firebase/perf
```

2. **Crashlytics** (optional):
```bash
npm install @react-native-firebase/crashlytics
```

3. **Remote Config** (for feature flags):
```bash
npm install @react-native-firebase/remote-config
```

## 🔐 Security Best Practices

### Authentication Strategy
```javascript
// Mobile app - anonymous auth for read access
await auth().signInAnonymously();

// Admin operations - use service account
// Server-side only, never in mobile app
```

### API Key Management
- Store Raspberry Pi API keys in Firestore `api_keys` collection
- Rotate keys regularly
- Use device-specific keys, not global keys

### Data Validation
```javascript
// Firestore rules validate data structure
allow create: if request.resource.data.keys().hasAll(['device_id', 'speed'])
  && request.resource.data.speed is number
  && request.resource.data.speed >= 0
  && request.resource.data.speed <= 300; // Max reasonable speed
```

## 🧪 Testing

### Test Data Creation
```javascript
// Create test device
await firestore().collection('devices').doc('test_device').set({
  name: 'Test Speedometer',
  description: 'Testing device',
  active: true,
  created_at: firestore.FieldValue.serverTimestamp()
});

// Create test speed data
await firestore().collection('speed_data').add({
  device_id: 'test_device',
  timestamp: new Date().toISOString(),
  speed: 25.5,
  pulse_count: 12,
  created_at: firestore.FieldValue.serverTimestamp()
});
```

### Emulator Testing
```bash
# Start Firebase emulators
firebase emulators:start

# Test with emulator
export FIRESTORE_EMULATOR_HOST=localhost:8080
npm run test
```

## 📈 Scaling Considerations

### Query Optimization
- Use composite indexes for complex queries
- Implement pagination for large datasets
- Cache frequently accessed data

### Cost Management
- Monitor read/write operations in Firebase Console
- Implement data retention policies
- Use security rules to prevent abuse

### Performance Tips
```javascript
// Batch writes for efficiency
const batch = firestore().batch();
batch.set(doc1, data1);
batch.set(doc2, data2);
await batch.commit();

// Use onSnapshot for real-time updates
const unsubscribe = collection.onSnapshot(snapshot => {
  // Handle updates
});
```

## 🆘 Troubleshooting

### Common Issues

1. **Permission Denied**:
   - Check Firestore security rules
   - Verify user authentication status
   - Ensure correct collection/document structure

2. **Index Missing**:
   - Firebase will suggest required indexes
   - Add to `firestore.indexes.json`
   - Deploy with `firebase deploy --only firestore:indexes`

3. **Mobile App Build Errors**:
   - Verify `google-services.json` and `GoogleService-Info.plist` placement
   - Check package names match Firebase configuration
   - Clean and rebuild project

4. **Raspberry Pi Connection Issues**:
   - Verify Firebase project ID and API key
   - Check cellular data connection
   - Test with Firebase REST API directly

### Debug Commands
```bash
# Check Firebase project
firebase projects:list

# Validate rules
firebase firestore:rules

# Test security rules
firebase emulators:start --only firestore
```

## 📚 Additional Resources

- [Firebase Documentation](https://firebase.google.com/docs)
- [React Native Firebase](https://rnfirebase.io/)
- [Firestore Security Rules](https://firebase.google.com/docs/firestore/security/get-started)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)

---

**Next Steps:**
1. Create Firebase project and configure services
2. Deploy security rules and indexes
3. Set up mobile app with Firebase SDK
4. Configure API server with service account
5. Test end-to-end data flow
6. Monitor usage and optimize performance

Your Firebase-powered IoT speedometer system is now ready for production use! 🚀