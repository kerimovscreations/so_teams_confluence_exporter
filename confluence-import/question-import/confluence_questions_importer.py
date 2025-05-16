#!/usr/bin/env python3
import json
import requests
import os
import base64
from datetime import datetime
import time
from bs4 import BeautifulSoup

# Configuration
CONFLUENCE_BASE_URL = "https://confluence.pashabank.az"
PARENT_PAGE_ID = "322175520"  # ID of "Stackoverflow questions" page
SPACE_KEY = "DE"
PAT_FILE_PATH = "confluence-import/question-import/pat.txt"
QUESTIONS_FILE_PATH = "questions/stackoverflow_questions.json"

def read_personal_access_token(file_path):
    """Read the personal access token from file."""
    with open(file_path, 'r') as file:
        return file.read().strip()

def read_questions(file_path):
    """Read the StackOverflow questions from JSON file."""
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

def format_comments(comments):
    """Format comments as HTML."""
    if not comments:
        return ""

    comments_html = "<h3>Comments:</h3><div class='comments'>"

    for comment in comments:
        user_name = comment.get("owner", {}).get("display_name", "Unknown User")
        creation_date = datetime.fromtimestamp(comment.get("creation_date", 0)).strftime('%Y-%m-%d %H:%M')
        body = comment.get("body", "")

        comments_html += f"""
        <div class='comment'>
            <p><strong>{user_name}</strong> <em>({creation_date})</em>:</p>
            <div class='comment-body'>{body}</div>
        </div>
        <hr/>
        """

    comments_html += "</div>"
    return comments_html

def format_answers(answers):
    """Format answers as HTML."""
    if not answers:
        return ""

    answers_html = "<h2>Answers:</h2>"

    for answer in answers:
        user_name = answer.get("owner", {}).get("display_name", "Unknown User")
        creation_date = datetime.fromtimestamp(answer.get("creation_date", 0)).strftime('%Y-%m-%d %H:%M')
        body = answer.get("body", "")
        is_accepted = answer.get("is_accepted", False)
        score = answer.get("score", 0)

        accepted_status = "<span style='color:green;'>(Accepted Answer)</span>" if is_accepted else ""
        score_display = f"Score: {score}"

        answers_html += f"""
        <div class='answer'>
            <p><strong>{user_name}</strong> <em>({creation_date})</em> {accepted_status} - {score_display}</p>
            <div class='answer-body'>{body}</div>
        </div>
        """

        # Add comments on this answer
        answer_comments = answer.get("comments", [])
        if answer_comments:
            answers_html += "<div class='answer-comments' style='margin-left: 20px;'>"
            answers_html += "<h4>Comments on this answer:</h4>"

            for comment in answer_comments:
                commenter = comment.get("owner", {}).get("display_name", "Unknown User")
                comment_date = datetime.fromtimestamp(comment.get("creation_date", 0)).strftime('%Y-%m-%d %H:%M')
                comment_body = comment.get("body", "")

                answers_html += f"""
                <div class='comment'>
                    <p><strong>{commenter}</strong> <em>({comment_date})</em>:</p>
                    <div class='comment-body'>{comment_body}</div>
                </div>
                """

            answers_html += "</div>"

        answers_html += "<hr/>"

    return answers_html

def main():
    # Read the personal access token
    token = read_personal_access_token(PAT_FILE_PATH)
    if not token:
        print("Failed to read personal access token.")
        return

    # Read StackOverflow questions
    questions = read_questions(QUESTIONS_FILE_PATH)
    if not questions:
        print("Failed to read questions or no questions found.")
        return

    processed = 0
    skipped = 0

    for question in questions:

      title = question.get("title", "Untitled Question")

      # Check if question already exists
      if page_exists(token, title, SPACE_KEY):
          print(f"Question '{title}' already exists. Skipping.")
          skipped += 1
          return

      # Format creation date
      if "creation_date" in question:
          creation_timestamp = question.get("creation_date")
          creation_date = datetime.fromtimestamp(creation_timestamp).strftime('%Y-%m-%d')
      else:
          creation_date = "Unknown date"

      # Format the question body
      # We'll use the HTML body directly since it's already in HTML format
      body = question.get("body", "")

      # Add question metadata header
      tags = question.get("tags", [])
      tags_display = ", ".join([f"<code>{tag}</code>" for tag in tags])

      user_name = question.get("owner", {}).get("display_name", "Unknown User")
      view_count = question.get("view_count", 0)
      score = question.get("score", 0)
      is_answered = "Yes" if question.get("is_answered", False) else "No"

      header = f"""
      <div class='question-metadata'>
          <p><strong>Original Question:</strong> <a href="{question.get('link', '')}">{question.get('link', '')}</a></p>
          <p><strong>Asked by:</strong> {user_name}</p>
          <p><strong>Created:</strong> {creation_date}</p>
          <p><strong>Tags:</strong> {tags_display}</p>
          <p><strong>Views:</strong> {view_count} | <strong>Score:</strong> {score} | <strong>Answered:</strong> {is_answered}</p>
      </div>
      <hr/>
      <h1>Question:</h1>
      """

      # Format question comments
      comments_html = format_comments(question.get("comments", []))

      # Format answers
      answers_html = format_answers(question.get("answers", []))

      # Combine everything
      full_body = header + body + comments_html + answers_html

      # Add CSS styling
      styling = """
      <style>
          .question-metadata {
              background-color: #f5f5f5;
              padding: 10px;
              border-radius: 5px;
              margin-bottom: 20px;
          }
          .comments, .answer-comments {
              background-color: #f9f9f9;
              padding: 10px;
              border-left: 3px solid #ccc;
              margin: 10px 0;
          }
          .comment {
              margin-bottom: 10px;
          }
          .answer {
              margin-bottom: 20px;
              border-bottom: 1px solid #eee;
              padding-bottom: 10px;
          }
      </style>
      """

      full_body = styling + full_body

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
          print(f"Failed to create page for question: {title}")

      print(f"\nSummary: Processed {processed} questions, skipped {skipped} existing questions.")

if __name__ == "__main__":
    main()