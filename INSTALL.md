# Installation & Setup Guide

## Quick Start (1 minute!)

### Step 1: Install the Integration

**Option A: HACS (Easiest)**
1. Open HACS → Integrations
2. Click ⋮ (three dots) → Custom repositories
3. Add: `https://github.com/j2deen/schluter-heat-rs1`
4. Category: Integration
5. Click "Install"
6. Restart Home Assistant

**Option B: Manual**
1. Download the latest release
2. Extract to `config/custom_components/schluter_heat/`
3. Restart Home Assistant

---

### Step 2: Add to Home Assistant

That's it! Just two fields:

1. **Settings** → **Devices & Services**
2. Click **+ Add Integration**
3. Search for **"Schluter DITRA-HEAT-E-RS1"**
4. Enter your information:
   - **Email Address**: Your Schluter account email
   - **Password**: Your Schluter account password
5. If you have multiple locations, select which one to add
6. Click **Submit**

**Note:** Your password is used once to generate a secure token and is **never stored**!

✅ Done! Your thermostats will now appear as climate entities.

**We automatically detect your locations - no need to dig through URLs!**

---

## Security Note

### What Happens to Your Password?

Your credentials are handled securely:
1. ✅ Sent directly to Schluter's API (over HTTPS)
2. ✅ Used once to generate a secure refresh token
3. ✅ **Immediately discarded** (never stored)
4. ✅ Only the refresh token is saved

This is the **same process** as logging into the Schluter app or website!

---

## Verification

### Check Integration is Working

1. Go to **Settings** → **Devices & Services**
2. You should see "Schluter DITRA-HEAT" with your thermostats listed
3. Click on it to see all your devices

### Check Entities

1. Go to **Developer Tools** → **States**
2. Filter for `climate.`
3. You should see your thermostats (e.g., `climate.kitchen_floor`)
4. Check that:
   - `current_temperature` shows a value
   - `target_temperature` shows a value
   - `hvac_action` shows heating/idle/off

### Test Control

Try changing temperature:
1. Go to **Settings** → **Devices & Services** → **Schluter DITRA-HEAT**
2. Click on one of your thermostats
3. Adjust the temperature slider
4. Check your physical thermostat - it should update!

---

## Troubleshooting

### Error: "Invalid authentication"

**Problem**: Wrong username or password

**Solutions**:
1. Double-check your email and password
2. Try logging into schluterditraheat.com to verify credentials
3. Check for typos or extra spaces

### Error: "Cannot connect"

**Problem**: Can't reach Schluter API

**Solutions**:
1. Check your internet connection
2. Try visiting https://schluterditraheat.com to verify it's accessible
3. Check Home Assistant logs for more details
4. Wait a few minutes and try again (server might be temporarily down)

### Error: "No devices found"

**Problem**: Selected location has no devices configured

**Solutions**:
1. Make sure you have RS1 thermostats configured in your Schluter account
2. Log into https://schluterditraheat.com and verify your thermostats appear
3. If you have multiple locations, try selecting a different one during setup

### Integration doesn't show up

**Problem**: Installation incomplete

**Solutions**:
1. Verify files are in `config/custom_components/schluter_heat/`
2. Check the logs: **Settings** → **System** → **Logs**
3. Restart Home Assistant
4. Clear browser cache (Ctrl+Shift+R)

### Entities not updating

**Problem**: Communication issue or expired session

**Solutions**:
1. Check the integration status in **Devices & Services**
2. Click "Reload" on the integration
3. If that doesn't work, you may need to reauthenticate (enter your credentials again)
4. Look at logs for error messages

### Temperature changes don't work

**Problem**: API call failing

**Solutions**:
1. Check internet connection
2. Verify thermostat is online in Schluter app
3. Check Home Assistant logs for API errors
4. Try reloading the integration

---

## Advanced Configuration

### Customize Entity Names

1. **Settings** → **Devices & Services** → **Schluter DITRA-HEAT**
2. Click on a thermostat
3. Click the gear icon (⚙️)
4. Change "Name" and "Entity ID"

### Customize Polling Interval

By default, the integration polls every 30 seconds. To change:

Edit `const.py` and change:
```python
SCAN_INTERVAL: Final = 60  # Change to 60 seconds
```

Then restart Home Assistant.

### Multiple Locations

If you have thermostats in multiple locations:
1. Add the integration multiple times
2. Use a different Location ID each time
3. Each will show up as a separate integration

---

## Getting Help

### Before Asking for Help

1. Check the logs:
   - **Settings** → **System** → **Logs**
   - Look for errors mentioning `schluter_heat`
2. Try reloading the integration
3. Try removing and re-adding with fresh credentials

### Where to Get Help

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community support
- **Home Assistant Community**: General HA help

### What to Include

When reporting issues, include:
1. Home Assistant version
2. Integration version
3. Number of thermostats
4. Error messages from logs
5. Steps to reproduce the problem

---

## Upgrade Guide

### From v1.0.0 to v2.0.0 (Future)

Instructions will be added here when new versions are released.

### Keeping Up to Date

**HACS Users:**
- HACS will notify you of updates
- Click "Update" when available

**Manual Users:**
- Watch GitHub releases
- Download and replace files
- Restart Home Assistant

---

## Uninstallation

To remove the integration:

1. **Settings** → **Devices & Services**
2. Find "Schluter DITRA-HEAT"
3. Click ⋮ (three dots) → **Delete**
4. Confirm removal
5. (Optional) Delete files from `custom_components/schluter_heat/`
6. Restart Home Assistant

---

## Next Steps

Once installed, check out:
- **[README.md](README.md)** - Feature overview and examples
- **[AUTOMATIONS.md](AUTOMATIONS.md)** - More automation ideas
- **[FAQ.md](FAQ.md)** - Common questions

Happy automating! 🏠🔥
