import os
import re
import requests
from time import sleep
import concurrent.futures
from tqdm import tqdm  # type: ignore
import config

API_URL = config.WIKI_API_URL_DEFAULT
DATA_DIR = config.DATA_DIR_RAW
MAX_WORKERS = config.MAX_WORKERS


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)


def fetch_category_members(api_url, category, cmcontinue=None):
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": "50",
        "format": "json",
    }
    if cmcontinue:
        params["cmcontinue"] = cmcontinue

    for _ in range(3):
        try:
            resp = requests.get(api_url, params=params)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Network error: {e}. Retrying in 3s...")
            sleep(3)
    return {}


def fetch_page_content(api_url, title):
    """
    Fetches the text extract AND the list of images for a page.
    Returns: (text, images)
    """
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts|images",
        "explaintext": True,
        "titles": title,
    }

    try:
        resp = requests.get(api_url, params=params)
        resp.raise_for_status()
        data = resp.json()
        pages = data.get("query", {}).get("pages", {})

        for page_id, page in pages.items():
            text = page.get("extract", "")
            images = page.get("images", [])
            return text, images
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch {title}: {e}")

    return "", []


def save_page_data(category, title, text, image_path):
    """
    Saves the page data. If an image_path is provided, it's written
    at the top of the file for the cleaning script to use.
    """
    safe_title = title.replace("/", "_")
    folder = os.path.join(DATA_DIR, category)
    ensure_dir(folder)
    path = os.path.join(folder, f"{safe_title}.txt")

    try:
        with open(path, "w", encoding="utf-8") as f:
            if image_path:
                f.write(f"ImagePath: {image_path}\n\n")
            f.write(text)
    except Exception as e:
        print(f"❌ Failed to save {title}: {e}")


def download_image(url, folder, filename):
    """Downloads an image from a URL and saves it to a folder."""
    ensure_dir(folder)
    path = os.path.join(folder, filename)

    # Avoid re-downloading
    if os.path.exists(path):
        return path

    try:
        resp = requests.get(url)
        resp.raise_for_status()
        with open(path, "wb") as f:
            f.write(resp.content)
        return path
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to download image {url}: {e}")
    return None


def discover_pages_to_fetch(api_url, category, recipe_categories, visited, work_items):
    """
    PHASE 1: Recursively scans categories and adds work items to a list.
    A work item is a tuple: (title, category, is_recipe_category)
    """
    if category in visited:
        return
    visited.add(category)
    print(f"🔍 Discovering pages in: {category}")

    cmcontinue = None
    is_recipe_category = category in recipe_categories

    while True:
        data = fetch_category_members(api_url, category, cmcontinue)
        members = data.get("query", {}).get("categorymembers", [])
        if not members:
            break

        for member in members:
            title = member["title"]
            if title.startswith("Category:"):
                subcat = title.replace("Category:", "")
                discover_pages_to_fetch(api_url, subcat, recipe_categories, visited, work_items)
            else:
                work_items.append((title, category, is_recipe_category))

        if "continue" in data:
            cmcontinue = data["continue"]["cmcontinue"]
        else:
            break


def process_page_work_item(api_url, work_item):
    """
    PHASE 2: The actual work done by each thread.
    Fetches one page and saves it.
    """
    title, category, is_recipe_category = work_item

    text, images = fetch_page_content(api_url, title)

    image_path_to_save = None
    if is_recipe_category and images:
        for image in images:
            image_title = image.get("title", "")
            if "crafting" in image_title.lower() or "recipe" in image_title.lower():
                # Found a recipe image, now get its URL
                image_info_params = {
                    "action": "query",
                    "format": "json",
                    "prop": "imageinfo",
                    "titles": image_title,
                    "iiprop": "url"
                }
                try:
                    info_resp = requests.get(api_url, params=image_info_params)
                    info_resp.raise_for_status()
                    info_data = info_resp.json()
                    info_pages = info_data.get("query", {}).get("pages", {})
                    for _, page_info in info_pages.items():
                        image_url = page_info.get("imageinfo", [{}])[0].get("url")
                        if image_url:
                            image_filename = image_title.replace("File:", "")
                            image_folder = "static/images/recipes"
                            image_path_to_save = download_image(image_url, image_folder, image_filename)
                            break # Stop after finding the first recipe image
                except requests.exceptions.RequestException as e:
                    print(f"❌ Failed to fetch image info for {image_title}: {e}")
            if image_path_to_save:
                break

    save_page_data(category, title, text, image_path_to_save)
    return title


def fetch_wiki(api_url, categories, recipe_categories=None):
    if recipe_categories is None:
        recipe_categories = set()

    print(f"--- Phase 1: Discovering all pages to fetch from {api_url} ---")
    visited = set()
    work_items = []

    for cat in categories:
        discover_pages_to_fetch(api_url, cat, recipe_categories, visited, work_items)

    print(f"\n✅ Discovered {len(work_items)} total pages.")

    print(f"\n--- Phase 2: Downloading pages with {MAX_WORKERS} workers ---")

    # Partial application to pass api_url to the worker function
    from functools import partial
    worker_func = partial(process_page_work_item, api_url)

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(worker_func, item) for item in work_items]

        for future in tqdm(
            concurrent.futures.as_completed(futures), total=len(work_items)
        ):
            try:
                future.result()
            except Exception as e:
                tqdm.write(f"❌ A task failed: {e}")

    print("\n🎉 All pages downloaded successfully!")


if __name__ == "__main__":
    # All categories to download (Default vanilla)
    default_categories = {
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

    default_recipe_categories = {"Crafting", "Brewing", "Smelting", "Smithing"}
    
    fetch_wiki(API_URL, default_categories, default_recipe_categories)