#!/usr/bin/env python3
import json
from datetime import datetime
import re
from urllib.parse import urljoin, urlparse
from pathlib import Path

# Configuration
JSON_FILE = "stackoverflow_questions.json"
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

def write_to_markdown(questions_data, output_file="stackoverflow_export.md"):
    """Write all questions and answers to a Markdown file with proper styling."""
    print(f"Writing {len(questions_data)} questions to {output_file}...")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Stack Overflow Teams Export\n\n")
        f.write(f"*Exported on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

        for question in questions_data:
            if not question:  # Skip empty entries
                continue

            # Write question title
            if 'title' in question:
                f.write(f"## {question['title']}\n\n")
            else:
                continue  # Skip questions without title

            # Question metadata
            if 'tags' in question:
                tags = ", ".join(question['tags']) if question['tags'] else "No tags"
                f.write(f"**Tags**: {tags}  \n")

            if 'owner' in question and 'display_name' in question['owner']:
                f.write(f"**Author**: {question['owner']['display_name']}  \n")

            if 'creation_date' in question:
                f.write(f"**Created**: {format_date(question['creation_date'])}  \n")

            if 'is_answered' in question:
                status = "✅ Answered" if question['is_answered'] else "❓ Unanswered"
                f.write(f"**Status**: {status}  \n")

            f.write("\n")  # Add an extra line after metadata

            # Question body
            if 'body_markdown' in question:
                body = replace_image_urls(question['body_markdown'])
                f.write(f"{body}\n\n")
            elif 'body' in question:
                body = replace_image_urls(question['body'])
                f.write(f"{body}\n\n")

            # Question comments
            if 'comments' in question and question['comments']:
                f.write(f"**Comments on Question:**\n\n")
                for comment in question['comments']:
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

            # Answers section
            if 'answers' in question and question['answers']:
                f.write(f"### Answers ({len(question['answers'])})\n\n")

                for answer in question['answers']:
                    if not answer:  # Skip empty answers
                        continue

                    # Answer metadata
                    if 'owner' in answer and 'display_name' in answer['owner']:
                        f.write(f"**Answered by**: {answer['owner']['display_name']}  \n")

                    if 'creation_date' in answer:
                        f.write(f"**Date**: {format_date(answer['creation_date'])}  \n")

                    if 'is_accepted' in answer and answer['is_accepted']:
                        f.write("✅ **Accepted Answer**  \n")

                    f.write("\n")  # Add an extra line after answer metadata

                    # Answer content
                    if 'body_markdown' in answer:
                        answer_body = replace_image_urls(answer['body_markdown'])
                        f.write(f"{answer_body}\n\n")
                    elif 'body' in answer:
                        answer_body = replace_image_urls(answer['body'])
                        f.write(f"{answer_body}\n\n")

                    # Answer comments
                    if 'comments' in answer and answer['comments']:
                        f.write(f"**Comments on this Answer:**\n\n")
                        for comment in answer['comments']:
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

                    f.write("---\n\n")  # Add separator between answers
            else:
                f.write("*No answers yet*\n\n")

            f.write("---\n\n")  # Add separator between questions

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

def process_questions_file():
    """Process the questions JSON file and download all images from Pashabank URLs."""
    # Read the JSON file
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        questions = json.load(f)

    print(f"Processing {len(questions)} questions...")

    # Track all image URLs
    all_urls = []
    downloaded_files = []

    # Process each question and its answers
    for question in questions:
        # Extract images from question body
        if 'body_markdown' in question:
            urls = extract_image_urls(question['body_markdown'])
            all_urls.extend(urls)

        # Extract images from answers
        if 'answers' in question:
            for answer in question['answers']:
                if 'body_markdown' in answer:
                    urls = extract_image_urls(answer['body_markdown'])
                    all_urls.extend(urls)

    # Remove duplicates
    unique_urls = list(set(all_urls))
    print(f"Found {len(unique_urls)} unique image URLs from pashabank.stackenterprise.co/images")

    # Store the image urls in a text file
    with open("image_urls.txt", 'w', encoding='utf-8') as f:
        for url in unique_urls:
            f.write(url + "\n")
    print(f"Image URLs saved to 'image_urls.txt'")

    print(f"Successfully downloaded {len(downloaded_files)} images to '{IMAGE_FOLDER}' folder")

def main():
    """Main function to read JSON and generate Markdown."""
    try:
        # Read the JSON file
        json_file = "stackoverflow_questions.json"
        print(f"Reading questions from {json_file}...")

        with open(json_file, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)

        # Generate the Markdown file
        write_to_markdown(questions_data)

        print("Markdown file created successfully!")

    except Exception as e:
        print(f"Error during conversion: {e}")

if __name__ == "__main__":
    process_questions_file()
    main()