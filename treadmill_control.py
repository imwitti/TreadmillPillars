# treadmill_control.py
import asyncio
import platform
import time
from bleak import BleakScanner, BleakClient

ftms_service_uuid = "00001826-0000-1000-8000-00805f9b34fb"
control_point_uuid = "00002AD9-0000-1000-8000-00805f9b34fb"
treadmill_data_uuid = "00002ACD-0000-1000-8000-00805f9b34fb"

class TreadmillControl:
    def __init__(self, testing=None):
        self.client = None
        self.testing = platform.system() == "Windows" if testing is None else testing
        self.current_speed = 0.0
        self.start_time = None
        self.simulated_distance = 0.0

    async def connect(self, target_name=None, target_address=None):
        if self.testing:
            print("Simulated connection to treadmill.")
            self.client = "SimulatedClient"
            self.start_time = time.time()
            return

        for attempt in range(6):
            try:
                print(f"BLE connection attempt {attempt + 1}")
                devices = await BleakScanner.discover(return_adv=True)

                treadmill = None
                for device, adv_data in devices.values():
                    print(f"- {device.name or 'Unknown'} ({device.address})")

                    if ftms_service_uuid in adv_data.service_uuids:
                        treadmill = device
                        print("Found FTMS treadmill.")
                        break
                    if target_name and device.name == target_name:
                        treadmill = device
                        print(f"Matched treadmill by name: {target_name}")
                        break
                    if target_address and device.address.lower() == target_address.lower():
                        treadmill = device
                        print(f"Matched treadmill by address: {target_address}")
                        break

                if treadmill:
                    self.client = BleakClient(treadmill.address)
                    await self.client.connect()
                    print(f"Connected to {treadmill.name or 'Unknown'} ({treadmill.address})")
                    return

                raise Exception("Treadmill not found.")
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2)

        raise Exception("Failed to connect after 3 attempts.")

    async def disconnect(self):
        if self.testing:
            print("Simulated disconnection from treadmill.")
            self.client = None
            return
        if self.client:
            await self.client.disconnect()

    async def request_control(self):
        if self.testing:
            print("Simulated control request.")
            return
        await self.client.write_gatt_char(control_point_uuid, bytearray([0x00]))
        await self.wait_for_response()

    async def set_speed(self, speed_kmh):
        self.current_speed = speed_kmh
        if self.testing:
            speed_mph = round(speed_kmh / 1.59, 2)
            print(f"Simulated setting speed to {speed_kmh:.2f} km/h ({speed_mph:.2f} mph)")
            return
        speed_mph = round(speed_kmh / 1.59, 2)
        speed_value = int(speed_mph * 100).to_bytes(2, byteorder='little')
        await self.client.write_gatt_char(control_point_uuid, bytearray([0x02]) + speed_value)
        print(f"Set speed to {speed_kmh:.2f} km/h ({speed_mph:.2f} mph)")
        await self.wait_for_response()

    async def set_incline(self, incline):
        if self.testing:
            print(f"Simulated setting incline to {incline:.1f} %")
            return
        incline_value = int(incline * 10).to_bytes(2, byteorder='little', signed=True)
        await self.client.write_gatt_char(control_point_uuid, bytearray([0x03]) + incline_value)
        print(f"Set incline to {incline:.1f} %")
        await self.wait_for_response()

    async def wait_for_response(self):
        if self.testing:
            print("Simulated waiting for response.")
            return

        def handle_response(sender, data):
            op_code = data[0]
            request_op_code = data[1]
            result_code = data[2]
            if result_code == 0x01:
                print(f"Operation {request_op_code} succeeded")
            else:
                print(f"Operation {request_op_code} failed with result code {result_code}")

        await self.client.start_notify(control_point_uuid, handle_response)
        await asyncio.sleep(1)
        await self.client.stop_notify(control_point_uuid)

    async def start_monitoring(self, callback):
        if self.testing:
            print("Simulated start monitoring.")
            if self.start_time is None:
                self.start_time = time.time()
            self.simulated_distance = 0.0  # Reset distance on start

            async def simulate_data():
                while True:
                    elapsed_time = time.time() - self.start_time
                    self.simulated_distance += (self.current_speed / 3600)  # km per sec

                    distance_int = round(self.simulated_distance * 1000 / 10) * 10
                    speed_int = int(self.current_speed * 100)
                    elapsed_int = int(elapsed_time)

                    # Flags: bits 0, 2, 10 → Speed, Distance, Elapsed Time
                    flags = 0b0000010100000100
                    data = bytearray([
                        flags & 0xFF, (flags >> 8) & 0xFF,
                        speed_int & 0xFF, speed_int >> 8,
                        distance_int & 0xFF, (distance_int >> 8) & 0xFF, (distance_int >> 16) & 0xFF,
                        elapsed_int & 0xFF, (elapsed_int >> 8) & 0xFF, (elapsed_int >> 16) & 0xFF
                    ])

                    print(f"[Sim] Speed: {self.current_speed:.2f} km/h, Distance: {self.simulated_distance:.3f} km, Elapsed: {int(elapsed_time)}s")
                    callback(None, data)

                    await asyncio.sleep(1)

            asyncio.create_task(simulate_data())
            return

        if self.client:
            await self.client.start_notify(treadmill_data_uuid, callback)

    async def stop_monitoring(self):
        if self.testing:
            print("Simulated stop monitoring.")
            return
        if self.client:
            await self.client.stop_notify(treadmill_data_uuid)

    async def increase_speed(self):
        await self.set_speed(self.current_speed + 0.5)

    async def decrease_speed(self):
        await self.set_speed(self.current_speed - 0.5)

def parse_treadmill_data(data):
    flags = int.from_bytes(data[0:2], byteorder='little')
    idx = 2

    speed = distance = elapsed_time = incline = None

    try:
        if flags & 0x01 and len(data) >= idx + 2:  # Bit 0 = speed present
            speed = int.from_bytes(data[idx:idx+2], 'little') / 100.0
            idx += 2

        if flags & 0x04 and len(data) >= idx + 3:  # Bit 2 = distance present
            distance = int.from_bytes(data[idx:idx+3], 'little') / 1000.0
            idx += 3

        if flags & 0x08 and len(data) >= idx + 2:  # Bit 3 = incline present
            incline = int.from_bytes(data[idx:idx+2], 'little', signed=True) / 10.0
            idx += 2

        if flags & 0x0400 and len(data) >= idx + 3:  # Bit 10 = elapsed time present
            elapsed_time = int.from_bytes(data[idx:idx+3], 'little')
            idx += 3
    except Exception as e:
        print(f"[WARN] Failed to parse treadmill data: {e}")

    return speed, distance, incline, elapsed_time
