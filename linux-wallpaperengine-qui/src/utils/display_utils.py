import subprocess
import shutil
from typing import List, NamedTuple

class DisplayInfo(NamedTuple):
    name: str
    resolution: str
    primary: bool

def check_xrandr_installed():
    if not shutil.which('xrandr'):
        raise Exception("xrandr is not installed. Please install xrandr using your system's package manager (e.g., 'sudo apt install x11-xserver-utils' for Debian/Ubuntu)")

def get_displays() -> List[DisplayInfo]:
    try:
        check_xrandr_installed()
        output = subprocess.check_output(['xrandr', '--current']).decode()
        displays = []
        
        for line in output.split('\n'):
            if ' connected ' in line:
                parts = line.split()
                name = parts[0]
                primary = 'primary' in line
                resolution = next((p for p in parts if 'x' in p), 'unknown')
                displays.append(DisplayInfo(name=name, resolution=resolution, primary=primary))
        
        return displays
    except Exception as e:
        raise Exception(f"Failed to get displays: {str(e)}")
