# Installation Guide

This guide provides detailed installation instructions for the Alnor Ventilation integration.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Methods](#installation-methods)
  - [HACS Installation](#hacs-installation-recommended)
  - [Manual Installation](#manual-installation)
- [Post-Installation](#post-installation)
- [Verification](#verification)
- [Uninstallation](#uninstallation)

---

## Prerequisites

### Required

- ✅ **Home Assistant** 2026.1.0 or newer
- ✅ **Alnor cloud account** with registered devices
- ✅ **Internet connection** for initial setup and cloud mode

### Optional (for local Modbus)

- 🔌 Devices on same network as Home Assistant
- 🔌 Port 502 accessible (Modbus TCP)
- 🔌 Static IP addresses or DHCP reservations

---

## Installation Methods

### HACS Installation (Recommended)

HACS (Home Assistant Community Store) provides the easiest installation and update method.

#### Step 1: Install HACS

If you haven't installed HACS yet:

1. Follow the official [HACS installation guide](https://hacs.xyz/docs/setup/download)
2. Restart Home Assistant
3. Complete HACS setup through the UI

#### Step 2: Add Custom Repository

1. Open HACS in Home Assistant
2. Click **Integrations**
3. Click the **⋮** menu (three dots, top right corner)
4. Select **Custom repositories**
5. Enter repository details:
   - **Repository:** `https://github.com/nashant/ha-alnor`
   - **Category:** `Integration`
6. Click **Add**

#### Step 3: Install Integration

1. Search for **"Alnor Ventilation"** in HACS
2. Click on the integration card
3. Click **Download** (bottom right)
4. Select the latest version
5. Click **Download** again

#### Step 4: Restart Home Assistant

1. Go to **Settings** → **System** → **Restart**
2. Click **Restart Home Assistant**
3. Wait for restart to complete

#### Step 5: Add Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration** (bottom right)
3. Search for **"Alnor Ventilation"**
4. Click on the integration to start setup

---

### Manual Installation

For advanced users or environments without HACS.

#### Step 1: Download Release

1. Go to [GitHub Releases](https://github.com/nashant/ha-alnor/releases)
2. Download the latest `alnor-x.x.x.zip` file
3. Extract the ZIP file

#### Step 2: Copy Files

Copy the `alnor` folder to your Home Assistant configuration directory:

```bash
# Your target structure should be:
config/
└── custom_components/
    └── alnor/
        ├── __init__.py
        ├── manifest.json
        ├── config_flow.py
        ├── coordinator.py
        ├── const.py
        ├── entity.py
        ├── fan.py
        ├── sensor.py
        ├── binary_sensor.py
        ├── select.py
        ├── button.py
        ├── strings.json
        └── translations/
            └── en.json
```

#### Via SSH/Terminal

```bash
# Navigate to config directory
cd /config

# Create custom_components directory if it doesn't exist
mkdir -p custom_components

# Download and extract (replace x.x.x with version)
wget https://github.com/nashant/ha-alnor/releases/download/vx.x.x/alnor-x.x.x.zip
unzip alnor-x.x.x.zip -d custom_components/

# Verify installation
ls -la custom_components/alnor/
```

#### Via Samba/SMB

1. Connect to your Home Assistant Samba share
2. Navigate to `config/custom_components/`
3. Create `alnor` folder if it doesn't exist
4. Copy all files from the extracted ZIP into the `alnor` folder

#### Step 3: Verify File Permissions

Ensure files are readable by Home Assistant:

```bash
chmod -R 755 /config/custom_components/alnor/
chown -R homeassistant:homeassistant /config/custom_components/alnor/
```

#### Step 4: Restart Home Assistant

```bash
# Via CLI
ha core restart

# Or use the UI:
# Settings → System → Restart → Restart Home Assistant
```

#### Step 5: Add Integration

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Alnor Ventilation"**
4. Click to start setup

---

## Post-Installation

### Check Installation

After restart, verify the integration is available:

1. Go to **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for "Alnor"
4. You should see **"Alnor Ventilation"** in the results

### Check Logs

If the integration doesn't appear, check for errors:

1. Go to **Settings** → **System** → **Logs**
2. Search for "alnor" or "custom_components"
3. Look for import errors or missing dependencies

Common errors:

```
Error loading custom_components.alnor
```
**Solution:** Files not in correct location, check directory structure

```
ModuleNotFoundError: No module named 'alnor_sdk'
```
**Solution:** Dependency issue, restart Home Assistant again

### Enable Debug Logging (Optional)

For troubleshooting:

```yaml
# configuration.yaml
logger:
  default: info
  logs:
    custom_components.alnor: debug
    alnor_sdk: debug
```

---

## Verification

### Test Integration

1. **Add Integration:**
   - Settings → Devices & Services → Add Integration
   - Search "Alnor Ventilation"
   - Should appear in results ✅

2. **Enter Credentials:**
   - Use your Alnor cloud account
   - Should connect successfully ✅

3. **Check Devices:**
   - After setup, go to Settings → Devices & Services → Alnor Ventilation
   - Click on the card to see devices
   - All your Alnor devices should be discovered ✅

4. **Check Entities:**
   - Go to Settings → Devices & Services → Alnor Ventilation → Devices
   - Click on a device
   - Should see fan, sensors, and other entities ✅

### Expected Results

For an HRU-PremAir-450, you should see:
- 1 fan entity
- 9 sensor entities
- 1 binary sensor entity
- 1 select entity
- 1 button entity

**Total: 13 entities per HRU device**

---

## Uninstallation

### Remove Integration

1. Go to **Settings** → **Devices & Services**
2. Find **Alnor Ventilation** card
3. Click **⋮** menu (three dots)
4. Select **Delete**
5. Confirm deletion

### Remove Files (Manual)

If you want to completely remove the integration:

```bash
# Remove integration files
rm -rf /config/custom_components/alnor/

# Restart Home Assistant
ha core restart
```

### Remove from HACS

1. Open HACS
2. Go to **Integrations**
3. Find **Alnor Ventilation**
4. Click **⋮** menu
5. Select **Remove**
6. Restart Home Assistant

---

## Updating

### HACS Update

HACS automatically checks for updates:

1. Go to HACS → Integrations
2. Updates show a blue badge
3. Click integration card
4. Click **Update**
5. Restart Home Assistant

### Manual Update

1. Download latest release
2. Extract and replace files in `custom_components/alnor/`
3. Restart Home Assistant

---

## Troubleshooting Installation

### Integration Not Appearing

**Problem:** Can't find "Alnor Ventilation" in Add Integration

**Solutions:**
1. Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
2. Verify files in correct location: `config/custom_components/alnor/`
3. Check file permissions (readable by HA user)
4. Restart Home Assistant again
5. Check logs for import errors

### Import Errors

**Problem:** Logs show import or module errors

**Solutions:**
1. Verify `manifest.json` is valid JSON
2. Check `requirements` in manifest includes `alnor-sdk>=0.1.0`
3. Ensure Home Assistant can access PyPI (internet connection)
4. Try: `pip install alnor-sdk` in HA container
5. Restart after fixing

### HACS Not Finding Repository

**Problem:** Custom repository addition fails

**Solutions:**
1. Verify URL is exactly: `https://github.com/nashant/ha-alnor`
2. Check GitHub is accessible from your network
3. Ensure HACS is properly installed and configured
4. Try adding through GitHub URL instead of search

---

## Next Steps

After successful installation:

1. 📖 [Configuration Guide](CONFIGURATION.md) - Set up the integration
2. 🎛️ [Usage Guide](USAGE.md) - Learn how to use entities
3. 🤖 [Automation Examples](AUTOMATIONS.md) - Sample automations
4. 🔧 [Troubleshooting](TROUBLESHOOTING.md) - Solve common issues

---

**Need Help?**
- 💬 [Community Discussions](https://github.com/nashant/ha-alnor/discussions)
- 🐛 [Report Issues](https://github.com/nashant/ha-alnor/issues)
