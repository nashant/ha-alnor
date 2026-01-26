# Alnor Ventilation Integration

![Version](https://img.shields.io/github/v/release/nashant/ha-alnor)
![Downloads](https://img.shields.io/github/downloads/nashant/ha-alnor/total)

Control your Alnor ventilation devices with Home Assistant! 🌬️

## Features

### 🔌 Dual-Mode Operation
- **Cloud API** for easy setup and reliable connectivity
- **Local Modbus TCP** for faster response (< 100ms) and offline operation
- Automatic fallback between modes

### 🔍 Automatic Discovery
- Discovers all bridges and devices instantly
- No manual device configuration needed
- Maps devices to Home Assistant areas

### 📊 Comprehensive Monitoring
- Real-time temperature readings (indoor, outdoor, supply, exhaust)
- Fan speeds and performance metrics
- Filter replacement countdown
- CO2 levels and humidity monitoring
- Fault detection and diagnostics

### 🎛️ Full Control
- Speed control (0-100%)
- Preset modes: standby, away, home, home_plus, auto, party
- Mode scheduling via automations
- Filter timer management

### ⚡ Smart Automation
Works perfectly with Home Assistant automations:
- Temperature-based ventilation
- CO2-triggered air refresh
- Presence-aware modes
- Filter replacement reminders

## Supported Devices

### Heat Recovery Units
- HRU-PremAir-450
- HRU-PremAir-500

**13 entities per device**: Fan control, 9 sensors, fault detection, mode select, filter reset

### Exhaust Fans
- VMC-02VJ04
- VMC series

**4 entities per device**: Fan control, speed sensor, fault detection, mode select

### Environmental Sensors
- VMS-02C05 (CO2 Sensor)
- VMI-02MC02 (Humidity Sensor)

**1-2 entities per sensor**: CO2 level, temperature, humidity

## Quick Start

1. **Install** via HACS or manually
2. **Configure** with your Alnor cloud credentials
3. **Discover** devices automatically
4. **Optionally** set up local Modbus connections for faster response
5. **Automate** your ventilation with Home Assistant

## Requirements

- Home Assistant 2024.1.0 or newer
- Alnor cloud account with registered devices
- (Optional) Devices on local network for Modbus TCP

## Documentation

- 📖 [Full README](https://github.com/nashant/ha-alnor/blob/main/README.md)
- 🛠️ [Installation Guide](https://github.com/nashant/ha-alnor/blob/main/docs/INSTALLATION.md)
- ❓ [FAQ](https://github.com/nashant/ha-alnor/blob/main/docs/FAQ.md)
- 🐛 [Issues](https://github.com/nashant/ha-alnor/issues)
- 💬 [Discussions](https://github.com/nashant/ha-alnor/discussions)

## Example Automation

```yaml
automation:
  - alias: "Boost ventilation on high CO2"
    trigger:
      - platform: numeric_state
        entity_id: sensor.office_co2_level
        above: 1000
    action:
      - service: fan.set_preset_mode
        target:
          entity_id: fan.living_room_hru
        data:
          preset_mode: "party"
```

---

Made with ❤️ for the Home Assistant community
