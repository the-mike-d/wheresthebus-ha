<img src="icon.png" alt="" width="96" align="right">

# WheresTheBus for Home Assistant (unofficial)

Brings your child's school bus from the **WheresTheBus** parent app into Home Assistant: where the bus is, how far it is from your stop, roughly how many minutes away it is, and a **Time to leave** sensor you can use for alerts.

> **Unofficial.** This project is not affiliated with, endorsed by, or supported by WheresTheBus LLC or any school district. It talks to the same service the WheresTheBus parent web app uses, which can change at any time without notice and break this integration. Check that using it is acceptable under WheresTheBus's terms for your account. Use at your own risk.

## What you get

One device per student on your account (named after the bus number), with:

| Entity | What it shows |
|---|---|
| `device_tracker` **Location** | The bus on the map while it's running |
| `sensor` **Distance to stop** | Miles between the bus and your stop (as reported by WheresTheBus) |
| `sensor` **Minutes away** | Estimated arrival. Uses WheresTheBus's ETA when it provides one, otherwise learns the bus's approach speed from successive positions. Blank for the first 3 minutes of a run while the speed is learned, and after the bus reaches your stop |
| `binary_sensor` **Time to leave** | On when the bus is due within *travel time + buffer*, or within the alert distance (1 mile by default). Stays off once the bus has reached your stop for that run |
| `binary_sensor` **Bus en route** | On while the bus is reporting a position |
| `sensor` **Status** | WheresTheBus status/notice text, "Reached stop at 6:30 AM" once the bus gets to your stop, or "Outside bus hours" |
| `sensor` **Scheduled time** | The stop time on file |
| `sensor` **Home to stop** | Straight-line miles from your home zone to the stop |

## Polling

The integration only contacts WheresTheBus during the windows you enable, every 15 seconds (the same rate as the app). Outside them it makes no requests.

Defaults: afternoon run **14:00–15:00** on, morning run **06:00–07:00** off, weekdays only.

## Install

### HACS
1. HACS → ⋮ → **Custom repositories** → add `https://github.com/mikedd732/wheresthebus-ha` as an **Integration**.
2. Install **WheresTheBus (unofficial)** and restart Home Assistant.

### Manual
Copy `custom_components/wheresthebus` into your Home Assistant `config/custom_components/` folder and restart.

## Set up
**Settings → Devices & services → Add integration → WheresTheBus**, then sign in with the email and password you use in the WheresTheBus app. Your password is stored in Home Assistant so the integration can sign in again when its session expires.

Then open the integration's **Configure** button to adjust:

- **Home location**: any zone (defaults to `zone.home`; edit it under *Settings → Areas, labels & zones*)
- **Travel time** from home to the stop and an extra **buffer**, in minutes
- **Alert distance**: also turn on *Time to leave* when the bus is within this many miles (default 1, 0 = off). Recommended: winding routes make the minutes estimate run high close to the stop, and the distance check catches that
- Morning / afternoon tracking on/off and their time windows
- Weekdays only

## Example automation

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.school_bus_1234_time_to_leave
    to: "on"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: Bus is coming
      message: >
        {{ states('sensor.school_bus_1234_minutes_away') | round(0) }} min away
        ({{ states('sensor.school_bus_1234_distance_to_stop') }} mi). Time to leave!
```

Replace `1234` with your bus number (check the entity IDs under the integration's device).

## Notes and limits
- Distance and ETA come from (or are derived from) WheresTheBus data. "Minutes away" is a straight-line estimate, so routes that double back can make it jump around.
- The bus counts as having reached your stop when it comes within 0.1 mile (about 500 ft) of it. The rest of that window, *Time to leave* stays off even if the route loops back past you.
- If WheresTheBus rejects your password, Home Assistant will ask you to sign in again.
- Tested with the School District of Lee County, FL. Other districts on WheresTheBus should work, but please open an issue if yours doesn't.

## Changelog
- **0.2.1**: Stop alerting after the bus reaches your stop; alert distance defaults to 1 mile; no ETA during the first 3 minutes of a run; higher minimum learned speed so early estimates don't spike; integration icon.
- **0.2.0**: First public release.

## License
MIT
