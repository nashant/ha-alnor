# Changelog

All notable changes to this project will be documented in this file.

## [1.1.1](https://github.com/nashant/ha-alnor/compare/v1.1.0...v1.1.1) (2026-01-26)


### Bug Fixes

* **coordinator:** use correct SDK API response keys ([02907b5](https://github.com/nashant/ha-alnor/commit/02907b54ceaa72edfb4e5fd9a69d2d04d9dba41d))

## [1.1.0](https://github.com/nashant/ha-alnor/compare/v1.0.1...v1.1.0) (2026-01-26)


### Features

* **ui:** add integration icon ([949eac5](https://github.com/nashant/ha-alnor/commit/949eac5225004b1fd69a88b3179e370c3b18103b))


### Bug Fixes

* **coordinator:** handle SDK API response format and fix unclosed sessions ([1ed3bfd](https://github.com/nashant/ha-alnor/commit/1ed3bfdb9e59543ba11f503045c2f567bcdc88fc))

## [1.0.1](https://github.com/nashant/ha-alnor/compare/v1.0.0...v1.0.1) (2026-01-26)


### Bug Fixes

* **config:** update AlnorCloudApi usage and add reauth flow ([5dfc4a4](https://github.com/nashant/ha-alnor/commit/5dfc4a484e4562f800e8770440bc1aeb38138393))

## 1.0.0 (2026-01-26)


### Bug Fixes

* **ci:** Address failing tests ([335905e](https://github.com/nashant/ha-alnor/commit/335905e7f201468546f2cf8acb9b6d44a9ebefab))
* **ci:** Only test python 3.13 ([9cf4117](https://github.com/nashant/ha-alnor/commit/9cf41174731a62bf3101ce060d9c69ed6d4e6877))
* **ci:** Use sdk correctly ([e38cac5](https://github.com/nashant/ha-alnor/commit/e38cac5cb3c421002cbfbd1e11f69c3c03c5f4ac))
* **ci:** workflow fixes ([40a82d8](https://github.com/nashant/ha-alnor/commit/40a82d81826ce281d05c05fe7797240597803052))
* **tests:** fix remaining test failures to achieve 100% pass rate ([c77279c](https://github.com/nashant/ha-alnor/commit/c77279cf184050b08b84393f0481f7453cd50a79))
* **tests:** fix test failures for CI compatibility ([a582062](https://github.com/nashant/ha-alnor/commit/a5820627b57f8e98447d3d34b3588c3e9fdffde6))

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
