import requests
import urllib.parse
import re

def search_fandom_wiki(mod_name):
    """
    Searches DuckDuckGo Lite to find a Fandom wiki for the given mod name.
    """
    search_query = urllib.parse.quote(f"{mod_name} minecraft wiki site:fandom.com")
    url = f"https://lite.duckduckgo.com/lite/?q={search_query}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            # Look for fandom.com subdomains
            matches = re.findall(r'https?://([a-zA-Z0-9-]+)\.fandom\.com/', resp.text)
            for m in matches:
                if m not in ["www", "community", "images", "static", "explore"]:
                    candidate_url = f"https://{m}.fandom.com/api.php"
                    if verify_wiki_api(candidate_url):
                        return candidate_url
    except Exception as e:
        print(f"⚠️ Search error for {mod_name}: {e}")
    
    return None

def verify_wiki_api(api_url):
    """
    Verifies if a Fandom API URL is valid and functional.
    """
    try:
        params = {"action": "query", "meta": "siteinfo", "format": "json"}
        resp = requests.get(api_url, params=params, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            if "query" in data and "general" in data["query"]:
                return True
    except:
        pass
    return False

def find_wiki_for_mod(mod_name):
    """
    Attempts to find a Fandom wiki for a given mod name using heuristics and internet search.
    """
    # 1. Clean name for direct subdomain guess
    clean_name = mod_name.lower().replace(" ", "-").replace("'", "")
    
    # 2. Direct Guess: Try the most likely subdomain
    candidate_url = f"https://{clean_name}.fandom.com/api.php"
    if verify_wiki_api(candidate_url):
        return candidate_url
    
    # 3. Internet Search: Use DuckDuckGo to find the correct wiki
    return search_fandom_wiki(mod_name)

def filter_mods(mod_list):
    """
    Returns the original list as requested to 'discover EVERY MOD'.
    """
    return mod_list
