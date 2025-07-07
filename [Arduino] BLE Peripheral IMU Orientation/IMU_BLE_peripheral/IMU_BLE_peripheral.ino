#include <SensorFusion.h>              
#include <Arduino_BMI270_BMM150.h>     
#include <ArduinoBLE.h>

SF fusion;

float g_x, g_y, g_z, a_x, a_y, a_z, m_x, m_y, m_z;
float deltat;
int pitch, roll, yaw;
unsigned long startupTime = 0;
unsigned long timer = 0;

// creating BLE services
BLEService imuService("180C");
BLECharacteristic orientationChar("2A56", BLERead | BLENotify, 40); 

// Setup
void setup() {
  Serial.begin(9600);
  // while (!Serial);

  Serial.println("Starting device...");

  // init IMU
  if (!IMU.begin()) {
    Serial.println("can't initialize IMU");
    while (1) {
      Serial.println("IMU problem");
      delay(1000);
    }
  }

  // init ble
  if (!BLE.begin()) {
    Serial.println("Failed to start BLE");
    while (1) {
      Serial.println("BLE problem");
      delay(1000);
    }
  }

  BLE.setLocalName("IMUPeripheral");
  BLE.setAdvertisedService(imuService);
  imuService.addCharacteristic(orientationChar);
  BLE.addService(imuService);
  BLE.advertise();

  Serial.print("BLE MAC Address: ");
  Serial.println(BLE.address());

  Serial.println("Warming up sensor fusion...");
  unsigned long warmupStart = millis();
  while (millis() - warmupStart < 8000) {
    if (IMU.gyroscopeAvailable()) {
      IMU.readAcceleration(a_x, a_y, a_z);    
      IMU.readGyroscope(g_x, g_y, g_z);  
      IMU.readMagneticField(m_x, m_y, m_z);  

      g_x *= DEG_TO_RAD;
      g_y *= DEG_TO_RAD;
      g_z *= DEG_TO_RAD;

      deltat = fusion.deltatUpdate();
      fusion.MadgwickUpdate(g_x, g_y, g_z, a_x, a_y, a_z, m_x, m_y, m_z, deltat);
    }
  }

  startupTime = millis();
  Serial.println("Sensor fusion ready");
}

void loop() {
  BLEDevice central = BLE.central();

  if (central) {
    Serial.print("connected to central: ");
    Serial.println(central.address());

    while (central.connected()) {
      if (IMU.gyroscopeAvailable()) {
        IMU.readAcceleration(a_x, a_y, a_z);    
        IMU.readGyroscope(g_x, g_y, g_z);
        IMU.readMagneticField(m_x, m_y, m_z);

        g_x *= DEG_TO_RAD;
        g_y *= DEG_TO_RAD;
        g_z *= DEG_TO_RAD;

        deltat = fusion.deltatUpdate();
        fusion.MadgwickUpdate(g_x, g_y, g_z, a_x, a_y, a_z, m_x, m_y, m_z, deltat);

        roll = fusion.getRoll();
        pitch = fusion.getPitch();
        yaw = fusion.getYaw();
      }

      if (millis() - timer > 300) {
        timer = millis();

        int16_t p = (int16_t)(pitch * 10);
        int16_t y = (int16_t)(yaw * 10);
        int16_t r = (int16_t)(roll * 10);

        uint8_t buffer[6];
        buffer[0] = p & 0xFF;
        buffer[1] = (p >> 8) & 0xFF;
        buffer[2] = y & 0xFF;
        buffer[3] = (y >> 8) & 0xFF;
        buffer[4] = r & 0xFF;
        buffer[5] = (r >> 8) & 0xFF;

        // String data = String(pitch) + "," + String(yaw) + "," + String(roll);
        orientationChar.writeValue(buffer, sizeof(buffer));

        // Serial.println(data);
      }
    }

    Serial.println("disconnected from central");
  }
  
}
