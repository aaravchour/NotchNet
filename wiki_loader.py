import os
import requests
from time import sleep

API_URL = "https://minecraft.fandom.com/api.php"
DATA_DIR = "data/wiki_pages"


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def fetch_category_members(category, cmcontinue=None):
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": "50",
        "format": "json",
    }
    if cmcontinue:
        params["cmcontinue"] = cmcontinue

    resp = requests.get(API_URL, params=params)
    resp.raise_for_status()
    return resp.json()


def fetch_page_content(title):
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "explaintext": True,
        "titles": title,
    }
    resp = requests.get(API_URL, params=params)
    resp.raise_for_status()
    data = resp.json()
    pages = data.get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        if "extract" in page:
            return page["extract"]
    return ""


def save_page_text(category, title, text):
    safe_title = title.replace("/", "_")
    folder = os.path.join(DATA_DIR, category)
    ensure_dir(folder)
    path = os.path.join(folder, f"{safe_title}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def download_category(category, visited=None):
    if visited is None:
        visited = set()
    if category in visited:
        return
    visited.add(category)

    print(f"🔽 Downloading pages in category: {category}")
    cmcontinue = None
    total = 0

    while True:
        data = fetch_category_members(category, cmcontinue)
        members = data.get("query", {}).get("categorymembers", [])

        for member in members:
            title = member["title"]
            if title.startswith("Category:"):
                subcat = title.replace("Category:", "")
                download_category(subcat, visited)  # Recursive call for subcategories
            else:
                print(f"Fetching: {title}")
                text = fetch_page_content(title)
                save_page_text(category, title, text)
                total += 1
                sleep(0.5)  # polite delay

        if "continue" in data:
            cmcontinue = data["continue"]["cmcontinue"]
        else:
            break

    print(f"✅ Finished downloading {total} pages for category: {category}")


if __name__ == "__main__":
    categories = {
        "Trading",
        "Brewing",
        "Enchanting",
        "Mobs",
        "Blocks",
        "Items",
        "Crafting",
        "Redstone",
        "Biomes",
        "Structures",
        "Commands",
        "Effects",
        "Smelting",
        "Smithing",
        "History",
        "Tutorials",
    }

    visited = set()
    for cat in categories:
        download_category(cat, visited)
