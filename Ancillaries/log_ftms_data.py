import asyncio
import json
import time
from datetime import datetime
from bleak import BleakScanner, BleakClient

FTMS_SERVICE_UUID = "00001826-0000-1000-8000-00805f9b34fb"
TREADMILL_DATA_UUID = "00002ACD-0000-1000-8000-00805f9b34fb"

log_file = "treadmill_log.json"
log_data = []

def parse_treadmill_data(data: bytearray):
    flags = int.from_bytes(data[0:2], byteorder='little')
    idx = 2

    speed = distance = elapsed_time = incline = None

    if flags & 0x01:  # Bit 0 = speed present
        speed = int.from_bytes(data[idx:idx+2], 'little') / 100.0
        idx += 2

    if flags & 0x04:  # Bit 2 = distance present
        distance = int.from_bytes(data[idx:idx+3], 'little') / 1000.0
        idx += 3

    if flags & 0x08:  # Bit 3 = incline present
        incline = int.from_bytes(data[idx:idx+2], 'little', signed=True) / 10.0
        idx += 2

    if flags & 0x0400:  # Bit 10 = elapsed time present
        elapsed_time = int.from_bytes(data[idx:idx+3], 'little')
        idx += 3

    return {
        "speed_kmh": speed,
        "distance_km": distance,
        "incline_percent": incline,
        "elapsed_time_s": elapsed_time,
    }

def notification_handler(_, data: bytearray):
    parsed = parse_treadmill_data(data)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "raw": data.hex(),
        "parsed": parsed
    }
    log_data.append(entry)
    print(f"[{entry['timestamp']}] {parsed}")

async def main():
    print("Scanning for treadmill...")
    devices = await BleakScanner.discover()

    treadmill = None
    for device in devices:
        if FTMS_SERVICE_UUID.lower() in [uuid.lower() for uuid in device.metadata.get("uuids", [])]:
            treadmill = device
            break

    if not treadmill:
        print("Treadmill with FTMS service not found.")
        return

    print(f"Connecting to {treadmill.name} ({treadmill.address})...")
    async with BleakClient(treadmill.address) as client:
        print("Connected. Subscribing to treadmill data notifications...")
        await client.start_notify(TREADMILL_DATA_UUID, notification_handler)

        try:
            print("Logging for 60 seconds... (Ctrl+C to stop early)")
            await asyncio.sleep(60)
        except KeyboardInterrupt:
            print("Stopped by user.")

        await client.stop_notify(TREADMILL_DATA_UUID)

    with open(log_file, "w") as f:
        json.dump(log_data, f, indent=2)
    print(f"Saved log to {log_file}")

if __name__ == "__main__":
    asyncio.run(main())
