# treadmill_control.py
import asyncio
import platform
from bleak import BleakScanner, BleakClient

ftms_service_uuid = "00001826-0000-1000-8000-00805f9b34fb"
control_point_uuid = "00002AD9-0000-1000-8000-00805f9b34fb"
treadmill_data_uuid = "00002ACD-0000-1000-8000-00805f9b34fb"

class TreadmillControl:
    def __init__(self, testing=None):
        self.client = None
        if testing is None:
            self.testing = platform.system() == "Windows"
        else:
            self.testing = testing
        self.current_speed = 0.0
        

    async def connect(self, target_name=None, target_address=None):
        if self.testing:
            print("Simulated connection to treadmill.")
            self.client = "SimulatedClient"  # Mock client to indicate connection
            return

        for attempt in range(6):
            try:
                print(f"BLE connection attempt {attempt + 1}")
                devices = await BleakScanner.discover(return_adv=True)

                treadmill = None
                for device, adv_data in devices.values():
                    print(f"- {device.name or 'Unknown'} ({device.address})")

                    # Priority 1: FTMS service
                    if ftms_service_uuid in adv_data.service_uuids:
                        treadmill = device
                        print("Found FTMS treadmill.")
                        break

                    # Priority 2: Match by name
                    if target_name and device.name == target_name:
                        treadmill = device
                        print(f"Matched treadmill by name: {target_name}")
                        break

                    # Priority 3: Match by MAC address
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
        await asyncio.sleep(1)  # Wait for the response
        await self.client.stop_notify(control_point_uuid)

    async def start_monitoring(self, callback):
        if self.testing:
            print("Simulated start monitoring.")
            # Simulate data
            async def simulate_data():
                while True:
                    speed_value = int(self.current_speed * 100).to_bytes(2, byteorder='little')
                    data = bytearray([0x08, 0x00]) + speed_value + bytearray([0x00, 0x00, 0x00, 0x00, 0x0A, 0x00])
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
    flags = data[0]
    speed = int.from_bytes(data[2:4], byteorder='little') / 100.0
    distance = int.from_bytes(data[4:7], byteorder='little') /1000
    incline = None
    if flags & 0x08:  # Check if Inclination and Ramp Angle Setting Present bit is set
        incline = int.from_bytes(data[7:9], byteorder='little', signed=True) / 10.0
    return speed, distance, incline
