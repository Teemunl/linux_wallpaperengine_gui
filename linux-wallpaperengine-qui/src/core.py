import shutil
import signal
import sys
from time import time

def initialize_app():
    # Initialize application settings or configurations
    pass

def handle_signal(signum, frame):
    # Handle termination signals
    sys.exit(0)

# Set up signal handling
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)