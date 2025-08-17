#!/usr/bin/env node

/**
 * Device Setup Script
 * Creates a new device and generates API key for authentication
 */

const sqlite3 = require('sqlite3').verbose();
const crypto = require('crypto');
const path = require('path');

// Generate secure API key
function generateApiKey() {
  return crypto.randomBytes(32).toString('hex');
}

async function setupDevice(deviceId, deviceName, description = '') {
  const dbPath = process.env.DB_PATH || './data/speedometer.db';
  
  return new Promise((resolve, reject) => {
    const db = new sqlite3.Database(dbPath, (err) => {
      if (err) {
        reject(err);
        return;
      }
    });

    db.serialize(() => {
      // Insert device
      db.run(`
        INSERT OR REPLACE INTO devices (id, name, description, active)
        VALUES (?, ?, ?, TRUE)
      `, [deviceId, deviceName, description], function(err) {
        if (err) {
          reject(err);
          return;
        }

        console.log(`✅ Device created: ${deviceId}`);
      });

      // Generate and insert API key
      const apiKey = generateApiKey();
      db.run(`
        INSERT OR REPLACE INTO api_keys (device_id, api_key, active)
        VALUES (?, ?, TRUE)
      `, [deviceId, apiKey], function(err) {
        if (err) {
          reject(err);
          return;
        }

        console.log(`🔑 API Key generated for ${deviceId}`);
        console.log(`API Key: ${apiKey}`);
        console.log(`\n📝 Save this API key securely! You'll need it to authenticate API requests.`);
        
        resolve({ deviceId, apiKey });
      });
    });

    db.close();
  });
}

// CLI interface
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args.length < 2) {
    console.log('Usage: node setup-device.js <device-id> <device-name> [description]');
    console.log('Example: node setup-device.js speedometer_001 "Main Speedometer" "Primary speedometer device"');
    process.exit(1);
  }

  const [deviceId, deviceName, description = ''] = args;

  setupDevice(deviceId, deviceName, description)
    .then(({ deviceId, apiKey }) => {
      console.log('\n🎉 Device setup complete!');
      console.log('\n📋 Configuration for your Raspberry Pi:');
      console.log(`{`);
      console.log(`  "device_id": "${deviceId}",`);
      console.log(`  "api_key": "${apiKey}",`);
      console.log(`  "api_endpoint": "http://your-server:3000/api/data"`);
      console.log(`}`);
      console.log('\nUpdate your config.json file with these values.');
    })
    .catch((err) => {
      console.error('❌ Error setting up device:', err.message);
      process.exit(1);
    });
}

module.exports = { setupDevice, generateApiKey };