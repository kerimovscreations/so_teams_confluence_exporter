#!/usr/bin/env python3
import json
from datetime import datetime
import re
from pathlib import Path

# Configuration
JSON_FILE = "stackoverflow_articles.json"
OUTPUT_FILE = "stackoverflow_articles.md"
IMAGE_FOLDER = "images"

# Create images folder if it doesn't exist
Path(IMAGE_FOLDER).mkdir(exist_ok=True)

def format_date(timestamp):
    """Convert Unix timestamp to readable date."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def replace_image_urls(text):
    """Replace remote image URLs with local image paths."""
    if not text:
        return text

    # Replace URLs in markdown image syntax: ![alt text](url)
    text = re.sub(
        r'!\[(.*?)\]\(https://pashabank\.stackenterprise\.co/images/a/([^\s\)]+)\)',
        r'![\1](images/\2)',
        text
    )

    # Replace URLs in HTML image tags: <img src="url" ...>
    text = re.sub(
        r'<img\s+([^>]*)src="https://pashabank\.stackenterprise\.co/images/a/([^\s"]+)"([^>]*)>',
        r'<img \1src="images/\2"\3>',
        text
    )

    return text

def write_to_markdown(articles_data):
    """Write all articles to a Markdown file with proper styling."""
    print(f"Writing {len(articles_data)} articles to {OUTPUT_FILE}...")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Stack Overflow Teams Articles Export\n\n")
        f.write(f"*Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

        for article in articles_data:
            if not article:  # Skip empty entries
                continue

            # Write article title
            if 'title' in article:
                f.write(f"## {article['title']}\n\n")
            else:
                continue  # Skip articles without title

            # Article metadata
            if 'tags' in article:
                tags = ", ".join(article['tags']) if article['tags'] else "No tags"
                f.write(f"**Tags**: {tags}  \n")

            if 'owner' in article and 'display_name' in article['owner']:
                f.write(f"**Author**: {article['owner']['display_name']}  \n")

            if 'creation_date' in article:
                f.write(f"**Created**: {format_date(article['creation_date'])}  \n")

            if 'last_edit_date' in article:
                f.write(f"**Last Edited**: {format_date(article['last_edit_date'])}  \n")

            if 'view_count' in article:
                f.write(f"**Views**: {article['view_count']}  \n")

            f.write("\n")  # Add an extra line after metadata

            # Article body
            if 'body_markdown' in article:
                body = article['body_markdown']
            elif 'body' in article:
                body = article['body']
            else:
                body = ""

            # Replace image URLs with local paths
            body = replace_image_urls(body)

            f.write(f"{body}\n\n")

            # Article comments
            if 'comments' in article and article['comments']:
                f.write(f"### Comments on Article ({len(article['comments'])})\n\n")
                for comment in article['comments']:
                    if not comment:  # Skip empty comments
                        continue

                    f.write("> ")

                    # Comment metadata and content
                    if 'owner' in comment and 'display_name' in comment['owner']:
                        f.write(f"**{comment['owner']['display_name']}**")
                    else:
                        f.write("**Unknown User**")

                    if 'creation_date' in comment:
                        f.write(f" ({format_date(comment['creation_date'])}): ")
                    else:
                        f.write(": ")

                    # Comment content - prefer body_markdown when available
                    if 'body_markdown' in comment:
                        f.write(f"{comment['body_markdown']}\n")
                    elif 'body' in comment:
                        f.write(f"{comment['body']}\n")

                    f.write("\n\n")

            f.write("---\n\n")  # Add separator between articles

def extract_image_urls(markdown_text):
    """Extract image URLs from markdown text that start with https://pashabank.stackenterprise.co/images."""
    if not markdown_text:
        return []

    # This regex pattern looks for markdown image syntax: ![alt text](url)
    # and also HTML image tags: <img src="url" ...>
    markdown_pattern = r'!\[.*?\]\((https://pashabank\.stackenterprise\.co/images/[^\s\)]+)\)'
    html_pattern = r'<img\s+[^>]*src="(https://pashabank\.stackenterprise\.co/images/[^\s"]+)"[^>]*>'

    markdown_urls = re.findall(markdown_pattern, markdown_text)
    html_urls = re.findall(html_pattern, markdown_text)

    return markdown_urls + html_urls

def process_articles_file():
    """Process the articles JSON file and extract all images from Pashabank URLs."""
    # Read the JSON file
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    print(f"Processing {len(articles)} articles...")

    # Track all image URLs
    all_urls = []

    # Process each article
    for article in articles:
        # Extract images from article body
        if 'body_markdown' in article:
            urls = extract_image_urls(article['body_markdown'])
            all_urls.extend(urls)
        elif 'body' in article:
            urls = extract_image_urls(article['body'])
            all_urls.extend(urls)

    # Remove duplicates
    unique_urls = list(set(all_urls))
    print(f"Found {len(unique_urls)} unique image URLs from pashabank.stackenterprise.co/images")

    # Store the image urls in a text file
    with open("image_urls.txt", 'w', encoding='utf-8') as f:
        for url in unique_urls:
            f.write(url + "\n")
    print(f"Image URLs saved to 'image_urls.txt'")

def main():
    """Main function to read JSON and generate Markdown."""
    try:
        # Read the JSON file
        print(f"Reading articles from {JSON_FILE}...")

        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            articles_data = json.load(f)

        # Generate the Markdown file
        write_to_markdown(articles_data)

        print(f"Markdown file created successfully at {OUTPUT_FILE}!")

    except Exception as e:
        print(f"Error during conversion: {e}")

if __name__ == "__main__":
    process_articles_file()
    main()