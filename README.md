# homelab-glance

A desk display for the homelab: an **ESP32-2432S028R ("Cheap Yellow Display", CYD)** —
2.8" 320×240 ILI9341 + XPT2046 touch — showing your **warden** security status at a glance.
No cloud; it polls warden's read-only REST API over the LAN.

Shows: **waiting for you** · **known-exploited CVEs** (in red ink when there are any) · warden **mode** · date and last update.
Below that: the **next two TfL buses each way** from a nearby stop (default: route 20 at Chandler Road,
to Loughton and to Debden). The minutes count down between polls (every 60 s); "due" means under a minute.

Styled like e-ink: paper background, black ink, one red ink, serif numbers, a dimmed backlight and slow redraws.
It's still an LCD, so it glows; for true e-paper see the note at the bottom.

## You need
- The CYD board + a USB data cable. **No SD card** (the slot is optional/unused).
- A Mac/PC with ESPHome to build & flash.

## Build & flash (on your Mac)
Nothing secret goes into the build: no `secrets.yaml`, no token on the command line.
```bash
python3 -m venv ~/esphome-venv && source ~/esphome-venv/bin/activate
pip install esphome
git clone git@github.com:casareanderson/homelab-glance.git
cd homelab-glance
esphome run glance-flash.yaml
```
Pick the USB serial port (`/dev/cu.usbserial-…` / `/dev/cu.wchusbserial-…`). The first build downloads the ESP
toolchain (a few GB, a few minutes). If it sticks on "Connecting…", hold the board's **BOOT** button.

## Setup — tap through it on the screen
After flashing, the display is a **4-step guide; tap anywhere for the next step**:
1. **WiFi** — on your phone join **`homelab-glance setup`** and pick your home WiFi.
2. **Make a token** — in warden: **Settings → Connect → New token** (name it `homelab-glance`), copy the `wdn_…`.
3. **Paste it** — on the same WiFi open the address on screen (or `http://homelab-glance.local`),
   paste into **Warden token**, press Enter.
4. **Done** — it switches to the glance by itself.

The token is stored in the board's flash (survives reboots and re-flashes) and the web page never shows it back.
To change it, paste a new one; **Clear warden token** on the same page puts the guide back.
Once set up, a tap refreshes immediately; otherwise it polls every 60 s.

Later updates go over WiFi, no cable needed: `esphome run glance-flash.yaml` and pick the network device.

## Notes
- **Bus stops** are the `substitutions:` at the top of `glance-flash.yaml`. Find yours with
  `curl "https://api.tfl.gov.uk/StopPoint/?lat=LAT&lon=LON&stopTypes=NaptanPublicBusCoachTram&radius=400"`
  and use the `naptanId`. The TfL API needs no key at this polling rate. Towards Loughton the 20 is signed
  *Walthamstow Central*, which is why the label is set by hand.
- **Network:** the board must reach `warden.cn1-lab.uk` (resolves to the LAN). Keep this trusted display on the
  main LAN; if you put it on the IoT VLAN, allow it to warden's IP. Anyone on the LAN can open its page to
  replace the token or adjust the backlight. They can't read the token back.
- **CYD variants differ** slightly: if colours look inverted (dark paper), flip `invert_colors:` in `glance-flash.yaml`.
  Taps only need to land *somewhere*, so touch calibration doesn't matter here.
- **Backlight** starts at 40% for the paper look; adjust it on the board's web page.
- The warden token is read-only (it can only *read* the console summary — never ban/patch/approve). Revoke it
  any time in Settings → Connect; the screen will say **token rejected**.
- `glance.yaml` + `ha/` are an alternative Home-Assistant-driven build if you'd rather route through HA
  (that one uses `secrets.yaml`, see `secrets.yaml.example`).
- **True e-paper:** the same polling works on a LilyGo T5 4.7" or a Waveshare e-paper + ESP32 with only the
  `display:` block swapped. That gives no glow, readability in sunlight, and weeks on a battery.

AGPL-3.0 · part of the C1 Lab homelab.
