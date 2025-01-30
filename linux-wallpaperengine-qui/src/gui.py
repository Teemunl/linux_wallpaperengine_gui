import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import requests
from io import BytesIO
import threading
import time
import subprocess
from utils.login_fetcher import fetch_steam_cookies
from utils.steam_fetcher import fetch_wallpaper_ids,WallpaperInfo
from utils.display_utils import get_displays
from utils.process_utils import kill_wallpaper_processes, run_wallpaper_engine, WallpaperManager
import asyncio
import concurrent.futures
from queue import Queue
import os
import json
import os.path
from tkinter import simpledialog  # Add this import at the top

class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self)  # Make canvas accessible
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def scroll_to_top(self):
        self.canvas.yview_moveto(0)

class LoginApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Linux Wallpaper Engine")
        self.cache_file = os.path.join(os.path.dirname(__file__), "wallpapers.txt")
        self.config_file = os.path.join(os.path.dirname(__file__), ".config")
        self.steam_username = self.load_config()
        
        # Kill any existing wallpaper processes first
        kill_wallpaper_processes()
        time.sleep(0.2)  # Give processes time to die
        
        # Initialize basic variables
        self.wallpapers = []
        self.selected_wallpapers = []
        self.is_auto_switching = False
        self.switch_interval = tk.IntVar(value=300)
        self.wallpaper_manager = WallpaperManager()
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.button_cooldown = {}
        self.change_queue = Queue()
        self.wallpaper_checkboxes = {}  # Add dictionary to store checkbox variables

        # Initialize GUI elements first
        self.setup_gui()
        
        # Start worker thread
        self.start_wallpaper_worker()
        
        # Try loading from cache silently
        if os.path.exists(self.cache_file):
            self.load_from_cache()
            self.display_wallpapers()  # No parameters needed anymore
            self.login_button.config(text="Refresh Wallpapers")

    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    for line in f:
                        if line.startswith('steam_username='):
                            return line.strip().split('=')[1]
            return self.prompt_username()
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.prompt_username()

    def prompt_username(self):
        """Prompt user for Steam username and save it"""
        username = simpledialog.askstring(
            "Steam Username Required", 
            "Enter your Steam username (from your profile URL):",
            parent=self.root
        )
        if username:
            self.save_config(username)
            return username
        return None

    def save_config(self, username):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                f.write(f"steam_username={username}")
        except Exception as e:
            print(f"Error saving config: {e}")

    def setup_gui(self):
        """Setup GUI elements"""
        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Top controls
        self.controls_frame = ttk.Frame(self.main_frame)
        self.controls_frame.pack(fill="x", pady=5)

        # Change button text based on cache status
        button_text = "Refresh Wallpapers" if os.path.exists(self.cache_file) else "Load Steam Wallpapers"
        self.login_button = ttk.Button(self.controls_frame, text=button_text, command=self.login)
        self.login_button.pack(side="left", padx=5)

        # Add display controls frame
        self.display_controls = ttk.Frame(self.controls_frame)
        self.display_controls.pack(side="left", padx=5)
        
        self.refresh_displays_btn = ttk.Button(
            self.display_controls,
            text="Refresh Displays",
            command=self.refresh_displays
        )
        self.refresh_displays_btn.pack(side="left", padx=5)

        # Add Select All button next to the refresh displays button
        self.select_all_btn = ttk.Button(
            self.display_controls,
            text="Select All Wallpapers",
            command=self.toggle_all_wallpapers
        )
        self.select_all_btn.pack(side="left", padx=5)

        # Auto-switch controls
        self.auto_switch_frame = ttk.LabelFrame(self.controls_frame, text="Auto Switch")
        self.auto_switch_frame.pack(side="right", padx=5)

        ttk.Label(self.auto_switch_frame, text="Interval (seconds):").pack(side="left")
        self.interval_entry = ttk.Entry(self.auto_switch_frame, textvariable=self.switch_interval, width=6)
        self.interval_entry.pack(side="left", padx=5)

        self.toggle_switch_btn = ttk.Button(self.auto_switch_frame, text="Start Auto Switch", command=self.toggle_auto_switch)
        self.toggle_switch_btn.pack(side="left", padx=5)

        # Add display selection frame between controls and wallpaper list
        self.display_frame = ttk.LabelFrame(self.main_frame, text="Displays")
        self.display_frame.pack(fill="x", pady=5)
        self.display_vars = {}  # Store display checkbuttons
        self.load_displays()

        # Scrollable wallpaper list
        self.wallpaper_frame = ScrollableFrame(self.main_frame)
        self.wallpaper_frame.pack(fill="both", expand=True, pady=10)

    def start_wallpaper_worker(self):
        """Start background worker for wallpaper changes"""
        def worker():
            while True:
                try:
                    wallpaper_id, display_name = self.change_queue.get()
                    if wallpaper_id is None:  # Shutdown signal
                        break
                    self.wallpaper_manager.change_wallpaper(display_name, wallpaper_id)
                except Exception as e:
                    print(f"Error in wallpaper worker: {e}")
        
        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def save_to_cache(self):
        """Save wallpapers to cache file"""
        try:
            cache_data = [{'id': w.id, 'preview_url': w.preview_url} for w in self.wallpapers]
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def load_from_cache(self):
        """Load wallpapers from cache file if it exists"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                self.wallpapers = [WallpaperInfo(id=w['id'], preview_url=w['preview_url']) 
                                 for w in cache_data]
                print(f"Loaded {len(self.wallpapers)} wallpapers from cache")
                return True
        except Exception as e:
            print(f"Error loading cache: {e}")
            self.wallpapers = []  # Reset wallpapers on error
        return False

    def load_preview_image(self, url):
        # Make image loading async
        def fetch_image():
            try:
                response = requests.get(url, timeout=5)  # Add timeout
                img = Image.open(BytesIO(response.content))
                img = img.resize((100, 100), Image.Resampling.LANCZOS)
                return img
            except Exception:
                return None

        return self.executor.submit(fetch_image)

    def toggle_wallpaper(self, wallpaper_info):
        """Toggle individual wallpaper selection"""
        if wallpaper_info in self.selected_wallpapers:
            self.selected_wallpapers.remove(wallpaper_info)
            self.wallpaper_checkboxes[wallpaper_info.id].set(False)
        else:
            self.selected_wallpapers.append(wallpaper_info)
            self.wallpaper_checkboxes[wallpaper_info.id].set(True)

    def toggle_auto_switch(self):
        self.is_auto_switching = not self.is_auto_switching
        if self.is_auto_switching:
            self.toggle_switch_btn.configure(text="Stop Auto Switch")
            # Start a new thread for auto-switching with immediate first change
            threading.Thread(target=self.auto_switch_wallpapers, args=(True,), daemon=True).start()
        else:
            self.toggle_switch_btn.configure(text="Start Auto Switch")

    def auto_switch_wallpapers(self, change_immediately=False):
        """Handle wallpaper auto-switching"""
        if not self.selected_wallpapers:
            print("No wallpapers selected for auto-switch")
            return

        current_index = 0
        selected_displays = [name for name, var in self.display_vars.items() if var.get()]
        
        if not selected_displays:
            print("No displays selected for auto-switch")
            return

        while self.is_auto_switching and self.selected_wallpapers:
            wallpaper = self.selected_wallpapers[current_index]
            print(f"Auto-switching to wallpaper {current_index + 1}/{len(self.selected_wallpapers)}: {wallpaper.id}")
            
            # Change wallpaper on all selected displays
            for display in selected_displays:
                self.wallpaper_manager.change_wallpaper(display, wallpaper.id)
            
            # If not immediate change, wait for interval
            if not change_immediately:
                time.sleep(self.switch_interval.get())
            change_immediately = False
            
            # Move to next wallpaper
            current_index = (current_index + 1) % len(self.selected_wallpapers)

    def login(self):
        """Modified login to use configured username"""
        try:
            if not self.steam_username:
                self.steam_username = self.prompt_username()
                if not self.steam_username:
                    messagebox.showerror("Error", "Steam username is required")
                    return

            self.login_button.config(state='disabled', text="Loading...")
            steam_cookies = fetch_steam_cookies()
            steam_url = f"https://steamcommunity.com/id/{self.steam_username}/myworkshopfiles/"
            print(f"Fetching wallpapers for user: {self.steam_username}")
            self.wallpapers = fetch_wallpaper_ids(steam_url, steam_cookies)
            self.save_to_cache()
            self.display_wallpapers()
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.login_button.config(state='normal', text="Refresh Wallpapers")

    def display_wallpapers(self):
        """Display wallpapers without any messages"""
        # Clear existing wallpapers
        for widget in self.wallpaper_frame.scrollable_frame.winfo_children():
            widget.destroy()

        if not self.wallpapers:
            return

        # Set minimum size for the window and canvas
        self.root.minsize(500, 400)
        self.wallpaper_frame.canvas.configure(width=480, height=400)
        
        # Create a progress bar
        progress = ttk.Progressbar(self.wallpaper_frame.scrollable_frame, 
                                 orient="horizontal", 
                                 length=200, 
                                 mode='determinate')
        progress.pack(pady=10)
        total = len(self.wallpapers)
        
        def load_images():
            futures = []
            for idx, wallpaper in enumerate(self.wallpapers):
                frame = ttk.Frame(self.wallpaper_frame.scrollable_frame)
                frame.pack(fill="x", pady=2, padx=5)
                
                # Checkbox with stored variable
                var = tk.BooleanVar()
                self.wallpaper_checkboxes[wallpaper.id] = var  # Store checkbox variable
                check = ttk.Checkbutton(frame, 
                                      command=lambda w=wallpaper: self.toggle_wallpaper(w),
                                      variable=var)
                check.pack(side="left")

                # Load preview image asynchronously
                future = self.load_preview_image(wallpaper.preview_url)
                futures.append((frame, future))

                # Wallpaper ID and display buttons
                ttk.Label(frame, text=f"ID: {wallpaper.id}").pack(side="left", padx=5)
                self.create_display_buttons(frame, wallpaper)

                # Update progress less frequently
                if idx % 5 == 0:  # Update every 5 items
                    progress['value'] = (idx + 1) / total * 100
                    self.root.update_idletasks()  # Use update_idletasks instead of update

            # Handle image loading results
            def check_futures():
                all_done = True
                for frame, future in futures:
                    if future.done():
                        if not hasattr(frame, 'image_loaded'):
                            img = future.result()
                            if img:
                                photo = ImageTk.PhotoImage(img)
                                label = ttk.Label(frame, image=photo)
                                label.image = photo
                                label.pack(side="left")
                            frame.image_loaded = True
                    else:
                        all_done = False
                
                if not all_done:
                    self.root.after(100, check_futures)
                else:
                    progress.destroy()
                    self.wallpaper_frame.scroll_to_top()

            self.root.after(100, check_futures)

        # Start loading images
        self.root.after(100, load_images)

    def create_display_buttons(self, frame, wallpaper):
        """Create display control buttons including All Displays button"""
        display_frame = ttk.Frame(frame)
        display_frame.pack(side="right", padx=5)
        
        # Add "All Displays" button with more prominence
        all_displays_btn = ttk.Button(
            display_frame,
            text="Set All Displays",  # Changed text to be more clear
            style='Accent.TButton',  # Optional: create a distinct style
            command=lambda w=wallpaper: self.set_wallpaper_all_displays(w)
        )
        all_displays_btn.pack(side="right", padx=5)  # Changed to right side
        
        # Add separator label
        ttk.Label(display_frame, text="|").pack(side="right", padx=5)
        
        # Individual display buttons section
        ttk.Label(display_frame, text="Single display:").pack(side="left", padx=5)
        for display_name in self.display_vars.keys():
            btn = ttk.Button(
                display_frame,
                text=display_name,
                command=lambda w=wallpaper, d=display_name: self.wallpaper_manager.change_wallpaper(d, w.id)
            )
            btn.pack(side="left", padx=2)

    def set_wallpaper_all_displays(self, wallpaper):
        """Set the wallpaper on all displays simultaneously"""
        selected_displays = self.get_selected_displays()
        if not selected_displays:
            selected_displays = list(self.display_vars.keys())
            
        # Send all display changes as a single command
        self.wallpaper_manager.change_wallpaper_all_displays(wallpaper.id, selected_displays)

    def handle_button_click(self, wallpaper_id, display_name, button):
        """Queue wallpaper change without blocking GUI"""
        current_time = time.time()
        button_id = f"{wallpaper_id}_{display_name}"
        print(f"Button clicked: {button_id}")
        if button_id in self.button_cooldown:
            if current_time - self.button_cooldown[button_id] < 1.0:
                return
                
        self.button_cooldown[button_id] = current_time
        self.change_queue.put((wallpaper_id, display_name))

    def refresh_displays(self):
        # Clear existing display frame
        for widget in self.display_frame.winfo_children():
            widget.destroy()
        self.display_vars.clear()
        
        # Reload displays
        self.load_displays()
        
        # Force update of wallpaper buttons if wallpapers are loaded
        if self.wallpapers:
            self.display_wallpapers()

    def load_displays(self):
        try:
            # Clear existing displays first
            for widget in self.display_frame.winfo_children():
                widget.destroy()
            
            displays = get_displays()
            if not displays:
                messagebox.showwarning("Warning", "No displays detected!")
                return

            for display in displays:
                var = tk.BooleanVar(value=display.primary)
                frame = ttk.Frame(self.display_frame)
                frame.pack(side="left", padx=5)
                
                cb = ttk.Checkbutton(
                    frame,
                    text=f"{display.name}\n({display.resolution})",
                    variable=var
                )
                cb.pack(side="top")
                self.display_vars[display.name] = var

            # Force GUI update
            self.display_frame.update()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to detect displays: {str(e)}")

    def get_selected_displays(self):
        return [name for name, var in self.display_vars.items() if var.get()]

    def change_wallpaper(self, wallpaper_id, display_name):
        """Non-blocking wallpaper change"""
        self.wallpaper_manager.change_wallpaper(display_name, wallpaper_id)

    def toggle_all_wallpapers(self):
        """Toggle selection state of all wallpapers"""
        all_selected = len(self.selected_wallpapers) == len(self.wallpapers)
        
        if all_selected:
            # Deselect all
            self.selected_wallpapers.clear()
            self.select_all_btn.config(text="Select All Wallpapers")
        else:
            # Select all - create a new list with all wallpapers
            self.selected_wallpapers = self.wallpapers.copy()
            self.select_all_btn.config(text="Deselect All")

        # Update all checkboxes to match current state
        for wallpaper in self.wallpapers:
            self.wallpaper_checkboxes[wallpaper.id].set(not all_selected)

    def __del__(self):
        """Cleanup when the application closes"""
        self.change_queue.put((None, None))  # Signal worker to stop
        self.wallpaper_manager.kill_all()
        # Kill all running processes
        for process in self.running_processes.values():
            try:
                os.killpg(os.getpgid(process.pid), 9)
            except:
                pass
        self.executor.shutdown(wait=False)

def main():
    root = tk.Tk()
    app = LoginApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
