# homelab-glance

A desk display for the homelab: an **ESP32-2432S028R ("Cheap Yellow Display", CYD)** —
2.8" 320×240 ILI9341 + XPT2046 touch — showing your **warden** security status at a glance.
No cloud; it polls warden's read-only REST API over the LAN.

Shows: warden **mode** (detect-only / enforcing) · **waiting for you** · **known-exploited CVEs** · a clock.

## You need
- The CYD board + a USB cable. **No SD card** (the slot is optional/unused).
- A Mac/PC with ESPHome to build & flash.

## Build & flash (on your Mac)
```bash
brew install esphome            # or: pipx install esphome
git clone git@github.com:casareanderson/homelab-glance.git
cd homelab-glance
```
1. In warden: **Settings → Connect → New token** (name it `homelab-glance`). Copy the `wdn_…`.
2. `cp secrets.yaml.example secrets.yaml` and paste it:  `warden_auth: "Bearer wdn_…"`
3. Plug the CYD in over USB, then:
   ```bash
   esphome run glance-flash.yaml
   ```
   Pick the USB serial port; it compiles and flashes (first build downloads the ESP toolchain — a few min, fast on a Mac).
4. **First boot** it makes a WiFi AP **"homelab-glance setup"** — connect to it from your phone/laptop and enter your WiFi.
   It then joins, reaches warden, and the screen fills in.

## Notes
- **Network:** the board must reach `warden.cn1-lab.uk` (resolves to the LAN). If you put it on the IoT VLAN,
  allow it to warden's IP, or keep this trusted display on the main LAN.
- **CYD variants differ** slightly: if colours look inverted, flip `invert_colors:` in `glance-flash.yaml`;
  the touch (unused for now) may need calibration later. Pins below match the common ESP32-2432S028R.
- The warden token is read-only (it can only *read* the console summary — never ban/patch/approve). Revoke it
  any time in Settings → Connect.
- `glance.yaml` + `ha/` are an alternative Home-Assistant-driven build if you'd rather route through HA.

AGPL-3.0 · part of the C1 Lab homelab.
