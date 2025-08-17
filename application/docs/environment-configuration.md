# Environment Configuration Guide

Complete guide for configuring environment variables and testing SIM7070G connectivity.

## 🧪 SIM7070G Internet Testing

### Quick Test Scripts

Two test scripts are available to verify SIM7070G cellular data connectivity:

#### 1. Simple HTTP Test (Recommended for quick testing)

```bash
cd application/raspberry-pi
sudo python3 simple_http_test.py
```

**Features:**
- Quick connectivity check (30 seconds)
- Full HTTP test (2-3 minutes)
- Interactive mode selection
- Minimal setup required

**Example Output:**
```
🌐 Simple SIM7070G HTTP Test
========================================
[1/8] Connecting to SIM7070G...
✅ Serial connected
[2/8] Testing basic communication...
✅ SIM module responding
[3/8] Checking network registration...
✅ Network registered
[4/8] Setting APN...
✅ APN configured
[5/8] Attaching to GPRS...
✅ GPRS attached
[6/8] Initializing HTTP...
✅ HTTP initialized
[7/8] Setting HTTP parameters...
✅ HTTP parameters set
[8/8] Making HTTP request...
✅ HTTP request successful!

📄 HTTP Response (first 200 chars):
----------------------------------------
{
  "args": {},
  "headers": {
    "Host": "httpbin.org",
    "User-Agent": "curl/7.68.0"
  },
  "origin": "203.0.113.1",
  "url": "http://httpbin.org/get"
}
----------------------------------------
🎉 SUCCESS: Internet connectivity is working!
```

#### 2. Comprehensive Test (For detailed diagnostics)

```bash
cd application/raspberry-pi
sudo python3 test_sim7070g_internet.py
```

**Features:**
- Complete diagnostic suite
- Signal strength analysis
- Multiple HTTP endpoint tests
- DNS resolution testing
- Detailed error reporting

**Example Summary:**
```
📊 TEST SUMMARY
==================================================
Basic Communication          ✅ PASS
Sim Card                     ✅ PASS
Network Registration         ✅ PASS
Signal Quality              ✅ PASS
Data Connection             ✅ PASS
Dns Resolution              ✅ PASS
Http Test 1                 ✅ PASS
Http Test 2                 ✅ PASS
Http Test 3                 ✅ PASS

Overall: 9/9 tests passed
🎉 ALL TESTS PASSED - Internet connectivity is working!
```

### Common Issues and Solutions

#### Network Registration Failed
```bash
# Check SIM card
AT+CPIN?
# Should return: +CPIN: READY

# Check network operators
AT+COPS?
# Should show registered network
```

#### Poor Signal Quality
```bash
# Check signal strength
AT+CSQ
# Response: +CSQ: <rssi>,<ber>
# rssi > 10 is acceptable, > 15 is good
```

#### APN Configuration Issues
```bash
# Try different APNs for Greek carriers:
AT+CGDCONT=1,"IP","internet"        # Generic
AT+CGDCONT=1,"IP","cosmote"         # COSMOTE
AT+CGDCONT=1,"IP","data.cosmote.gr" # COSMOTE specific
AT+CGDCONT=1,"IP","gint.b-online.gr" # WIND
```

## 📱 Mobile App Environment Configuration

### Setup Process

1. **Install react-native-config**:
```bash
cd application/mobile
npm install react-native-config
```

2. **iOS Configuration** (if using iOS):
```bash
cd ios
pod install
```

3. **Android Configuration**:
Add to `android/settings.gradle`:
```gradle
include ':react-native-config'
project(':react-native-config').projectDir = new File(rootProject.projectDir, '../node_modules/react-native-config/android')
```

### Environment Files

#### Development Environment (`.env.development`)
```bash
# Copy development environment
npm run env:dev

# Or manually
cp .env.development .env
```

**Development Features:**
- Local API server (`http://localhost:3000`)
- Debug mode enabled
- Faster refresh intervals
- Test device IDs
- Reduced security features

