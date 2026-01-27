# Local Development Environment Setup

This guide sets up a local Home Assistant instance with your Alnor integration mounted for live development.

## Prerequisites

- Docker and Docker Compose installed
- Your Alnor cloud credentials (email and password)

## Quick Start

```bash
# Start Home Assistant
docker-compose up -d

# View logs
docker-compose logs -f
```

That's it! Home Assistant will be available at **http://localhost:8123**

**First startup takes 2-3 minutes** as it downloads dependencies and initializes the database.

The container automatically:
- Mounts `custom_components/alnor/` to `/config/custom_components/alnor/` (read-only)
- Creates `ha-dev-config/` directory for persistent Home Assistant configuration
- Detects and uses your system's timezone automatically

### 2. Initial Home Assistant Setup

1. Open http://localhost:8123 in your browser
2. Complete the onboarding:
   - Create your admin account
   - Set your home location and unit system
   - Skip adding any devices/integrations for now

### 3. Install HACS (Home Assistant Community Store)

HACS is optional but useful for managing other custom integrations.

#### Option A: Manual HACS Installation (Recommended for Dev)

```bash
# Download HACS
docker-compose exec homeassistant bash -c "
wget -O - https://get.hacs.xyz | bash -
"

# Restart Home Assistant
docker-compose restart
```

#### Option B: Skip HACS

If you don't need HACS, skip this step. Your Alnor integration will work fine without it.

### 4. Add the Alnor Integration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for "Alnor Ventilation"
3. Enter your Alnor cloud credentials (email and password)
4. Configure options:
   - Enable/disable zone synchronization
   - Optionally configure local Modbus TCP IPs
   - Optionally configure humidity control

### 5. Verify the Integration

After adding the integration, you should see:

**Climate Entities (for HRU devices):**
- `climate.{device_name}` - Main climate control
- Temperature display (supply air)
- Fan modes: low, medium, high
- Preset modes: standby, away, home, home_plus, auto, party

**Fan Entities (for exhaust fans):**
- `fan.{device_name}` - Fan control

**Sensors:**
- Temperature sensors (indoor, outdoor, supply, exhaust)
- Fan speed sensors
- Filter status
- And more...

**Switch Entities (if humidity configured):**
- `switch.{device_name}_humidity_control` - Enable/disable auto humidity control

## Development Workflow

### Making Code Changes

1. **Edit files** in `custom_components/alnor/` directory
2. **Restart Home Assistant** to load changes:
   ```bash
   docker-compose restart
   ```
   Or use the UI: **Developer Tools** → **Restart** → **Restart Home Assistant**

3. **Check logs** for errors:
   ```bash
   docker-compose logs -f homeassistant
   ```
   Or use the UI: **Settings** → **System** → **Logs**

### Viewing Logs

**In terminal:**
```bash
# All logs
docker-compose logs -f

# Filter for Alnor integration
docker-compose logs -f | grep alnor

# Last 100 lines
docker-compose logs --tail=100
```

**In Home Assistant UI:**
- **Settings** → **System** → **Logs**
- Filter by "custom_components.alnor"

### Testing Changes

After making changes and restarting:

1. **Test basic functionality:**
   - Turn climate entity on/off
   - Change fan modes (low/medium/high)
   - Change preset modes (away, home, party, etc.)
   - Verify temperature readings

2. **Test humidity control** (if configured):
   - Set target humidity
   - Enable humidity control switch
   - Verify automatic mode switching

3. **Check entity states:**
   - **Developer Tools** → **States**
   - Find your climate entity
   - Verify attributes are correct

### Debugging Tips

**Enable debug logging:**

Add to `ha-dev-config/configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.alnor: debug
    alnor_sdk: debug
```

Then restart Home Assistant.

**Check for integration errors:**
```bash
# In the container
docker-compose exec homeassistant bash
cd /config
cat home-assistant.log | grep -i alnor | grep -i error
```

### Configuration File Locations

All configuration is stored in `ha-dev-config/`:

