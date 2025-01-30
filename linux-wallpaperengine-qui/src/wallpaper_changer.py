import tkinter as tk
from gui import LoginApp
import core

class WallpaperChanger:
    def __init__(self, screen_root):
        self.screen_root = screen_root
        self.wallpaper_ids = []

    def fetch_wallpaper_ids(self):
        # This method will interact with the steam_fetcher to get wallpaper IDs
        pass

    def change_wallpaper(self, wallpaper_id):
        command = f"linux-wallpaperengine --silent --screen-root {self.screen_root} {wallpaper_id}"
        # Execute the command to change the wallpaper
        pass

    def update_wallpaper(self):
        # This method will fetch wallpaper IDs and change the wallpaper
        pass

if __name__ == "__main__":
    core.main()