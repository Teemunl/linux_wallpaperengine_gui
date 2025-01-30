import subprocess
import psutil
import threading
from queue import Queue
import time
import os
import signal
import sys

def kill_wallpaper_processes():
    """Kill all running instances of linux-wallpaperengine and linux-wallpaper"""
    try:
        # Kill all instances of linux-wallpaperengine
        subprocess.run(
            "pkill -9 -f linux-wallpaperengine",
            shell=True,
            stderr=subprocess.DEVNULL,
            timeout=3
        )
        # Kill all instances of linux-wallpaper
        subprocess.run(
            "pkill -9 -f linux-wallpaper",
            shell=True,
            stderr=subprocess.DEVNULL,
            timeout=3
        )
        # Small delay to ensure processes are killed
        time.sleep(0.1)
    except Exception as e:
        print(f"Error killing wallpaper processes: {e}", file=sys.stderr)

def preexec_function():
    """Safely configure the child process"""
    try:
        # Create new process group
        os.setpgrp()
        # Ignore signals that might be sent to parent
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except Exception as e:
        print(f"Error in preexec_fn: {e}", file=sys.stderr)
        # Don't raise, as this would crash the child process
        pass

def run_wallpaper_engine(wallpaper_id, display_name):
    """Run wallpaper engine as a detached process"""
    #print(f"Running wallpaper engine with wallpaper_id={wallpaper_id}, display_name={display_name}")  # Debug logging
        
    try:
        # Ensure arguments are strings and properly formatted
        print(f"Running wallpaper engine with wallpaper_id={wallpaper_id}, display_name={display_name}")  # Debug logging
        command = [
            "linux-wallpaperengine",
            "--silent",
            "--screen-root",
            str(display_name),
            str(wallpaper_id)
        ]
        print(f"Executing command: {' '.join(command)}")  # Debug logging
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=preexec_function,
            start_new_session=True
        )
        return process
    except Exception as e:
        print(f"Error running wallpaper engine: {e}", file=sys.stderr)
        return None

class WallpaperManager:
    def __init__(self):
        # Kill any existing processes first
        kill_wallpaper_processes()
        self.processes = {}
        self.command_queue = Queue()
        self.running = True
        self.worker_thread = threading.Thread(target=self._process_commands, daemon=True)
        self.worker_thread.start()
        self._cleanup_old_processes()
        self.lock = threading.Lock()  # Add thread lock

    def _cleanup_old_processes(self):
        """Clean up any leftover processes from previous runs"""
        kill_wallpaper_processes()

    def _process_commands(self):
        while self.running:
            try:
                cmd = self.command_queue.get(timeout=1)
                if cmd is None:
                    break
                display_name, wallpaper_id = cmd
                self._change_wallpaper(display_name, wallpaper_id)
            except Exception:
                continue

    def _change_wallpaper(self, display_name, wallpaper_id):
        with self.lock:
            try:
                # Kill previous process for this display
                if display_name in self.processes:
                    try:
                        pgid = os.getpgid(self.processes[display_name])
                        os.killpg(pgid, signal.SIGTERM)
                        time.sleep(0.1)  # Give process time to terminate
                    except ProcessLookupError:
                        pass  # Process already terminated
                    except Exception as e:
                        print(f"Error killing previous process: {e}", file=sys.stderr)

                # Start new process
                process = run_wallpaper_engine(wallpaper_id, display_name)
                if process and process.poll() is None:  # Check if process started successfully
                    self.processes[display_name] = process.pid
                    
            except Exception as e:
                print(f"Error in _change_wallpaper: {e}", file=sys.stderr)

    def change_wallpaper(self, display_name, wallpaper_id):
        """Queue a wallpaper change request"""
        self.command_queue.put((display_name, wallpaper_id))

    def kill_all(self):
        """Kill all wallpaper processes"""
        self.running = False
        self.command_queue.put(None)  # Signal worker to stop
        
        # Kill process groups
        for pgid in self.processes.values():
            try:
                os.killpg(pgid, signal.SIGTERM)
                time.sleep(0.1)  # Give processes time to terminate gracefully
                try:
                    os.killpg(pgid, signal.SIGKILL)  # Force kill if still running
                except ProcessLookupError:
                    pass  # Process already terminated
            except Exception as e:
                print(f"Error killing process {pgid}: {e}")
        
        # Additional cleanup
        kill_wallpaper_processes()
        
        self.processes.clear()