```
ha-dev-config/
├── configuration.yaml       # Main HA config
├── automations.yaml        # Automations (UI-managed)
├── scripts.yaml            # Scripts (UI-managed)
├── scenes.yaml             # Scenes (UI-managed)
├── .storage/               # Integration configs (JSON)
│   └── core.config_entries # Your Alnor integration config
└── home-assistant.log      # Main log file
```

## Stopping the Development Environment

```bash
# Stop containers
docker-compose down

# Stop and remove all data (fresh start)
docker-compose down -v
rm -rf ha-dev-config/
```

## Useful Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# View logs
docker-compose logs -f

# Shell access
docker-compose exec homeassistant bash

# Check Home Assistant version
docker-compose exec homeassistant python -m homeassistant --version

# Validate configuration
docker-compose exec homeassistant python -m homeassistant --script check_config -c /config
```

## Testing Specific Scenarios

### Test Climate Entity

```yaml
# Add to Developer Tools → Services

# Turn on
service: climate.set_hvac_mode
target:
  entity_id: climate.living_room_hru
data:
  hvac_mode: fan_only

# Change fan mode
service: climate.set_fan_mode
target:
  entity_id: climate.living_room_hru
data:
  fan_mode: high

# Change preset mode
service: climate.set_preset_mode
target:
  entity_id: climate.living_room_hru
data:
  preset_mode: party

# Set target humidity (if configured)
service: climate.set_humidity
target:
  entity_id: climate.living_room_hru
data:
  humidity: 60
```

### Test Humidity Control

```yaml
# Enable automatic humidity control
service: switch.turn_on
target:
  entity_id: switch.living_room_hru_humidity_control

# Disable automatic humidity control
service: switch.turn_off
target:
  entity_id: switch.living_room_hru_humidity_control
```

## Troubleshooting

### Integration Not Appearing

1. Check that the integration is properly mounted:
   ```bash
   docker-compose exec homeassistant ls -la /config/custom_components/alnor
   ```
   You should see all the Python files.

2. Check for syntax errors:
   ```bash
   docker-compose exec homeassistant python -m py_compile /config/custom_components/alnor/*.py
   ```

3. Restart and check logs:
   ```bash
   docker-compose restart
   docker-compose logs -f | grep alnor
   ```

### Integration Loads But Doesn't Work

1. Check Home Assistant logs:
   ```bash
   docker-compose logs -f homeassistant | grep -i error
   ```

2. Verify your credentials are correct

3. Check if the SDK is installed:
   ```bash
   docker-compose exec homeassistant pip list | grep alnor
   ```

### Need Fresh Start

```bash
# Complete reset
docker-compose down
rm -rf ha-dev-config/
docker-compose up -d
```

This will:
- Remove all Home Assistant configuration
- Require re-running onboarding
- Require re-adding the integration

### Port 8123 Already in Use

If you have another Home Assistant instance running:

```bash
# Change the port in docker-compose.yml
# Replace:
#   - "8123:8123"
# With:
#   - "8124:8123"

# Then access at http://localhost:8124
```

## Integration Development Checklist

- [ ] Start development container
- [ ] Complete Home Assistant onboarding
- [ ] Install HACS (optional)
- [ ] Add Alnor integration with credentials
- [ ] Verify entities appear
- [ ] Make code changes
- [ ] Restart Home Assistant
- [ ] Test changes
- [ ] Check logs for errors
- [ ] Repeat as needed

## Production Deployment

When ready to deploy to production:

1. **Commit your changes** to git
2. **Update version** in `manifest.json`
3. **Update CHANGELOG.md**
4. **Create a release** on GitHub
5. **Install in production** via HACS or manual copy

## Additional Resources

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Custom Integration Tutorial](https://developers.home-assistant.io/docs/creating_integration_manifest)
- [Climate Entity Documentation](https://developers.home-assistant.io/docs/core/entity/climate)
- [Testing Custom Integrations](https://developers.home-assistant.io/docs/development_testing)

## Notes

- The custom component is mounted **read-only** (`:ro`) to prevent accidental modifications inside the container
- All changes should be made in your local `custom_components/alnor/` directory
- The `ha-dev-config/` directory persists between container restarts
- Use `docker-compose down -v` to completely reset and start fresh
