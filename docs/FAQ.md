# Frequently Asked Questions (FAQ)

## General Questions

### What is this integration?

The Alnor Ventilation integration allows you to control and monitor your Alnor ventilation devices (Heat Recovery Units, exhaust fans, and sensors) directly from Home Assistant.

### Which devices are supported?

- **Heat Recovery Units:** HRU-PremAir-450, HRU-PremAir-500
- **Exhaust Fans:** VMC-02VJ04, VMC series
- **Sensors:** VMS-02C05 (CO2), VMI-02MC02 (Humidity)

See [Supported Devices](../README.md#supported-devices) for details.

### Do I need an Alnor cloud account?

**Yes**, a cloud account is required for initial setup and device discovery. However, once configured, you can optionally use local Modbus TCP connections for offline operation.

### Is this official from Alnor?

**No**, this is a community-developed integration. It uses the Alnor cloud API and Modbus TCP protocol to communicate with devices.

---

## Installation & Setup

### How do I install this integration?

See the [Installation Guide](INSTALLATION.md) for step-by-step instructions. We recommend using HACS for easiest installation.

### Can I use this without HACS?

**Yes**, you can install manually. Download the latest release and copy files to `config/custom_components/alnor/`. See [Manual Installation](INSTALLATION.md#manual-installation).

### The integration doesn't appear in my integrations list

**Try these steps:**
1. Clear your browser cache (Ctrl+Shift+R)
2. Verify files are in `config/custom_components/alnor/`
3. Restart Home Assistant
4. Check logs for errors

### Setup fails with "Invalid credentials"

**Verify:**
- Email and password are correct (test in Alnor mobile app)
- Email is case-sensitive
- No typos in password
- Account is active and verified

---

## Features & Functionality

### What entities are created for my HRU?

For each HRU-PremAir device, you get:
- 1 fan control (speed + preset modes)
- 9 sensors (temperatures, speeds, filter, bypass, preheater)
- 1 binary sensor (fault detection)
- 1 select (mode selection)
- 1 button (filter reset)

**Total: 13 entities per HRU**

### Can I control fan speed?

**Yes!** Use the fan entity to:
- Set speed from 0-100%
- Select preset modes (standby, away, home, home_plus, auto, party)
- Turn on/off

### How often does data update?

- **Cloud mode:** Every 60 seconds
- **Local mode:** Every 30 seconds
- Updates automatically adjust based on connection type

### Can I trigger automations from sensor values?

**Absolutely!** All sensors can be used in automations. Examples:
- Increase ventilation when CO2 > 1000 ppm
- Boost airflow when indoor temperature > 25°C
- Send notification when filter needs replacement

---

## Local vs Cloud Mode

### What's the difference between cloud and local mode?

| Feature | Cloud Mode | Local Mode |
|---------|------------|------------|
| **Setup** | Automatic | Manual (IP config) |
| **Latency** | 1-2 seconds | < 100ms |
| **Offline** | ❌ No | ✅ Yes |
| **Internet** | Required | Not required |

### How do I enable local Modbus connections?

1. Go to integration options (Configure button)
2. Enable "Configure local Modbus TCP connections"
3. Enter IP address for each device
4. Integration validates and uses local connection if successful

**Requirements:**
- Devices on same network as Home Assistant
- Port 502 accessible
- Static IP or DHCP reservation recommended

### What happens if local connection fails?

The integration **automatically falls back to cloud mode**. You'll see a warning in logs but devices remain functional.

### Can I mix local and cloud connections?

**Yes!** You can configure local IPs for some devices and leave others on cloud. The integration handles both simultaneously.

### How do I know which mode my device is using?

Check the `connection_mode` attribute on any entity:

```yaml
{{ state_attr('fan.living_room_hru', 'connection_mode') }}
# Returns: 'local' or 'cloud'
```

### Why is local mode faster?

Local Modbus TCP connects directly to your device over LAN, bypassing internet round-trip to Alnor cloud servers.

---

## Troubleshooting

### My devices aren't discovered

**Check:**
1. Devices appear in Alnor mobile app
2. Bridge (gateway) is online and connected
3. Internet connection is working
4. Reload integration from UI

### Entities show as "Unavailable"

**Common causes:**
- Device is offline (check Alnor app)
- Internet connection lost (cloud mode)
- Local IP changed (local mode)
- API server issues

**Solutions:**
- Verify device is online in Alnor app
- Check network connectivity
- Reload integration
- Check logs for specific errors

### Local Modbus connection won't work

**Checklist:**
1. ✅ Device IP address is correct
2. ✅ Device is on same network as Home Assistant
3. ✅ Port 502 is not blocked by firewall
4. ✅ No network segmentation (VLANs, isolated networks)
5. ✅ Can ping device from HA: `ping <device_ip>`

**Still not working?**
The integration will automatically use cloud mode as fallback. Local mode is optional.

### Filter reset button doesn't work

**This depends on SDK support.** If the `alnor-sdk` doesn't implement `reset_filter_timer()`, the button won't function. Workaround: Reset filter manually through Alnor mobile app.

### Automation doesn't trigger

**Verify:**
- Entity ID is correct (check in Developer Tools → States)
- Trigger conditions are met (check current state)
- Automation is enabled
- Check automation traces for details

---

## Configuration

### Can I rename entities?

**Yes!** Go to entity settings and change the name. This won't affect functionality.

### How do I change device areas?

Go to device settings and assign to an area. If zone sync is enabled, this may update Alnor zones.

### What is zone synchronization?

Zone sync creates Alnor cloud zones matching your Home Assistant areas, allowing you to manage device locations from either interface.

**Enable in:** Integration options → "Synchronize zones with Home Assistant areas"

### Can I disable entities I don't need?

**Yes!** Go to entity settings and disable unwanted entities. They won't appear in UI but remain available if you change your mind.

---

## Performance & Resources

### Does this slow down Home Assistant?

**No.** The integration uses efficient polling with reasonable intervals (30-60s) and asynchronous operations.

### How much data does cloud mode use?

Minimal. Each update is a small API call (< 10 KB). Daily usage: ~10-15 MB per device.

### Does local mode use more CPU?

Local Modbus is actually more efficient than cloud API calls due to direct TCP communication.

---

## Privacy & Security

### What data is sent to Alnor cloud?

- Authentication credentials (encrypted)
- Device control commands (speed, mode changes)
- Configuration updates (zone assignments)

**Not sent:**
- Your Home Assistant configuration
- Other sensor data
- User behavior or analytics

### Are my credentials stored securely?

**Yes.** Home Assistant encrypts all credentials in the config entry. They're never stored in plain text.

### Can devices work without internet?

**Only with local Modbus TCP connections.** Cloud mode requires internet. We recommend:
- Configure local IPs for critical devices
- Keep cloud as backup fallback

### Is Modbus TCP secure?

Modbus TCP has **no built-in encryption**. We recommend:
- Use only on trusted home networks
- Don't expose port 502 to internet
- Use VLANs if you have IoT isolation

---

## Advanced Usage

### Can I use this with multiple Alnor accounts?

**No.** Currently, only one account can be configured per Home Assistant instance. Each account gets its own integration instance.

### Can I control devices from multiple locations?

**Yes**, through Home Assistant remote access (Nabu Casa or VPN). Local Modbus only works when on same network.

### How do I update the integration?

**HACS:**
- HACS automatically notifies of updates
- Click update button
- Restart Home Assistant

**Manual:**
- Download new release
- Replace files in `custom_components/alnor/`
- Restart Home Assistant

### Can I contribute to development?

**Absolutely!** See [CONTRIBUTING.md](../.github/CONTRIBUTING.md) for guidelines.

---

## Common Error Messages

### "Cannot connect to Alnor cloud"

**Meaning:** Integration can't reach Alnor API servers

**Solutions:**
- Check internet connection
- Verify firewall isn't blocking Home Assistant
- Check if Alnor service is down
- Wait and try again (temporary outage)

### "Invalid authentication credentials"

**Meaning:** Username or password incorrect

**Solutions:**
- Verify credentials in Alnor mobile app
- Check for typos (email is case-sensitive)
- Reset password if needed
- Re-add integration with correct credentials

### "Device unavailable"

**Meaning:** Specific device isn't responding

**Solutions:**
- Check device power and network
- Verify in Alnor mobile app
- Check bridge/gateway status
- Restart device if needed

### "Update failed"

**Meaning:** Coordinator couldn't fetch latest data

**Solutions:**
- Usually temporary, will retry automatically
- Check logs for specific error
- Verify devices are online
- Check network/internet connectivity

---

## Getting Help

### Where can I get support?

- 📖 [Documentation](../README.md)
- 💬 [Community Discussions](https://github.com/nashant/ha-alnor/discussions)
- 🐛 [Bug Reports](https://github.com/nashant/ha-alnor/issues)

### How do I report a bug?

1. Enable debug logging
2. Reproduce the issue
3. Copy relevant logs
4. [Open an issue](https://github.com/nashant/ha-alnor/issues/new) with:
   - Home Assistant version
   - Integration version
   - Device models
   - Steps to reproduce
   - Logs (remove sensitive info)

### How do I request a feature?

[Open a feature request](https://github.com/nashant/ha-alnor/issues/new) describing:
- What you want to accomplish
- Why it would be useful
- Expected behavior
- Any alternatives you've considered

---

## Still have questions?

Ask in [Discussions](https://github.com/nashant/ha-alnor/discussions) or check the full [Documentation](../README.md)!
