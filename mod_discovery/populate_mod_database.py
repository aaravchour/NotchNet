import requests
import time
import argparse
from tqdm import tqdm
from sqlalchemy.orm import Session
from mod_discovery.database import init_db, get_db, Mod
from mod_discovery.mod_discovery import fetch_modrinth_mods, get_mod_wiki_url, MODRINTH_API_URL

def fetch_bulk_projects(project_ids):
    """
    Fetches full project details for a list of project IDs using Modrinth's bulk endpoint.
    """
    # Modrinth allows [] syntax or comma separated? Docs say list of IDs.
    # Usually passed as ?ids=["id1","id2"]
    import json
    ids_json = json.dumps(project_ids)
    url = f"{MODRINTH_API_URL}/projects"
    params = {"ids": ids_json}
    headers = {"User-Agent": "NotchNet/1.0 (internal-dev)"}
    
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        if resp.status_code == 429:
            print("⏳ Rate limited on bulk fetch. Sleeping 10s...")
            time.sleep(10)
            return fetch_bulk_projects(project_ids)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"❌ Bulk fetch error: {e}")
        return []

def populate_database(limit=None):
    init_db()
    db = next(get_db())
    
    offset = 0
    batch_size = 100 # Modrinth max limit for search is 100 usually
    total_processed = 0
    
    print("🚀 Starting Modrinth discovery...")
    
    while True:
        if limit and total_processed >= limit:
            break
            
        print(f"🔍 Fetching search results offset={offset}...")
        results = fetch_modrinth_mods(limit=batch_size, offset=offset)
        hits = results.get("hits", [])
        total_hits = results.get("total_hits", 0)
        
        if not hits:
            print("✅ No more results.")
            break
            
        # Extract IDs for bulk fetch
        project_ids = [hit["project_id"] for hit in hits]
        
        # Bulk fetch details
        print(f"📦 Bulk fetching details for {len(project_ids)} mods...")
        full_details = fetch_bulk_projects(project_ids)
        
        # Create a map for quick lookup
        details_map = {p["id"]: p for p in full_details}
        
        count_added = 0
        for hit in hits:
            p_id = hit["project_id"]
            slug = hit["slug"]
            
            # Get full detail if available
            detail = details_map.get(p_id, {})
            
            # Extract info using improved discovery logic
            wiki_url = get_mod_wiki_url(detail)
            source_url = detail.get("source_url")
            issues_url = detail.get("issues_url")
            discord_url = detail.get("discord_url")
                
            # Create/Update Mod object
                
            # Create/Update Mod object
            # Check existence
            existing = db.query(Mod).filter_by(slug=slug).first()
            if not existing:
                new_mod = Mod(
                    name=hit["title"],
                    slug=slug,
                    source='modrinth',
                    wiki_url=wiki_url,
                    external_url=source_url or issues_url or f"https://modrinth.com/mod/{slug}",
                    description=hit["description"],
                    downloads=hit["downloads"]
                )
                db.add(new_mod)
                count_added += 1
            else:
                # Update fields if needed
                if wiki_url and not existing.wiki_url:
                    existing.wiki_url = wiki_url
        
        db.commit()
        print(f"💾 Saved {count_added} new mods to DB. (Total processed: {total_processed + len(hits)})")
        
        total_processed += len(hits)
        offset += batch_size
        
        if total_processed >= total_hits:
            print("✅ Reached end of Modrinth results.")
            break
            
        # Be nice to API
        time.sleep(1)

    print(f"🎉 Done! Total mods processed: {total_processed}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit number of mods to process")
    args = parser.parse_args()
    
    populate_database(limit=args.limit)
