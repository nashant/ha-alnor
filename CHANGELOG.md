# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-28

### Initial Release

First public release of the Alnor Ventilation integration for Home Assistant.

#### Supported Devices
- **Heat Recovery Units (HRU)**
  - HRU-PremAir-450
  - HRU-PremAir-500
- **Exhaust Fans**
  - VMC-02VJ04
  - VMC Exhaust Fan series
- **Environmental Sensors**
  - VMS-02C05 (CO2 Sensor)
  - VMI-02MC02 (Humidity Sensor)

#### Features

**Device Control**
- Climate platform for Heat Recovery Units with temperature display and humidity control
- Humidifier platform for HRUs with humidity sensor integration
- Fan platform for exhaust fans with speed and preset mode control
- Select platform for ventilation mode selection
- Switch platform for toggling automatic humidity control

**Humidity Control**
- Automatic ventilation adjustment based on external humidity sensors
- Configurable target humidity with hysteresis to prevent rapid mode switching
- User-configurable high/low humidity ventilation modes
- Configurable cooldown period between mode changes
- Per-device humidity configuration
- Real-time sensor monitoring with maximum value selection from multiple sensors

**Monitoring**
- Temperature sensors (indoor, outdoor, supply, exhaust)
- Fan speed sensors (exhaust and supply fans)
- Filter status monitoring with days remaining counter
- Bypass position monitoring
- Preheater demand monitoring
- CO2 level sensors
- Humidity sensors
- Binary sensors for fault detection with fault codes

**Configuration**
- UI-based configuration flow with automatic device discovery
- Options flow for humidity control setup with two-step configuration
  - Step 1: Select humidity sensors
  - Step 2: Configure control parameters (only shown when sensors selected)
- Options flow for local Modbus TCP configuration
- Zone synchronization with Home Assistant areas
- Reauthentication flow

**Connectivity**
- Dual-mode operation: Cloud API + Local Modbus TCP
- Automatic device discovery via Alnor cloud
- Per-device local IP configuration
- Automatic fallback from local to cloud connection
- Per-device connection mode tracking
- Separate update intervals for local (30s) and cloud (60s) connections

**Other Features**
- Filter timer reset button
- Comprehensive test suite (35 tests)
- Full Home Assistant integration patterns
- Support for multiple devices per account
- Entity naming with device names and slugs
- Proper device info with manufacturer, model, SW version, serial number

#### Technical Details
- Built on alnor-sdk >= 0.3.1
- Follows Home Assistant integration best practices
- Protocol-based humidity control mixin for code reuse
- Comprehensive error handling and logging
- Docker development environment
- CI/CD with GitHub Actions

---

## Links

- [GitHub Repository](https://github.com/nashant/ha-alnor)
- [Issue Tracker](https://github.com/nashant/ha-alnor/issues)
- [Documentation](https://github.com/nashant/ha-alnor)
