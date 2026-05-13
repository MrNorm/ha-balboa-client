# Balboa Spa (Serial-to-IP) — Home Assistant integration

A Home Assistant custom integration for Balboa-controlled spas connected via a generic RS-485-to-TCP bridge (Elfin-EW11, ser2net, socat, ESPHome serial server, etc.). **No Balboa WiFi module required.**

## Why this exists

Home Assistant ships a built-in `balboa` integration backed by [pybalboa](https://github.com/garbled1/pybalboa), but pybalboa waits for a `MODULE_IDENTIFICATION` response that only an actual Balboa WiFi module (50350) sends. With a generic serial-to-IP bridge there is no such module on the bus, the message never arrives, and the config flow times out — even though everything else (status updates, pump control, etc.) works fine.

This integration vendors a small patch to pybalboa that:

- Skips the module-identification probe in serial mode.
- Synthesizes a stable, locally-administered MAC from `host:port` so HA can register the device.

Everything else (climate, fan, light, switch, select, time, event, binary sensor) is the same as the upstream integration.

## Requirements

- A Balboa BP-series spa controller.
- An RS-485-to-TCP bridge wired to the spa's RS-485 port:
  - **115200 baud, 8N1, no flow control**
  - Configured in **TCP Server** mode
  - Listening on any port you choose (default 4257)
- Home Assistant 2024.12 or newer.

## Installation (HACS)

1. In HACS → **Integrations** → ⋮ menu → **Custom repositories**.
2. Add this repo URL with category **Integration**.
3. Install **Balboa Spa (Serial-to-IP)**.
4. Restart Home Assistant.
5. **Settings → Devices & services → Add integration → Balboa Spa (Serial-to-IP)**.
6. Enter the bridge's IP and port.

## Installation (manual)

Copy `custom_components/balboa_serial/` into your HA `config/custom_components/` directory and restart.

## Verifying the bridge before adding the integration

If you can see Balboa frames here, the bridge half is working:

```bash
timeout 5 nc <bridge-ip> <bridge-port> | xxd | head
# you should see lines starting with `7e` (the `~` delimiter)
```

If `nc` shows nothing or wrong-looking bytes, fix the bridge first (wrong port / wrong baud / wrong wires / something else holding the socket) — the integration will not work until plain `nc` shows valid frames.

## Coexisting with the official `balboa` integration

The two integrations use different domains (`balboa` vs `balboa_serial`) and isolated copies of pybalboa, so they can run side-by-side without interference. You don't need to remove the official one to try this.

## What's patched

See [`custom_components/balboa_serial/pybalboa/client.py`](custom_components/balboa_serial/pybalboa/client.py) — search for `serial_mode`. Three changes:

1. `__init__` accepts `serial_mode: bool = True` and pre-sets `_module_identification_loaded = True`.
2. When no MAC is supplied, one is derived from `sha256(host:port)` with the `02:` locally-administered prefix.
3. `request_module_identification()` is a no-op in serial mode (saves a useless probe every reconnect).

Everything else in pybalboa is unmodified.

## Credits

- [garbled1/pybalboa](https://github.com/garbled1/pybalboa) — the underlying spa protocol library.
- [Home Assistant core `balboa` integration](https://github.com/home-assistant/core/tree/dev/homeassistant/components/balboa) — the integration scaffolding ported here.
- [ccutrer/balboa_worldwide_app](https://github.com/ccutrer/balboa_worldwide_app) — original protocol reverse-engineering.
- [jshank/bwalink](https://github.com/jshank/bwalink) — the prior-art Docker+MQTT bridge this replaces.
