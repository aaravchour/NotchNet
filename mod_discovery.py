import requests
import urllib.parse

def find_wiki_for_mod(mod_name):
    """
    Attempts to find a Fandom wiki for a given mod name.
    """
    # Simple heuristic: Mod name + " wiki" search on Fandom or Google
    # For now, we'll try to guess the wiki URL directly or use a search API if available.
    # Since we don't have a Google Search API key readily available in this context,
    # we'll use a direct heuristics approach and a 'known wikis' map.

    # 1. Clean name
    clean_name = mod_name.lower().replace(" ", "-").replace("'", "")
    
    # 2. Known mappings (The "Hardcoded" list for top mods)
    known_wikis = {
        "rlcraft": "https://rlcraft.fandom.com/api.php",
        "create": "https://create.fandom.com/api.php",
        "botania": "https://botania.fandom.com/api.php",
        "feed-the-beast": "https://ftb.fandom.com/api.php",
        "ftb": "https://ftb.fandom.com/api.php",
        "sky-factory": "https://skyfactory-4.fandom.com/api.php",
        "twilight-forest": "https://twilightforest.fandom.com/api.php",
        "aether": "https://aether.fandom.com/api.php",
        "ice-and-fire": "https://ice-and-fire-mod.fandom.com/api.php",
    }
    
    if clean_name in known_wikis:
        return known_wikis[clean_name]

    # 3. Dynamic Guess: Try to hit the API of a likely wiki URL
    # e.g., https://<modname>.fandom.com/api.php
    candidate_url = f"https://{clean_name}.fandom.com/api.php"
    
    try:
        # Check if it exists with a simple query
        params = {"action": "query", "meta": "siteinfo", "format": "json"}
        resp = requests.get(candidate_url, params=params, timeout=3)
        if resp.status_code == 200:
             # Basic check if it returns valid JSON and has site info
             data = resp.json()
             if "query" in data and "general" in data["query"]:
                 return candidate_url
    except:
        pass

    return None

def filter_mods(mod_list):
    """
    Filters out technical/library mods that usually don't have gameplay wikis.
    """
    ignore_list = {
        "minecraft", "fabric-api", "fabric-loader", "java", "sodium", "lithium", 
        "phosphor", "iris", "cloth-config", "architectury", "jei", "rei", "emi",
        "modmenu", "yet-another-config-lib", "indium", "ferritecore"
    }
    
    return [m for m in mod_list if m.lower().replace(" ", "-") not in ignore_list]
