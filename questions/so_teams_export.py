#!/usr/bin/env python3
import requests
import time
import json
from datetime import datetime

# Configuration
BASE_URL = "https://pashabank.stackenterprise.co/api/2.3"
CLIENT_KEY_PATH = "client_key.txt"
OUTPUT_FILE = "stackoverflow_export.md"
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

    # Add the specified filter to all requests - including comments in the response
    # This filter should include both body and body_markdown for comments
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

def fetch_all_questions():
    """Fetch all questions from Stack Overflow Teams."""
    all_questions = []
    page = 1
    has_more = True

    print("Fetching questions...")

    while has_more:
        params = {
            'page': page,
            'pagesize': PAGE_SIZE,
            'sort': 'creation',
            'order': 'asc',
        }

        data = make_api_request('questions', params)

        if 'items' in data:
            all_questions.extend(data['items'])
            print(f"Fetched page {page}, got {len(data['items'])} questions. Total: {len(all_questions)}")

        has_more = data.get('has_more', False)
        page += 1

        # Be nice to the API
        time.sleep(1)

    return all_questions

def fetch_answers_for_question(question_id):
    """Fetch all answers for a specific question."""
    params = {
        'order': 'asc',
        'sort': 'creation',
        'site': 'stackoverflowteams',
        'pagesize': PAGE_SIZE
    }

    data = make_api_request(f'questions/{question_id}/answers', params)

    if 'items' in data:
        return data['items']

    return []

def fetch_comment_details(comment_id):
    """Fetch detailed information for a single comment."""

    data = make_api_request(f'comments/{comment_id}')

    if 'items' in data and data['items']:
        return data['items'][0]

    print(f"No details found for comment {comment_id}")
    return None

def fetch_comments_for_post(post_id, post_type):
    """Fetch all comments for a specific post (question or answer) and then
    fetch full details for each comment individually.

    Args:
        post_id: The ID of the post (question or answer)
        post_type: Either 'questions' or 'answers'

    Returns:
        List of comments with full details for the post
    """
    params = {
        'order': 'asc',
        'sort': 'creation',
        'site': 'stackoverflowteams',
        'pagesize': PAGE_SIZE
    }

    # First get the list of comments for this post
    data = make_api_request(f'{post_type}/{post_id}/comments', params)

    detailed_comments = []

    if 'items' in data and data['items']:
        comment_list = data['items']
        print(f"Found {len(comment_list)} comments for {post_type[:-1]} {post_id}. Fetching details...")

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

def fetch_question_details(question_id):
    """Fetch detailed information for a single question, including answers and comments."""
    # Fetch the question details
    params = {
        'site': 'stackoverflowteams'
    }
    data = make_api_request(f'questions/{question_id}', params)

    if 'items' not in data or not data['items']:
        print(f"No details found for question {question_id}")
        return None

    # Get the first item (the question)
    question = data['items'][0]

    # Fetch comments for the question
    print(f"Fetching comments for question {question_id}...")
    question['comments'] = fetch_comments_for_post(question_id, 'questions')

    # Fetch answers for the question
    print(f"Fetching answers for question {question_id}...")
    question['answers'] = fetch_answers_for_question(question_id)

    # Fetch comments for each answer
    for answer in question['answers']:
        answer_id = answer['answer_id']
        print(f"Fetching comments for answer {answer_id}...")
        answer['comments'] = fetch_comments_for_post(answer_id, 'answers')
        time.sleep(0.2)  # Be nice to the API

    return question

def format_date(timestamp):
    """Convert Unix timestamp to readable date."""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def write_to_markdown(questions_with_answers):
    """Write all questions and answers to a Markdown file."""
    print(f"Writing {len(questions_with_answers)} questions to {OUTPUT_FILE}...")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Stack Overflow Teams Export\n\n")
        f.write(f"*Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

        for question in questions_with_answers:
            # Write question
            f.write(f"## {question['title']}\n\n")

            # Question metadata
            tags = ", ".join(question['tags']) if 'tags' in question else "No tags"
            f.write(f"**Asked by**: {question.get('owner', {}).get('display_name', 'Unknown User')} | ")
            f.write(f"**Date**: {format_date(question['creation_date'])} | ")
            f.write(f"**Tags**: {tags}\n\n")

            # Question body
            if 'body_markdown' in question:
                f.write(f"{question['body_markdown']}\n\n")
            elif 'body' in question:
                f.write(f"{question['body']}\n\n")

            # Question comments
            if 'comments' in question and question['comments']:
                f.write(f"### Comments on Question ({len(question['comments'])})\n\n")
                for comment in question['comments']:
                    f.write(f"**{comment.get('owner', {}).get('display_name', 'Unknown User')}** ")
                    f.write(f"({format_date(comment['creation_date'])}): ")

                    # Use body_markdown if available, fall back to body if not
                    comment_text = comment.get('body_markdown', comment.get('body', 'No content'))
                    f.write(f"{comment_text}\n\n")

            # Answers
            if 'answers' in question and question['answers']:
                f.write(f"### Answers ({len(question['answers'])})\n\n")

                for answer in question['answers']:
                    f.write(f"**Answered by**: {answer.get('owner', {}).get('display_name', 'Unknown User')} | ")
                    f.write(f"**Date**: {format_date(answer['creation_date'])}")

                    if answer.get('is_accepted'):
                        f.write(" | ✅ **Accepted Answer**")

                    f.write("\n\n")

                    # Answer body - prefer body_markdown when available
                    if 'body_markdown' in answer:
                        f.write(f"{answer['body_markdown']}\n\n")
                    elif 'body' in answer:
                        f.write(f"{answer['body']}\n\n")

                    # Answer comments
                    if 'comments' in answer and answer['comments']:
                        f.write(f"**Comments on this Answer:**\n\n")
                        for comment in answer['comments']:
                            f.write(f"**{comment.get('owner', {}).get('display_name', 'Unknown User')}** ")
                            f.write(f"({format_date(comment['creation_date'])}): ")

                            # Use body_markdown if available, fall back to body if not
                            comment_text = comment.get('body_markdown', comment.get('body', 'No content'))
                            f.write(f"{comment_text}\n\n")

                    f.write("---\n\n")
            else:
                f.write("*No answers yet*\n\n")

            f.write("---\n\n")

def main():
    """Main function to export Stack Overflow Teams questions and answers."""
    try:
        # Fetch all questions first (to get IDs)
        questions = fetch_all_questions()
        print(f"Fetched a total of {len(questions)} questions.")

        # Process each question individually to get full details including comments
        detailed_questions = []
        for i, question_summary in enumerate(questions):
            question_id = question_summary['question_id']
            print(f"Processing question {i+1}/{len(questions)} (ID: {question_id})...")

            # Fetch detailed information for this question
            detailed_question = fetch_question_details(question_id)
            if detailed_question:
                detailed_questions.append(detailed_question)

            # Be nice to the API
            time.sleep(0.5)

        # Save enriched questions to JSON file
        json_output_file = "stackoverflow_questions.json"
        print(f"Saving enriched questions to {json_output_file}...")
        with open(json_output_file, 'w', encoding='utf-8') as json_file:
            json.dump(detailed_questions, json_file, indent=4)
        print(f"Enriched questions saved to {json_output_file}")

    except Exception as e:
        print(f"Error during export: {e}")

if __name__ == "__main__":
    main()