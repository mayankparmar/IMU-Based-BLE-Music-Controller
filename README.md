# BLE Motion-Controlled Music

This project demonstrates a motion-controlled music player using a BLE-enabled IMU device (Arduino Nano 33 BLE Sense or similar) and a Python script that reads orientation data to dynamically adjust VLC media player's volume and playback rate.

## Overview

The BLE peripheral broadcasts pitch, yaw, and roll data using sensor fusion. A Python client running on a computer listens to this data, calculates "motion energy", and uses it to control:

- **Volume** (based on movement intensity)
- **Playback tempo** (based on scaled movement)
- **Auto-pause** when BLE device disconnects

---

## Features

- BLE notification using [Bleak](https://github.com/hbldh/bleak)
- VLC control via RC socket interface
- YAML-based configurable settings
- Noise floor filtering and smoothing
- Auto-pause on BLE disconnection
- Cleanly logs pitch, yaw, roll, motion energy, volume, and tempo

---

# Python Script Setup

## Dependencies

Python 3 is required.

Python packages:
- `bleak`
- `pyyaml`

System software:
- [VLC media player](https://www.videolan.org/vlc/) (must be installed and accessible via command line)

## Setting up (automatic)

- Navigate to Python script folder and make the bash script, `setup.sh` executible: `sudo chmod +x setup.sh`
- Run the bash script: `./setup.sh`

## Setting up (manually)

```bash
# Clone the repository
git clone https://github.com/yourusername/ble-music-controller.git
cd ble-music-controller

# Ensure Python 3 is installed
python3 --version

# Create virtual environment
python3 -m venv venv

# Activate the environment
source venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install bleak pyyaml

# Run main script
python3 main.py
```

---

# Arduino Setup

## Dependencies

- `Sensor Fusion` by aster94
- `Arduino_BMI270_BMM150` by Arduino
- `ArduinoBLE` by Arduino

## Setup

Flash the provided Arduino code to the Nano 33 BLE Sense.

---

# Configuration

```yaml
playlist: "playlist.xspf"

control_parameters:
  normalisation_factor: 100.0
  sensitivity: 3.0
  smoothing_factor: 0.1
  decay_rate: 0.2
  noise_floor: 0.5

output_values:
  max_volume: 220
  min_tempo: 0.1
```

- ### `smoothing_factor`

  **Purpose**:  
  This controls the weight given to recent motion energy versus past values. It’s used in exponential smoothing:

  **Impact of Values**:
  - **Higher value** (closer to 1): Reacts faster to sudden motion; more jittery output.
  - **Lower value** (closer to 0): More stable output; slower to respond to new movements.


- ### `decay_rate`

  **Purpose**:  
  Controls how quickly the system "forgets" previous motion energy in the decay-based smoothing approach (if used instead of `smoothing_factor`). This is helpful if you want motion energy to fade when motion stops.

  **Impact of Values**:
  - **Higher value**: Past motion energy decays quickly; system resets quickly.
  - **Lower value**: Motion energy lingers; system takes longer to settle.

  > Note: The current implementation uses `smoothing_factor`. `decay_rate` is ignored unless explicitly used in the script instead.


- ### `noise_floor`

  **Purpose**:  
  Eliminates tiny, meaningless orientation changes (e.g., sensor jitter or hand tremors) by setting a minimum threshold for motion energy.

  **Impact of Values**:
  - **Higher value**: Filters out more small movements; system is less sensitive to fine motion.
  - **Lower value**: Captures smaller movements; may react to unintentional noise.


- ### `sensitivity`

  **Purpose**:  
  Controls how much the motion energy influences the output. It's a gain multiplier before scaling.

  **Impact of Values**:
  - **Higher value**: Small movements result in larger output changes (volume/tempo); more dramatic response.
  - **Lower value**: Requires bigger movements to trigger a response; system feels more "numb".


- ### `normalisation_factor`

  **Purpose**:  
  Defines the maximum expected motion energy for scaling between 0 and 1.

  **Impact of Values**:
  - **Higher value**: Narrows the effective output range; motion needs to be more intense to reach full output.
  - **Lower value**: Expands sensitivity range; less motion can achieve full volume or tempo.
  
