# homelab-glance

A desk display for the homelab: an **ESP32-2432S028R ("Cheap Yellow Display", CYD)**,
2.8" 320×240 with touch, styled like e-ink (paper, black ink, one red ink, serif numbers, dim backlight).
**Tap to flip pages:**

| Page | Shows |
|---|---|
| **Warden** | waiting for you · known-exploited CVEs (red when > 0) · mode · open findings · hot hosts |
| **Buses** | next TfL route 20 each way from Chandler Road (to Loughton / to Debden), counting down |
| **Homelab** | nodes up (Beszel) · services up (Uptime Kuma) · backups fresh · busiest CPU / RAM / disk · what's down |
| **Network** | internet up + ping · devices on the LAN · CrowdSec bans · warden events today |

## How it works
```
warden, TfL, Beszel, Kuma, backups, nmap ──> glance-feed (Hermes, every 60 s) ──> glance.json ──> board (every 30 s)
```
The board makes **one plain-HTTP request on the LAN** (`http://192.168.8.120:8798/glance.json`, ~400 bytes).
Hermes does all the slow work (TLS, logins, scans), so the board never blocks, which was what tripped the
ESP's 5 s watchdog and made it restart and blink. **No tokens live on the board.** Slow sources are cached
(Kuma and the LAN scan every 5 min, backups every 30 min), and a failing source just drops off its page.
The screen only redraws when the data changes, plus once a minute for the bus countdown.

`feed/` holds the Hermes side: `glance-feed.py` + a systemd timer, and a tiny read-only LAN web server
(`glance-feed-http.service`, bound to Hermes' LAN IP).

## Build & flash
```bash
python3 -m venv ~/esphome-venv && source ~/esphome-venv/bin/activate && pip install esphome
gh repo clone casareanderson/homelab-glance && cd homelab-glance
cp secrets.yaml.example secrets.yaml      # fill in wifi_ssid + wifi_password
esphome run glance-home.yaml              # USB the first time, WiFi (OTA) after that
```
`secrets.yaml` is gitignored. `glance-flash.yaml` is the same build without WiFi baked in. On first boot it
opens a hotspot, **homelab-glance setup**, so you can pick a network from your phone.

## Notes
- **Board variant:** the default is the two-USB CYD (micro-USB + USB-C, ST7789V). Others:
  `-s display_model ESP32-2432S028` (micro-USB only, ILI9341) or `-s display_model ESP32-2432S028-9342`.
  Fuzzy static = wrong variant. Paper looks dark or colours look negative? Add `-s invert_colors true`.
- The display uses ESPHome's `mipi_spi` driver, which draws in strips. A full-screen buffer won't fit in this
  ESP32's RAM ("Could not allocate buffer for display").
- The `gpio_pullup_en … input-only pad` line at boot is the touch IRQ pin (GPIO36) and is harmless.
- **Bus stops / feed URL** are `substitutions:` at the top of `glance-flash.yaml` (labels) and constants at the
  top of `feed/glance-feed.py` (stop IDs). Find stops with
  `curl "https://api.tfl.gov.uk/StopPoint/?lat=LAT&lon=LON&stopTypes=NaptanPublicBusCoachTram&radius=400"`.
- Not shown, on purpose: AdGuard stats (the GL.iNet build ties its API to the router UI session, 401) and
  NetBird peers (it only counts peers with a live tunnel, so "1/9" would look like an outage).
- The board's page (`http://homelab-glance.local`) has the backlight slider and live logs. It's LAN-only, and
  OTA has no password, so keep the display on the trusted LAN.
- `glance.yaml` + `ha/` are the older Home-Assistant-driven build.
- **True e-paper:** the same feed works on a LilyGo T5 4.7" or a Waveshare e-paper + ESP32 with only the
  `display:` block swapped.

AGPL-3.0 · part of the C1 Lab homelab.
