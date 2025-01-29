import requests
from bs4 import BeautifulSoup

def fetch_wallpaper_ids(steam_url):
    response = requests.get(steam_url)
    if response.status_code != 200:
        raise Exception("Failed to fetch the webpage")

    soup = BeautifulSoup(response.content, 'html.parser')
    wallpaper_ids = []

    # Assuming wallpaper IDs are contained in specific HTML elements
    for item in soup.find_all('div', class_='workshopItem'):
        wallpaper_id = item['data-id']  # Adjust based on actual HTML structure
        wallpaper_ids.append(wallpaper_id)

    return wallpaper_ids

def main():
    steam_url = "https://steamcommunity.com/id/elessential/myworkshopfiles/?appid=431960&browsefilter=mysubscriptions"
    wallpaper_ids = fetch_wallpaper_ids(steam_url)
    print(wallpaper_ids)

if __name__ == "__main__":
    main()