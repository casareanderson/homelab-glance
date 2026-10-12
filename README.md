# homelab-glance

A desk display for the homelab: an **ESP32-2432S028R ("Cheap Yellow Display", CYD)** —
2.8" 320×240 ILI9341 + XPT2046 touch — showing your **warden** security status at a glance.
No cloud; it reads values over the LAN via Home Assistant.

## How it works
- **Home Assistant** polls warden's read-only REST API (`/api/v1/summary`) with a bearer token
  and exposes a few sensors (see `ha/warden-glance-sensors.yaml`).
- **ESPHome** (`glance.yaml`) runs on the CYD, imports those HA sensors over the native API,
  and draws them on the screen. Updates push from HA — no polling on the ESP.

## Flash it (tomorrow)
1. In warden: **Settings → Connect → Make a token** (name it `homelab-glance`). Copy the `wdn_…`.
2. In Home Assistant: drop `ha/warden-glance-sensors.yaml` into a `packages:` include (or paste its
   `sensor:`/`template:` blocks into `configuration.yaml`), set `warden_bearer` in HA secrets, restart HA.
   Confirm `sensor.warden_waiting`, `sensor.warden_kev`, `sensor.warden_mode` appear.
3. `cp secrets.yaml.example secrets.yaml` and fill in wifi + your HA details.
4. Flash with ESPHome (dashboard or `esphome run glance.yaml`), USB first time then OTA.

## Notes
- **Network:** the CYD must reach Home Assistant. If you put it on the IoT VLAN (VLAN10), allow it to
  HA's IP, or keep this trusted display on the main LAN. Warden stays reached by *HA*, not the ESP.
- **CYD variants differ** on the touch controller and the RGB-LED polarity; pins below match the common
  ESP32-2432S028R. The touch needs a one-time calibration — adjust `calibration:` after first flash.
- This is a **starting point**: verify the display/touch on your exact board and tweak the layout.

AGPL-3.0 · part of the C1 Lab homelab.
