import requests
from bs4 import BeautifulSoup
from typing import Dict, List, NamedTuple
import re

class WallpaperInfo(NamedTuple):
    id: str
    preview_url: str
#ef fetch_wallpaper_ids(steam_url: str, cookies: Dict[str, str]) -> List[WallpaperInfo]:
def fetch_wallpaper_ids(steam_url: str, cookies: str) -> List[WallpaperInfo]:
    all_wallpapers = []
    page = 1
    base_url = steam_url.split('?')[0]
    
    while True:
        current_url = f"{base_url}?appid=431960&browsefilter=mysubscriptions&p={page}"
        response = requests.get(current_url, cookies=cookies)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch wallpapers: HTTP {response.status_code}")

        soup = BeautifulSoup(response.content, 'html.parser')
        subscriptions = soup.find_all('div', class_='workshopItemSubscription')
        if not subscriptions:
            break
            
        for sub in subscriptions:
            sub_id = sub.get('id', '')
            if sub_id.startswith('Subscription'):
                wallpaper_id = sub_id.replace('Subscription', '')
                if wallpaper_id.isdigit():
                    preview_img = sub.find('img', class_='backgroundImg')
                    preview_url = preview_img.get('src') if preview_img else ''
                    all_wallpapers.append(WallpaperInfo(id=wallpaper_id, preview_url=preview_url))
        page += 1

    if not all_wallpapers:
        raise Exception("No wallpapers found. Make sure you're logged in and have subscribed wallpapers.")

    return all_wallpapers

def main():
    """Remove hardcoded example"""
    print("Please run through the GUI application")

if __name__ == "__main__":
    main()