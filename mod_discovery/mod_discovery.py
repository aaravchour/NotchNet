import requests
import urllib.parse
import re
import time

MODRINTH_API_URL = "https://api.modrinth.com/v2"

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
                if m not in ["www", "community", "images", "static", "explore", "minecraft"]:
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

def find_wiki_fallback(mod_name):
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

def fetch_modrinth_mods(query="", limit=100, offset=0, sort="downloads"):
    """
    Fetches mods from Modrinth API.
    """
    url = f"{MODRINTH_API_URL}/search"
    params = {
        "query": query,
        "limit": limit,
        "offset": offset,
        "index": sort,
        "facets": '[["project_type:mod"]]'
    }
    headers = {
        "User-Agent": "NotchNet/1.0 (internal-dev)" 
    }
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        if resp.status_code == 429:
            print("⏳ Rate limited. Sleeping for 5 seconds...")
            time.sleep(5)
            return fetch_modrinth_mods(query, limit, offset, sort)
            
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"❌ Modrinth API error: {e}")
        return {"hits": [], "total_hits": 0}

def check_url_exists(url):
    """
    Checks if a URL exists and returns 200 OK.
    """
    headers = {
        "User-Agent": "NotchNet/1.0 (internal-dev)"
    }
    try:
        # Use HEAD first for speed, fallback to GET if 405/403
        resp = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
        if resp.status_code == 200:
            return True
        if resp.status_code == 405: # Method Not Allowed often happens with HEAD
             resp = requests.get(url, headers=headers, stream=True, timeout=5)
             return resp.status_code == 200
    except:
        pass
    return False

def get_mod_wiki_url(mod_data):
    """
    Extracts wiki URL from Modrinth data or attempts discovery.
    """
    # 1. Check explicit wiki_url in API response
    wiki_url = mod_data.get("wiki_url")
    if wiki_url:
        return wiki_url
        
    # 2. Heuristic: Check Source/Issues URL for Wiki
    source_url = mod_data.get("source_url")
    if source_url and "github.com" in source_url:
        # Construct GitHub Wiki URL
        # GitHub wikis are usually at repo_url/wiki
        candidate = source_url.rstrip("/") + "/wiki"
        if check_url_exists(candidate):
            return candidate
            
    # 3. Fallback: Search Fandom/Web (Optional - can be slow)
    # We only do this if we really, really want to find a wiki.
    # To avoid rate limiting and massive slowdowns on bulk import, 
    # we might skip this step or make it very selective.
    # For now, let's skip it to prioritize speed of importation.
    # return find_wiki_fallback(mod_data.get("title", ""))
    
    return None

def fetch_full_project_details(slug):
    """
    Fetches full project details to get the official wiki link.
    """
    url = f"{MODRINTH_API_URL}/project/{slug}"
    headers = {"User-Agent": "NotchNet/1.0 (internal-dev)"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 429:
             time.sleep(5)
             return fetch_full_project_details(slug)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None
