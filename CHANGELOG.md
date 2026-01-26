# Changelog

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of Alnor Ventilation integration
- Support for HRU-PremAir-450 and HRU-PremAir-500 devices
- Support for VMC-02VJ04 exhaust fans
- Support for VMS-02C05 CO2 sensors and VMI-02MC02 humidity sensors
- Dual-mode operation (Cloud API + Local Modbus TCP)
- Automatic device discovery via Alnor cloud
- Zone synchronization with Home Assistant areas
- Fan platform with speed and preset mode control
- Comprehensive sensor support (temperatures, speeds, filter status)
- Binary sensor for fault detection
- Select platform for mode selection
- Button platform for filter timer reset
- Configuration flow with UI setup
- Options flow for local IP configuration
- Automatic fallback from local to cloud connection
- Per-device connection mode tracking
- GitHub Actions CI/CD pipeline
- Automated semantic versioning and releases
- Comprehensive test suite
- Full documentation

<!--
Changelog format:

## [Version] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Features that will be removed in future versions

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security updates
-->
