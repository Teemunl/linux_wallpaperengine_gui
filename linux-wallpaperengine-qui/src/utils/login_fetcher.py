__all__ = ['fetch_steam_cookies']

import browser_cookie3 as browsercookie
from typing import Dict

def fetch_steam_cookies() -> Dict[str, str]:
    try:
        steam_cookies = {}
        print("Loading cookies for domain: .steamcommunity.com")
        
        # Try loading cookies from Firefox explicitly
        try:
            cookies = browsercookie.firefox(domain_name='steamcommunity.com')
            print("Loaded cookies from Firefox.")
            print("Cookies:", cookies)
        except Exception as e:
            print(f"Failed to load cookies from Firefox: {e}")
            cookies = None
        
        # If Firefox fails, try loading cookies from Chrome
        if cookies is None:
            try:
                cookies = browsercookie.chrome(domain_name='steamcommunity.com')
                print("Loaded cookies from Chrome.")
            except Exception as e:
                print(f"Failed to load cookies from Chrome: {e}")
                cookies = None
        
        if cookies is None:
            raise Exception("No cookies found. Ensure you are logged into Steam in your browser.")
        
        print("Cookies loaded successfully.")
        
        for cookie in cookies:
            steam_cookies[cookie.name] = cookie.value
            
        required_cookies = ['sessionid', 'steamLoginSecure']
        missing_cookies = [c for c in required_cookies if c not in steam_cookies]
        
        if missing_cookies:
            raise Exception(f"Missing required Steam cookies: {missing_cookies}. Please login to Steam in your browser first.")
            
        return steam_cookies
    except Exception as e:
        raise Exception(f"Failed to fetch Steam cookies: {str(e)}")

def main():
    cookies = fetch_steam_cookies()
    print("Found Steam cookies:", list(cookies.keys()))

if __name__ == "__main__":
    main()