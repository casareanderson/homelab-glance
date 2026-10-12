#!/usr/bin/env python3
"""glance-feed — one small JSON for the homelab-glance desk display (ESP32 CYD).

Gathers facts (no LLM) every minute and writes /var/lib/glance-feed/glance.json,
served on the LAN by glance-feed-http. The board makes one quick plain-HTTP request
instead of slow TLS calls to warden/TfL (which tripped its 5 s watchdog).

Slow sources (Kuma, backups, LAN scan) are cached and refreshed less often.
Every section is optional: a failing source becomes null, never breaks the feed.
"""
import json
import os
import re
import subprocess
import sys
import time

import requests

sys.path.insert(0, "/opt/hermes-agent")
sys.path.insert(0, "/root/.hermes/scripts")

OUT_DIR = "/var/lib/glance-feed"
OUT = f"{OUT_DIR}/glance.json"
CACHE = "/var/cache/glance-feed.json"  # kept out of the served dir
WARDEN = "https://warden.cn1-lab.uk/api/v1/summary"
TFL = "https://api.tfl.gov.uk/StopPoint/{}/Arrivals"
BUS_LINE = "20"
BUS_STOPS = {"a": "150042006003", "b": "150042006004"}  # Chandler Rd: to Loughton / to Debden
LAN = "192.168.8.0/24"
SLOW = {"kuma": 300, "backup": 1800, "lan": 300, "patches": 900}  # seconds between refreshes


def warden_token():
    tok = os.environ.get("WARDEN_TOKEN")
    if tok:
        return tok
    for line in open("/root/.hermes/profiles/sec/.env"):
        if line.startswith("WARDEN_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"')
    return None


def warden():
    r = requests.get(WARDEN, headers={"Authorization": f"Bearer {warden_token()}"}, timeout=10)
    r.raise_for_status()
    d = r.json()
    k = d.get("kpi", {})
    hh = d.get("host_health", {})
    return {"mode": d.get("mode", "?"), "wait": k.get("approvals", 0), "kev": k.get("vuln_kev", 0),
            "bans": k.get("bans", 0), "ev24": k.get("events_24h", 0), "find": k.get("findings_open", 0),
            "hot": hh.get("hot", 0)}


def patches():
    """Pending package updates + reboots, from warden's vulns view (it scans every host daily)."""
    r = requests.get(WARDEN.replace("/summary", "/vulns"),
                     headers={"Authorization": f"Bearer {warden_token()}"}, timeout=20)
    r.raise_for_status()
    ts = r.json().get("targets", [])
    upg = [t for t in ts if (t.get("upgradable") or 0) > 0]
    reb = [t["name"][:12] for t in ts if t.get("reboot_required")]
    return {"pending": sum(t["upgradable"] for t in upg), "hosts": len(upg), "reboot": reb[:3], "n_reboot": len(reb)}


def buses():
    out = {}
    for key, stop in BUS_STOPS.items():
        r = requests.get(TFL.format(stop), timeout=10)
        r.raise_for_status()
        t = sorted(a["timeToStation"] for a in r.json()
                   if a.get("lineName") == BUS_LINE and a.get("timeToStation", -1) >= 0)
        out[key] = (t + [-1, -1])[:2]
    return out


def lab():
    d = json.load(open("/var/lib/beszel-snapshot/hosts.json"))
    hosts = d.get("hosts", [])
    up = [h for h in hosts if h.get("status") == "up" and not h.get("stale")]
    down = [h["name"] for h in hosts if h not in up]

    def top(key):
        h = max(up, key=lambda h: h.get(key) or 0, default=None)
        return [h["name"][:10], round(h.get(key) or 0)] if h else None
    return {"up": len(up), "total": len(hosts), "down": down[:3],
            "cpu": top("cpu"), "mem": top("mem_pct"), "disk": top("disk_pct")}


def kuma():
    import hermes_secrets as secrets
    from uptime_kuma_api import UptimeKumaApi
    a = UptimeKumaApi(secrets.get("KUMA_URL", "/Kuma"), timeout=30)
    try:
        a.login(secrets.get("KUMA_USER", "/Kuma"), secrets.get("KUMA_ADMIN_PASSWORD", "/Passwords"))
        mons = {m["id"]: m for m in a.get_monitors() if m.get("active")}
        beats = a.get_heartbeats()
    finally:
        a.disconnect()
    down = []
    for mid, m in mons.items():
        hb = beats.get(mid) or beats.get(str(mid)) or []
        last = hb[-1] if isinstance(hb, list) and hb else None
        st = last.get("status") if isinstance(last, dict) else None
        if st is not None and int(st) not in (1, 3):  # 1 up, 3 maintenance
            down.append(m.get("name", "?"))
    return {"up": len(mons) - len(down), "total": len(mons), "down": down[:3]}


def backup():
    p = subprocess.run(["python3", "/root/.hermes/scripts/fleet-backup-verify.py"],
                       capture_output=True, text=True, timeout=120)
    fresh = stale = missing = 0
    for m in re.finditer(r"(\d+) fresh, (\d+) stale, (\d+) missing", p.stdout):
        fresh, stale, missing = fresh + int(m[1]), stale + int(m[2]), missing + int(m[3])
    if not (fresh or stale or missing):
        raise RuntimeError("no backup summary")
    return {"fresh": fresh, "stale": stale, "missing": missing}


def lan():
    p = subprocess.run(["nmap", "-sn", "-n", LAN], capture_output=True, text=True, timeout=120)
    return {"devices": p.stdout.count("Host is up")}


def internet():
    p = subprocess.run(["ping", "-c3", "-W2", "-q", "1.1.1.1"], capture_output=True, text=True, timeout=15)
    m = re.search(r"= [\d.]+/([\d.]+)/", p.stdout)
    loss = re.search(r"(\d+)% packet loss", p.stdout)
    return {"up": p.returncode == 0, "ms": round(float(m[1])) if m else None,
            "loss": int(loss[1]) if loss else 100}


def safe(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 — one bad source must not blank the screen
        print(f"{fn.__name__}: {type(e).__name__}: {e}"[:200], file=sys.stderr)
        return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    try:
        cache = json.load(open(CACHE))
    except Exception:  # noqa: BLE001
        cache = {}
    now = int(time.time())
    for name, every in SLOW.items():
        c = cache.get(name)
        if not c or now - c.get("at", 0) >= every or c.get("v") is None:
            v = safe(globals()[name])
            if v is not None or not c:
                cache[name] = {"at": now, "v": v}
    feed = {
        "gen": now,
        "w": safe(warden),
        "bus": safe(buses),
        "lab": safe(lab),
        "kuma": cache["kuma"]["v"],
        "bk": cache["backup"]["v"],
        "pt": cache["patches"]["v"],
        "net": {"inet": safe(internet), "lan": cache["lan"]["v"]},
    }
    json.dump(cache, open(CACHE + ".tmp", "w"))
    os.replace(CACHE + ".tmp", CACHE)
    with open(OUT + ".tmp", "w") as f:
        json.dump(feed, f, separators=(",", ":"))
    os.replace(OUT + ".tmp", OUT)


if __name__ == "__main__":
    main()
