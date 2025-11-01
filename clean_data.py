import os
import re
from tqdm import tqdm  # type: ignore

SOURCE_DIR = "data/wiki_pages"
OUTPUT_DIR = "data/wiki_pages_cleaned"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_text(text):
    """Applies a series of regex cleanups to the raw wiki text."""
    # Remove ==Headers==
    text = re.sub(r"==+.*?==+", "", text)
    # Remove [[Category:...]] tags
    text = re.sub(r"\[\[Category:.*?\]\]", "", text)
    # Remove {{Templates}} - non-greedy, simple cases only
    text = re.sub(r"\{\{.*?\}\}", "", text, flags=re.DOTALL)
    # Remove remaining wikilink brackets
    text = re.sub(r"\[\[|\]\]", "", text)
    # Remove stray http links (we already processed the one we want)
    text = re.sub(r"http\S+", "", text)
    # Remove non-printable/non-ASCII characters
    text = re.sub(r"[^ -~\n]", "", text)
    # Collapse 3+ newlines down to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_and_save_file(filepath, relative_path):
    """
    Cleans a single file and saves it to the output directory.
    This function now also processes the ImageSourceURL and ImagePath tags.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        raw_text = f.read()

    image_link_tag = ""

    # 1. Look for our special ImageSourceURL tag (at the start of the file)
    url_match = re.search(r"^ImageSourceURL:\s*(http\S+)", raw_text, re.MULTILINE)
    path_match = re.search(r"^ImagePath:\s*(\S+)", raw_text, re.MULTILINE)

    if url_match:
        url = url_match.group(1)
        filename_with_query = url.split("/")[-1]
        filename = filename_with_query.split("?")[0]

        if filename:
            image_link_tag = f"\n\nImageLink: {filename}"

        raw_text = re.sub(
            r"^ImageSourceURL:\s*http\S+\n*", "", raw_text, count=1, flags=re.MULTILINE
        )
    elif path_match:
        path = path_match.group(1)
        filename = os.path.basename(path)

        if filename:
            image_link_tag = f"\n\nImageLink: {filename}"

        raw_text = re.sub(
            r"^ImagePath:\s*\S+\n*", "", raw_text, count=1, flags=re.MULTILINE
        )

    # 5. Clean the rest of the text
    cleaned = clean_text(raw_text)

    # 6. Append our new ImageLink tag to the *end* of the cleaned text
    # This ensures it's indexed along with the document.
    cleaned_text = cleaned + image_link_tag

    # 7. Save the cleaned file
    cleaned_path = os.path.join(OUTPUT_DIR, relative_path)
    os.makedirs(os.path.dirname(cleaned_path), exist_ok=True)

    with open(cleaned_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)


def walk_and_clean(source_dir):
    """Walks the source directory, cleans all .txt files, and saves to output."""
    file_list = []
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".txt"):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, source_dir)
                file_list.append((full_path, relative_path))

    # Use tqdm for a progress bar
    for full_path, relative_path in tqdm(file_list, desc="Cleaning files"):
        clean_and_save_file(full_path, relative_path)


if __name__ == "__main__":
    print(f"🧹 Starting cleanup from '{SOURCE_DIR}'...")
    walk_and_clean(SOURCE_DIR)
    print(f"✅ Cleaned files saved to '{OUTPUT_DIR}'")
