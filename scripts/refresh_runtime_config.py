#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path


CONFIG_PATH = Path("/etc/sing-box/config.json")
RESOLV_PATH = Path("/etc/resolv.conf")


def default_lan_ip():
    out = subprocess.check_output(["ip", "-o", "-4", "route", "get", "1.1.1.1"], text=True)
    parts = out.split()
    if "src" not in parts:
        raise RuntimeError("cannot detect LAN IPv4 address")
    return parts[parts.index("src") + 1]


def main():
    if not CONFIG_PATH.exists():
        return 0
    lan_ip = default_lan_ip()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    changed = False

    for inbound in config.get("inbounds", []) or []:
        if not isinstance(inbound, dict):
            continue
        if inbound.get("tag") == "dns-in" and inbound.get("listen") != lan_ip:
            inbound["listen"] = lan_ip
            changed = True

    clash = config.setdefault("experimental", {}).setdefault("clash_api", {})
    controller = f"{lan_ip}:9090"
    if clash.get("external_controller") != controller:
        clash["external_controller"] = controller
        changed = True

    if changed:
        CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Updated sing-box listeners for {lan_ip}.")
    else:
        print(f"sing-box listeners already match {lan_ip}.")

    RESOLV_PATH.unlink(missing_ok=True)
    RESOLV_PATH.write_text(
        f"nameserver {lan_ip}\n"
        "nameserver 223.5.5.5\n"
        "nameserver 1.1.1.1\n"
        "options timeout:2 attempts:2\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
