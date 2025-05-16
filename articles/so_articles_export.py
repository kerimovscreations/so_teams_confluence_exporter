#!/usr/bin/env python3
import requests
import time
import json
from datetime import datetime

# Configuration
BASE_URL = "https://pashabank.stackenterprise.co/api/2.3"
CLIENT_KEY_PATH = "client_key.txt"
JSON_OUTPUT_FILE = "stackoverflow_articles.json"
PAGE_SIZE = 100  # Number of items to fetch per page

def load_client_key():
    """Load the client key from the file."""
    with open(CLIENT_KEY_PATH, 'r') as f:
        return f.read().strip()

def make_api_request(endpoint, params=None):
    """Make an API request to Stack Overflow Teams."""
    if params is None:
        params = {}

    # Add client key to all requests
    params['key'] = load_client_key()

    # Add the specified filter to all requests - including all article details
    # This filter should include both body and body_markdown
    params['filter'] = '!-NjR7YBAGtXRbJN1ECErSn*8.E3y04xrL'

    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, params=params, verify=False)

    # Check for rate limiting
    if response.status_code == 429:
        backoff = int(response.headers.get('Backoff', 30))
        print(f"Rate limited. Waiting for {backoff} seconds...")
        time.sleep(backoff)
        return make_api_request(endpoint, params)

    # Raise exception for other errors
    response.raise_for_status()

    return response.json()

def fetch_all_articles():
    """Fetch all articles from Stack Overflow Teams."""
    all_articles = []
    page = 1
    has_more = True

    print("Fetching articles...")

    while has_more:
        params = {
            'page': page,
            'pagesize': PAGE_SIZE,
            'sort': 'creation',
            'order': 'asc',
        }

        data = make_api_request('articles', params)

        if 'items' in data:
            all_articles.extend(data['items'])
            print(f"Fetched page {page}, got {len(data['items'])} articles. Total: {len(all_articles)}")

        has_more = data.get('has_more', False)
        page += 1

        # Be nice to the API
        time.sleep(1)

    return all_articles

def fetch_comment_details(comment_id):
    """Fetch detailed information for a single comment."""
    data = make_api_request(f'comments/{comment_id}')

    if 'items' in data and data['items']:
        return data['items'][0]

    print(f"No details found for comment {comment_id}")
    return None

def fetch_comments_for_article(article_id):
    """Fetch all comments for a specific article and then
    fetch full details for each comment individually.

    Args:
        article_id: The ID of the article

    Returns:
        List of comments with full details for the article
    """
    params = {
        'order': 'asc',
        'sort': 'creation',
        'site': 'stackoverflowteams',
        'pagesize': PAGE_SIZE
    }

    # First get the list of comments for this article
    data = make_api_request(f'articles/{article_id}/comments', params)

    detailed_comments = []

    if 'items' in data and data['items']:
        comment_list = data['items']
        print(f"Found {len(comment_list)} comments for article {article_id}. Fetching details...")

        # For each comment, fetch its full details
        for i, comment_summary in enumerate(comment_list):
            comment_id = comment_summary['comment_id']
            print(f"  Fetching details for comment {i+1}/{len(comment_list)} (ID: {comment_id})...")

            # Get detailed comment information
            detailed_comment = fetch_comment_details(comment_id)

            if detailed_comment:
                # Ensure both body and body_markdown fields are present
                if 'body' in detailed_comment and 'body_markdown' not in detailed_comment:
                    detailed_comment['body_markdown'] = detailed_comment['body']
                elif 'body_markdown' in detailed_comment and 'body' not in detailed_comment:
                    detailed_comment['body'] = detailed_comment['body_markdown']

                detailed_comments.append(detailed_comment)

            # Be nice to the API
            time.sleep(0.2)

    return detailed_comments

def fetch_article_details(article_id):
    """Fetch detailed information for a single article, including comments."""
    # Fetch the article details
    params = {
        'site': 'stackoverflowteams'
    }
    data = make_api_request(f'articles/{article_id}', params)

    if 'items' not in data or not data['items']:
        print(f"No details found for article {article_id}")
        return None

    # Get the first item (the article)
    article = data['items'][0]

    # Fetch comments for the article
    print(f"Fetching comments for article {article_id}...")
    article['comments'] = fetch_comments_for_article(article_id)

    return article

def main():
    """Main function to export Stack Overflow Teams articles to JSON."""
    try:
        # Fetch all articles first (to get IDs)
        articles = fetch_all_articles()
        print(f"Fetched a total of {len(articles)} articles.")

        # Process each article individually to get full details including comments
        detailed_articles = []
        for i, article_summary in enumerate(articles):
            article_id = article_summary['article_id']
            print(f"Processing article {i+1}/{len(articles)} (ID: {article_id})...")

            # Fetch detailed information for this article
            detailed_article = fetch_article_details(article_id)
            if detailed_article:
                detailed_articles.append(detailed_article)

            # Be nice to the API
            time.sleep(0.5)

        # Save enriched articles to JSON file
        print(f"Saving enriched articles to {JSON_OUTPUT_FILE}...")
        with open(JSON_OUTPUT_FILE, 'w', encoding='utf-8') as json_file:
            json.dump(detailed_articles, json_file, indent=4)
        print(f"Enriched articles saved to {JSON_OUTPUT_FILE}")

        print("To generate a Markdown file from this JSON, run: ./json_to_markdown.py")

    except Exception as e:
        print(f"Error during export: {e}")

if __name__ == "__main__":
    main()