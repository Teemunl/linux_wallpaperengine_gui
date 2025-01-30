import shutil
import signal
import sys
from time import time
import tkinter as tk
from gui import LoginApp

def initialize_app():
    # Initialize application settings or configurations
    pass

def handle_signal(signum, frame):
    # Handle termination signals
    sys.exit(0)

def main():
    initialize_app()
    root = tk.Tk()
    app = LoginApp(root)
    root.mainloop()

# Set up signal handling
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)