#### Production Environment (`.env.production`)
```bash
# Copy production environment
npm run env:prod

# Or manually
cp .env.production .env
```

**Production Features:**
- Production Firebase project
- SSL pinning enabled
- Analytics and crash reporting
- Biometric authentication
- Optimized performance settings

### Configuration Categories

#### 1. Firebase Configuration
```bash
# Required for Firebase integration
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_API_KEY=your-web-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_DATABASE_URL=https://your-project-default-rtdb.firebaseio.com
```

#### 2. API Server Configuration
```bash
# Optional if using custom backend
API_BASE_URL=https://your-api-server.herokuapp.com
API_TIMEOUT=30000
WEBSOCKET_URL=wss://your-api-server.herokuapp.com
```

#### 3. Device Configuration
```bash
# Speedometer-specific settings
DEFAULT_DEVICE_ID=speedometer_001
DEFAULT_WHEEL_CIRCUMFERENCE=2.1
DEFAULT_SPEED_THRESHOLD=50
DEFAULT_DATA_INTERVAL=30
```

#### 4. Feature Flags
```bash
# Control app features
ENABLE_MAPS=true
ENABLE_TRIP_DETECTION=true
ENABLE_GEOFENCING=false
ENABLE_FLEET_MANAGEMENT=false
```

#### 5. Performance Settings
```bash
# Optimize app performance
CHART_DATA_POINTS_LIMIT=100
CHART_REFRESH_INTERVAL=5000
NETWORK_TIMEOUT=10000
RETRY_ATTEMPTS=3
```

### Usage in Code

#### Import Configuration
```javascript
import AppConfig from '../config/AppConfig';

// Access configuration values
const firebaseConfig = AppConfig.FIREBASE_CONFIG;
const apiUrl = AppConfig.API_BASE_URL;
const debugMode = AppConfig.DEBUG_MODE;
```

#### Conditional Features
```javascript
// Feature flags
if (AppConfig.ENABLE_MAPS) {
  // Initialize maps functionality
}

if (AppConfig.DEBUG_MODE) {
  console.log('Debug information');
}

// Environment-specific behavior
if (AppConfig.IS_PRODUCTION) {
  // Production-only features
  analytics.initialize();
} else {
  // Development-only features
  showDebugPanel();
}
```

#### Configuration Validation
```javascript
// Validate required configuration
if (!AppConfig.validate()) {
  console.error('Invalid configuration');
  // Handle missing configuration
}

// Log all configuration (development only)
if (AppConfig.DEBUG_MODE) {
  AppConfig.log();
}
```

### Build Configuration

#### Android Build Variants
```bash
# Development build
npx react-native run-android --variant=debug

# Production build with environment
ENVFILE=.env.production npx react-native run-android --variant=release
```

#### iOS Build Schemes
```bash
# Development
npx react-native run-ios --scheme="SpeedometerApp" --configuration=Debug

# Production
npx react-native run-ios --scheme="SpeedometerApp" --configuration=Release
```

## 🔧 Configuration Management

### Environment Switching
```bash
# Switch to development
npm run env:dev
npx react-native start --reset-cache

# Switch to production
npm run env:prod
npx react-native start --reset-cache
```

### Configuration Validation

#### Required Variables Checklist
- [ ] `FIREBASE_PROJECT_ID` - Firebase project identifier
- [ ] `FIREBASE_API_KEY` - Firebase web API key
- [ ] `FIREBASE_AUTH_DOMAIN` - Firebase authentication domain
- [ ] `FIREBASE_DATABASE_URL` - Firebase Realtime Database URL

#### Optional Variables
- [ ] `API_BASE_URL` - Custom backend API URL
- [ ] `DEFAULT_DEVICE_ID` - Default speedometer device ID
- [ ] `ENABLE_PUSH_NOTIFICATIONS` - Push notification toggle
- [ ] `DEBUG_MODE` - Debug logging toggle

