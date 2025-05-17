#!/usr/bin/env python3
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup

# Configuration
CONFLUENCE_BASE_URL = "YOUR_CONFLUENCE_URL"  # e.g., "https://yourcompany.atlassian.net/wiki"
PARENT_PAGE_ID = "YOUR_PARENT_PAGE_ID"  # ID of the parent page where articles will be created
SPACE_KEY = "YOUR_SPACE_KEY"  # e.g., "TEAM" or "DOC"
PAT_FILE_PATH = "pat.txt"
ARTICLES_FILE_PATH = "../../articles/stackoverflow_articles.json"

def read_personal_access_token(file_path):
    """Read the personal access token from file."""
    with open(file_path, 'r') as file:
        return file.read().strip()

def read_articles(file_path):
    """Read the StackOverflow articles from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def clean_html(html_content):
    """Clean HTML content to make it valid XHTML for Confluence."""
    # Parse the HTML using BeautifulSoup with the 'html.parser'
    soup = BeautifulSoup(html_content, 'html.parser')

    # Convert to string, which also cleans up any invalid HTML
    cleaned_html = str(soup)

    # Additional fixes for Confluence-specific requirements
    # Replace self-closing tags that might cause issues
    cleaned_html = cleaned_html.replace('<br>', '<br/>')

    return cleaned_html

def get_existing_pages(token, space_key, parent_id=None):
    """Get a list of existing pages in the space."""
    url = f"{CONFLUENCE_BASE_URL}/rest/api/content"
    params = {
        "spaceKey": space_key,
        "expand": "title",
        "limit": 500,  # Increased limit to get more pages
        "type": "page"
    }

    # Only filter by ancestor if specified
    if parent_id:
        params["ancestorId"] = parent_id

    headers = {
        "Authorization": f"Bearer {token}"
    }

    existing_pages = {}
    start = 0

    # Paginate through all results
    while True:
        params["start"] = start
        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            print(f"Error fetching existing pages: {response.status_code}")
            print(f"Response: {response.text}")
            return existing_pages

        data = response.json()
        results = data.get('results', [])

        for page in results:
            existing_pages[page['title']] = page['id']

        # Check if we need to fetch more pages
        if len(results) < params["limit"]:
            break

        start += len(results)

    return existing_pages

def page_exists(token, title, space_key):
    """Check if a page with the given title exists in the space."""
    url = f"{CONFLUENCE_BASE_URL}/rest/api/content"
    params = {
        "spaceKey": space_key,
        "title": title,
        "expand": "title"
    }

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return len(data.get('results', [])) > 0

    return False

def create_confluence_page(token, title, body, space_key, parent_id):
    """Create a new page in Confluence."""
    # First check if the page exists
    if page_exists(token, title, space_key):
        print(f"Page with title '{title}' already exists in space {space_key}")
        return None

    url = f"{CONFLUENCE_BASE_URL}/rest/api/content"

    # Clean the HTML body to ensure it's valid XHTML
    clean_body = clean_html(body)

    # Create page data
    data = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {
            "storage": {
                "value": clean_body,
                "representation": "storage"
            }
        },
        "ancestors": [{"id": parent_id}]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error creating page: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def main():
    # Read the personal access token
    token = read_personal_access_token(PAT_FILE_PATH)
    if not token:
        print("Failed to read personal access token.")
        return

    # Read StackOverflow articles
    articles = read_articles(ARTICLES_FILE_PATH)
    if not articles:
        print("Failed to read articles or no articles found.")
        return

    processed = 0
    skipped = 0

    for article in articles:

        title = article.get("title", "Untitled Article")

        # Check if article already exists
        if page_exists(token, title, SPACE_KEY):
            print(f"Article '{title}' already exists. Skipping.")
            skipped += 1
            continue

        # Format creation date
        if "creation_date" in article:
            creation_timestamp = article.get("creation_date")
            creation_date = datetime.fromtimestamp(creation_timestamp).strftime('%Y-%m-%d')
        else:
            creation_date = "Unknown date"

        # Format the article body
        # We'll use the HTML body directly since it's already in HTML format
        body = article.get("body", "")

        # Create a header with article metadata
        header = f"""
        <p><strong>Original Article:</strong> <a href="{article.get('link', '')}">{article.get('link', '')}</a></p>
        <p><strong>Created:</strong> {creation_date}</p>
        <p><strong>Tags:</strong> {', '.join(article.get('tags', []))}</p>
        <hr/>
        """

        # Combine header and body
        full_body = header + body

        # Create the page in Confluence
        result = create_confluence_page(
            token,
            title,
            full_body,
            SPACE_KEY,
            PARENT_PAGE_ID
        )

        if result:
            print(f"Successfully created page: {result.get('title')}")
            print(f"Page URL: {CONFLUENCE_BASE_URL}{result.get('_links', {}).get('webui', '')}")
            processed += 1
        else:
            print(f"Failed to create page for article: {title}")

    print(f"\nSummary: Processed {processed} articles, skipped {skipped} existing articles.")

if __name__ == "__main__":
    main()