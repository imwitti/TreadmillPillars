import asyncio
import json
from datetime import datetime
from bleak import BleakScanner, BleakClient

HR_SERVICE_UUID = "0000180D-0000-1000-8000-00805f9b34fb"
HR_MEASUREMENT_UUID = "00002A37-0000-1000-8000-00805f9b34fb"

log_file = "hr_monitor_log.json"
log_data = []

def hr_notification_handler(_, data: bytearray):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "raw_bytes": list(data),
        "hex": data.hex()
    }
    log_data.append(entry)
    print(f"[{entry['timestamp']}] Raw: {entry['raw_bytes']} Hex: {entry['hex']}")

async def main():
    print("Scanning for heart rate monitor...")
    devices = await BleakScanner.discover()

    hr_monitor = None
    for device in devices:
        uuids = device.metadata.get("uuids", [])
        if HR_SERVICE_UUID.lower() in [uuid.lower() for uuid in uuids]:
            hr_monitor = device
            break

    if not hr_monitor:
        print("No heart rate monitor with HR service found.")
        return

    print(f"Connecting to {hr_monitor.name} ({hr_monitor.address})...")
    async with BleakClient(hr_monitor.address) as client:
        await asyncio.sleep(1.0)  # Give time for connection to stabilize
        print("Connected. Subscribing to heart rate notifications...")
        try:
            await client.start_notify(HR_MEASUREMENT_UUID, hr_notification_handler)
            print("Logging for 60 seconds... (Ctrl+C to stop early)")
            await asyncio.sleep(60)
            await client.stop_notify(HR_MEASUREMENT_UUID)
        except Exception as e:
            print(f"[ERROR] Notification failed: {e}")

    with open(log_file, "w") as f:
        json.dump(log_data, f, indent=2)
    print(f"Saved log to {log_file}")

if __name__ == "__main__":
    asyncio.run(main())
