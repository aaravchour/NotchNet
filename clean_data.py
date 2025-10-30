import os
import re
from tqdm import tqdm

SOURCE_DIR = "data/wiki_pages"
OUTPUT_DIR = "data/wiki_pages_cleaned"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_text(text):
    # Remove MediaWiki section markers and categories
    text = re.sub(r"==+.*?==+", "", text)
    text = re.sub(r"\[\[Category:.*?\]\]", "", text)
    text = re.sub(r"\{\{.*?\}\}", "", text)  # remove templates like {{Infobox}}
    text = re.sub(r"\[\[|\]\]", "", text)  # remove brackets
    text = re.sub(r"http\S+", "", text)  # remove links
    text = re.sub(r"[^ -~\n]", "", text)  # remove non-ASCII except newlines
    text = re.sub(r"\n{3,}", "\n\n", text)  # reduce multiple blank lines
    return text.strip()


def clean_and_save_file(filepath, relative_path):
    with open(filepath, "r", encoding="utf-8") as f:
        raw_text = f.read()

    cleaned = clean_text(raw_text)

    # Create subfolder if necessary
    cleaned_path = os.path.join(OUTPUT_DIR, relative_path)
    os.makedirs(os.path.dirname(cleaned_path), exist_ok=True)

    with open(cleaned_path, "w", encoding="utf-8") as f:
        f.write(cleaned)


def walk_and_clean(source_dir):
    for root, _, files in os.walk(source_dir):
        for file in tqdm(files, desc="Cleaning files"):
            if file.endswith(".txt"):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, source_dir)
                clean_and_save_file(full_path, relative_path)


if __name__ == "__main__":
    walk_and_clean(SOURCE_DIR)
    print(f"✅ Cleaned files saved to '{OUTPUT_DIR}'")
