# treadmill_control.py

import asyncio
import platform
import time
from bleak import BleakScanner, BleakClient
from log_simulator import simulate_from_log  # only used when testing

ftms_service_uuid = "00001826-0000-1000-8000-00805f9b34fb"
control_point_uuid = "00002AD9-0000-1000-8000-00805f9b34fb"
treadmill_data_uuid = "00002ACD-0000-1000-8000-00805f9b34fb"

class TreadmillControl:
    def __init__(self, testing=None, log_path="treadmill_log.json"):
        self.client = None
        self.testing = platform.system() == "Windows" if testing is None else testing
        self.log_path = log_path
        self.current_speed = 0.0
        self.start_time = None

    async def connect(self, target_name=None, target_address=None):
        if self.testing:
            print("Simulated connection to treadmill.")
            self.client = "SimulatedClient"
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

        raise Exception("Failed to connect after 6 attempts.")

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
            print("Simulated start monitoring from log.")
            asyncio.create_task(simulate_from_log(callback, self.log_path))
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


def parse_treadmill_data(data: bytes):
    flags = int.from_bytes(data[0:2], byteorder='little')
    idx = 2

    def read_uint8():
        nonlocal idx
        val = data[idx]
        idx += 1
        return val

    def read_uint16():
        nonlocal idx
        val = int.from_bytes(data[idx:idx+2], 'little')
        idx += 2
        return val

    def read_sint16():
        nonlocal idx
        val = int.from_bytes(data[idx:idx+2], 'little', signed=True)
        idx += 2
        return val

    def read_uint24():
        nonlocal idx
        val = int.from_bytes(data[idx:idx+3] + b'\x00', 'little')
        idx += 3
        return val

    parsed = {}

    if (flags & 0x01) == 0:
        parsed["speed_kmh"] = read_uint16() / 100.0

    if flags & (1 << 1):
        parsed["average_speed_kmh"] = read_uint16() / 100.0

    if flags & (1 << 2):
        parsed["distance_km"] = read_uint24() / 1000.0

    if flags & (1 << 3):
        parsed["incline_percent"] = read_sint16() / 10.0
        idx += 2  # Skip Ramp Angle Setting

    if flags & (1 << 4):
        parsed["positive_elevation_gain_m"] = read_uint16()
        parsed["negative_elevation_gain_m"] = read_uint16()

    if flags & (1 << 5):
        parsed["instantaneous_pace_sec_per_km"] = read_uint16()

    if flags & (1 << 6):
        parsed["average_pace_sec_per_km"] = read_uint16()

    if flags & (1 << 7):
        parsed["total_energy_kcal"] = read_uint16()
        parsed["energy_per_hour_kcal"] = read_uint16()
        parsed["energy_per_minute_kcal"] = read_uint8()

    if flags & (1 << 8):
        parsed["heart_rate_bpm"] = read_uint8()

    if flags & (1 << 9):
        parsed["metabolic_equivalent"] = read_uint8() / 10.0

    if flags & (1 << 10):
        parsed["elapsed_time_s"] = read_uint16()

    if flags & (1 << 11):
        parsed["remaining_time_s"] = read_uint16()

    if flags & (1 << 12):
        parsed["force_on_belt_n"] = read_sint16()
        parsed["power_output_w"] = read_sint16()

    #return parsed

    values = (
        parsed.get("speed_kmh"),
        parsed.get("distance_km"),
        parsed.get("incline_percent"),
        parsed.get("elapsed_time_s")
    )

    #print(f"[TEST MODE] Parsed treadmill data: speed={values[0]}, distance={values[1]}, incline={values[2]}, elapsed_time={values[3]}")

    return values