### Security Considerations

#### Sensitive Information
```bash
# Never commit these files:
.env
.env.local
.env.production

# Always use .env.example for templates
```

#### Production Security
```bash
# Enable security features in production
SSL_PINNING_ENABLED=true
API_KEY_VALIDATION=true
BIOMETRIC_AUTH_ENABLED=true
CRASH_REPORTING_ENABLED=true
```

#### Development Security
```bash
# Disable security features for easier development
SSL_PINNING_ENABLED=false
API_KEY_VALIDATION=false
BIOMETRIC_AUTH_ENABLED=false
DEBUG_MODE=true
```

## 🧩 Integration Testing

### End-to-End Test Flow

1. **Test SIM7070G Connectivity**:
```bash
cd application/raspberry-pi
sudo python3 simple_http_test.py
```

2. **Verify Firebase Configuration**:
```bash
cd application/mobile
npm run env:dev
npx react-native run-android
```

3. **Test Data Flow**:
```bash
# Raspberry Pi sends test data
cd application/raspberry-pi
sudo python3 firebase_client.py

# Mobile app receives real-time updates
# Check Firebase Console for data
```

### Configuration Debugging

#### Check Environment Loading
```javascript
import Config from 'react-native-config';

console.log('Loaded config:', {
  FIREBASE_PROJECT_ID: Config.FIREBASE_PROJECT_ID,
  API_BASE_URL: Config.API_BASE_URL,
  DEBUG_MODE: Config.DEBUG_MODE,
});
```

#### Firebase Connection Test
```javascript
import AppConfig from '../config/AppConfig';
import firebaseService from '../services/FirebaseService';

// Test Firebase connectivity
const testFirebase = async () => {
  const health = await firebaseService.checkConnectionHealth();
  console.log('Firebase health:', health);
};
```

## 📋 Configuration Templates

### Personal Development Setup
```bash
# .env.development
APP_NAME=MySpeedometer Dev
FIREBASE_PROJECT_ID=my-speedometer-dev
FIREBASE_API_KEY=AIza...
DEFAULT_DEVICE_ID=my_test_device
DEBUG_MODE=true
SPEED_ALERT_THRESHOLD=30
```

### Production Deployment
```bash
# .env.production
APP_NAME=Speedometer Pro
FIREBASE_PROJECT_ID=speedometer-prod-12345
FIREBASE_API_KEY=AIza...
DEFAULT_DEVICE_ID=speedometer_001
DEBUG_MODE=false
CRASH_REPORTING_ENABLED=true
ANALYTICS_ENABLED=true
```

### Multi-Device Fleet Setup
```bash
# .env.fleet
ENABLE_FLEET_MANAGEMENT=true
ENABLE_GEOFENCING=true
DEFAULT_SPEED_THRESHOLD=50
CHART_DATA_POINTS_LIMIT=200
ENABLE_TRIP_DETECTION=true
```

## 🔄 CI/CD Integration

### GitHub Actions Environment
```yaml
# .github/workflows/build.yml
env:
  FIREBASE_PROJECT_ID: ${{ secrets.FIREBASE_PROJECT_ID }}
  FIREBASE_API_KEY: ${{ secrets.FIREBASE_API_KEY }}
  API_BASE_URL: ${{ secrets.API_BASE_URL }}
```

### Docker Environment
```dockerfile
# Dockerfile
ENV FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID}
ENV API_BASE_URL=${API_BASE_URL}
ENV DEBUG_MODE=false
```

---

**Quick Start Checklist:**
1. ✅ Test SIM7070G with `simple_http_test.py`
2. ✅ Copy `.env.example` to `.env` and configure
3. ✅ Set Firebase credentials
4. ✅ Choose development/production environment
5. ✅ Build and run mobile app
6. ✅ Verify end-to-end data flow

Your environment is now fully configured for development and production! 🚀