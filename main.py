import math
import yaml
import struct
import time
import os
import asyncio
import socket
from bleak import BleakClient
import subprocess

# load config
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

PLAYLIST = config.get("playlist", "your_music.mp3")
MAX_VOL = config.get("output_values", {}).get("max_volume", 220)
MIN_TEMPO = config.get("output_values", {}).get("min_tempo", 0.6)
SENSITIVITY = config.get("control_parameters", {}).get("sensitivity", 1.0)
SMOOTHING = config.get("control_parameters", {}).get("smoothing_factor", 0.1)
NOISE_FLOOR = config.get("control_parameters", {}).get("noise_floor", 0.5)
DECAY_RATE = config.get("control_parameters", {}).get("decay_rate", 0.2)
NORMALISATION = config.get("control_parameters", {}).get("normalisation_factor", 100.0)

DEVICE_MAC = "04:be:a4:cf:03:17"
CHARACTERISTIC_UUID = "00002a56-0000-1000-8000-00805f9b34fb"
VLC_HOST = "127.0.0.1"
VLC_PORT = 4212

previous_orientation = {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
smoothed_motion = 0.0

vlc_process = subprocess.Popen([
    "vlc", "--intf", "qt",
    "--extraintf", "rc",
    "--rc-host", "localhost:4212",
    "--no-video-title-show",
    "--playlist-autostart",
    "--play-and-exit",
    PLAYLIST
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ)

def clamp(val, min_val, max_val):
    return max(min_val, min(val, max_val))

def send_to_vlc(cmd):
    try:
        with socket.create_connection((VLC_HOST, VLC_PORT), timeout=1) as s:
            s.recv(1024)
            s.sendall((cmd + "\n").encode())
            s.recv(1024)
    except Exception as e:
        print(f"[VLC Error] {e}")

def handle_notification(sender, data):
    try:
        if len(data) != 6:
            print("Packet size mismatch")
            return

        pitch_i, yaw_i, roll_i = struct.unpack("<hhh", data)
        pitch, yaw, roll = pitch_i / 10.0, yaw_i / 10.0, roll_i / 10.0

        if yaw > 180:
            yaw -= 360

        global previous_orientation, smoothed_motion

        # orientation deltas
        dp = pitch - previous_orientation["pitch"]
        dy = yaw - previous_orientation["yaw"]
        dr = roll - previous_orientation["roll"]

        # updating previous values
        previous_orientation["pitch"] = pitch
        previous_orientation["yaw"] = yaw
        previous_orientation["roll"] = roll

        # motion energy (euclidian distance
        motion_energy = clamp(math.sqrt(dp**2 + dy**2 + dr**2), 0, 50)
        if motion_energy < NOISE_FLOOR:
            motion_energy = 0

        # decay smoothing
        #decay_rate = config.get("decay_rate", 0.2)
        #smoothed_motion = smoothed_motion * (1 - decay_rate) + motion_energy

        smoothed_motion = (1 - SMOOTHING) * smoothed_motion + SMOOTHING * motion_energy
        scaled_motion = clamp(smoothed_motion * SENSITIVITY / NORMALISATION, 0, 1)

        # 50 to MAX_VOL
        volume = int(50 + scaled_motion * (MAX_VOL - 50))
        send_to_vlc(f"volume {volume}")

        # tempo max value 1.0
        rate = clamp(1.0 - (1.0 - MIN_TEMPO) * (1.0 - scaled_motion), MIN_TEMPO, 1.0)
        send_to_vlc(f"rate {rate}")

        print(f"[IMU] P={pitch:.1f}, Y={yaw:.1f}, R={roll:.1f} \t Motion Energy={smoothed_motion:.2f}, Vol={volume}, Rate={rate}")

    except Exception as e:
        print(f"[Parse Error] {e}, Data: {data}")

from bleak import BleakClient, BleakError
import asyncio

def on_ble_disconnect(client):
    print("BLE device disconnected. Music paused.")
    send_to_vlc("pause")


async def wait_for_ble_connection(address, char_uuid, handler):
    print(f"Waiting for BLE device {address}...")
    while True:
        try:
            async with BleakClient(address, disconnected_callback=on_ble_disconnect) as client:
                # client.set_disconnected_callback(on_ble_disconnect)

                if client.is_connected:
                    print(f"Connected to {address}")
                    await client.start_notify(char_uuid, handler)

                    while True:
                        await asyncio.sleep(1)
        except BleakError as e:
            print(f"BLE not available yet: {e}")
            await asyncio.sleep(5)  # retry
        except asyncio.CancelledError:
            break

def wait_for_vlc_rc(host, port, timeout=10):
    """Wait up to `timeout` seconds for VLC to open the RC port."""
    print("Waiting for VLC RC interface to be ready...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                print("VLC RC interface is ready.")
                return True
        except (ConnectionRefusedError, socket.timeout):
            time.sleep(0.5)
    print("VLC RC interface not available after timeout.")
    return False


async def main():
    try:
        await wait_for_ble_connection(DEVICE_MAC, CHARACTERISTIC_UUID, handle_notification)
    finally:
        if vlc_process and vlc_process.poll() is None:
            print("Stopping VLC process...")
            vlc_process.terminate()
            try:
                vlc_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("VLC did not terminate in time. Killing.")
                vlc_process.kill()

if __name__ == "__main__":
    #print(f"Ready to play: {PLAYLIST}")
    print(f"Max Volume: {MAX_VOL}, Sensitivity: {SENSITIVITY}")
    '''
    #global vlc_process
    #vlc_process = subprocess.Popen([
        #"vlc", PLAYLIST,
        #"extraintf", "rc",
        #"--rc-host", f"{VLC_HOST}:{VLC_PORT}"
    ])

    if not wait_for_vlc_rc(VLC_HOST, VLC_PORT, timeout=10):
        print("Exiting: VLC did not become ready.")

    print(f"Started VLC playing {PLAYLIST} with PID {vlc_process.pid}")
    '''
    asyncio.run(main())
