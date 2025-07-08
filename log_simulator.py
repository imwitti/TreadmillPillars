import json
import asyncio
import os

async def simulate_from_log(callback, log_path=None):
    if log_path is None:
        base_dir = os.path.dirname(__file__)
        log_path = os.path.join(base_dir, "Simulation", "treadmill_log.json")

    try:
        with open(log_path, "r") as f:
            log_entries = json.load(f)
    except FileNotFoundError:
        print(f"[Sim] Log file not found at: {os.path.abspath(log_path)}")
        return

    for entry in log_entries:
        raw_bytes = bytes.fromhex(entry["raw"])
        #print(f"[Sim] Sending: {entry['timestamp']} raw={entry['raw']}")
        callback(None, raw_bytes)
        await asyncio.sleep(1)
