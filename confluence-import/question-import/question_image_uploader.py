#!/usr/bin/env python3
import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Configuration
CONFLUENCE_BASE_URL = "YOUR_CONFLUENCE_URL"  # e.g., "https://yourcompany.atlassian.net/wiki"
PARENT_PAGE_ID = "YOUR_PARENT_PAGE_ID"  # ID of the parent page where questions will be created
SPACE_KEY = "YOUR_SPACE_KEY"  # e.g., "TEAM" or "DOC"
PAT_FILE_PATH = "pat.txt"
IMAGES_FOLDER_PATH = "question-images"
QUESTIONS_FILE_PATH = "../../questions/stackoverflow_questions.json"
EXTERNAL_IMAGE_DOMAIN = "YOUR_STACK_ENTERPRISE_DOMAIN"  # Domain of external images

def read_personal_access_token(file_path):
    """Read the personal access token from file."""
    with open(file_path, 'r') as file:
        return file.read().strip()

def read_questions(file_path):
    """Read the StackOverflow questions from JSON file."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_questions(questions, file_path):
    """Save the updated StackOverflow questions back to the JSON file."""
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(questions, file, ensure_ascii=False, indent=4)
    print(f"Questions successfully saved to {file_path}")

def clean_html(html_content):
    """Clean HTML content to make it valid XHTML for Confluence."""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Convert to string, which also cleans up any invalid HTML
    cleaned_html = str(soup)

    # Additional fixes for Confluence-specific requirements
    cleaned_html = cleaned_html.replace('<br>', '<br/>')

    return cleaned_html

def page_exists(token, title, space_key):
    """Check if a page with the given title exists in the space under the parent."""
    url = f"{CONFLUENCE_BASE_URL}/rest/api/content"
    params = {
        "spaceKey": space_key,
        "title": title,
        "expand": "body.storage"
    }

    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        results = response.json().get('results', [])
        if results:
            return results[0]

    return None

def upload_image_to_confluence(token, page_id, image_path):
    """Upload an image as an attachment to a Confluence page."""
    url = f"{CONFLUENCE_BASE_URL}/rest/api/content/{page_id}/child/attachment"

    # Get the image filename from the path
    filename = os.path.basename(image_path)

    # Determine the MIME type based on the file extension
    mime_type = "image/png"  # Default to PNG
    if filename.lower().endswith(".jpg") or filename.lower().endswith(".jpeg"):
        mime_type = "image/jpeg"
    elif filename.lower().endswith(".gif"):
        mime_type = "image/gif"

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Atlassian-Token": "no-check"
    }

    # Check if attachment already exists
    params = {"filename": filename}
    response = requests.get(url, headers=headers, params=params)

    # Read the image file
    with open(image_path, 'rb') as file:
        image_data = file.read()

    if response.status_code == 200 and len(response.json().get("results", [])) > 0:
        # Attachment exists, get the attachment ID
        attachment_id = response.json()["results"][0]["id"]
        # Update the attachment
        update_url = f"{url}/{attachment_id}/data"
        files = {"file": (filename, image_data, mime_type)}
        response = requests.post(update_url, headers=headers, files=files)
    else:
        # Create new attachment
        files = {"file": (filename, image_data, mime_type)}
        response = requests.post(url, headers=headers, files=files)

    if response.status_code in [200, 201]:
        result = response.json()
        # Construct the URL for the image in Confluence
        download_url = f"{CONFLUENCE_BASE_URL}/download/attachments/{page_id}/{filename}"
        return download_url
    else:
        print(f"Error uploading image {filename}: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def update_page_with_new_image_urls(token, page_id, updated_content, title=None, version=None):
    """Update a Confluence page with new content that has updated image URLs."""
    url = f"{CONFLUENCE_BASE_URL}/rest/api/content/{page_id}"

    # First, get the current version of the page if not provided
    if version is None:
        response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params={"expand": "version"})

        if response.status_code != 200:
            print(f"Error getting page version: {response.status_code}")
            print(f"Response: {response.text}")
            return False

        current_version = response.json()["version"]["number"]
        title = title or response.json()["title"]
    else:
        current_version = version

    # Prepare the update data
    data = {
        "version": {
            "number": current_version + 1  # Increment the version
        },
        "title": title,
        "type": "page",
        "body": {
            "storage": {
                "value": updated_content,
                "representation": "storage"
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # Update the page
    response = requests.put(url, json=data, headers=headers)

    if response.status_code in [200, 204]:
        print(f"Successfully updated page: {page_id}")
        return True
    else:
        print(f"Error updating page: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def find_and_replace_image_urls(html_content, uploaded_images, image_filenames):
    """Find external image URLs in HTML content and replace them with Confluence-hosted URLs."""
    soup = BeautifulSoup(html_content, 'html.parser')
    replaced_count = 0
    replacements = {}  # Track the replacements for updating the original question

    # Find all <a> tags that contain <img> tags
    for a_tag in soup.find_all('a'):
        # Check if the <a> tag has an href attribute and if it contains an <img> tag
        if a_tag.has_attr('href') and EXTERNAL_IMAGE_DOMAIN in a_tag['href'] and a_tag.find('img'):
            img_tag = a_tag.find('img')

            # Get the filename from the href
            parsed_url = urlparse(a_tag['href'])
            path = parsed_url.path
            filename = os.path.basename(path)

            # Check if we have an uploaded version of this image
            if filename in image_filenames and filename in uploaded_images:
                # Update both the <a> href and the <img> src attributes
                old_href = a_tag['href']
                a_tag['href'] = uploaded_images[filename]

                # Also update the image source if it exists
                if img_tag.has_attr('src'):
                    img_tag['src'] = uploaded_images[filename]

                replaced_count += 1
                print(f"Replaced image URL in <a> href: {old_href} -> {uploaded_images[filename]}")
                replacements[old_href] = uploaded_images[filename]

    # Also find standalone <img> tags (not inside <a> tags)
    for img_tag in soup.find_all('img', src=True):
        # Skip images that are already processed (inside <a> tags)
        if img_tag.parent.name == 'a' and EXTERNAL_IMAGE_DOMAIN in img_tag.parent.get('href', ''):
            continue

        src = img_tag['src']
        if EXTERNAL_IMAGE_DOMAIN in src:
            parsed_url = urlparse(src)
            path = parsed_url.path
            filename = os.path.basename(path)

            if filename in image_filenames and filename in uploaded_images:
                old_src = img_tag['src']
                img_tag['src'] = uploaded_images[filename]
                replaced_count += 1
                print(f"Replaced standalone image src: {old_src} -> {uploaded_images[filename]}")
                replacements[old_src] = uploaded_images[filename]

    return str(soup), replaced_count, replacements

def extract_image_filenames_from_html(html_content):
    """Extract image filenames from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    filenames = []

    # Check <a> tags with href pointing to images
    for a_tag in soup.find_all('a'):
        if a_tag.has_attr('href') and EXTERNAL_IMAGE_DOMAIN in a_tag['href']:
            parsed_url = urlparse(a_tag['href'])
            path = parsed_url.path
            filename = os.path.basename(path)
            filenames.append(filename)

    # Also check <img> tags
    for img in soup.find_all('img'):
        src = img.get('src')
        if src and EXTERNAL_IMAGE_DOMAIN in src:
            parsed_url = urlparse(src)
            path = parsed_url.path
            filename = os.path.basename(path)
            if filename not in filenames:  # Avoid duplicates
                filenames.append(filename)

    return filenames

def update_question_content(question, replacements):
    """Update the question content with the replacements."""
    if not replacements:
        return question

    # Update the question body
    body = question.get("body", "")
    for old_url, new_url in replacements.items():
        body = body.replace(old_url, new_url)
    question["body"] = body

    # Update the question body_markdown if it exists
    if "body_markdown" in question:
        body_markdown = question.get("body_markdown", "")
        for old_url, new_url in replacements.items():
            body_markdown = body_markdown.replace(old_url, new_url)
        question["body_markdown"] = body_markdown

    # Update image URLs in answers
    if "answers" in question and question["answers"]:
        for i, answer in enumerate(question["answers"]):
            # Update answer body
            answer_body = answer.get("body", "")
            if answer_body:
                for old_url, new_url in replacements.items():
                    answer_body = answer_body.replace(old_url, new_url)
                answer["body"] = answer_body

            # Update answer body_markdown if it exists
            if "body_markdown" in answer:
                answer_body_markdown = answer.get("body_markdown", "")
                for old_url, new_url in replacements.items():
                    answer_body_markdown = answer_body_markdown.replace(old_url, new_url)
                answer["body_markdown"] = answer_body_markdown

            question["answers"][i] = answer

    return question

def main():
    # Read the personal access token
    token = read_personal_access_token(PAT_FILE_PATH)
    if not token:
        print("Failed to read personal access token.")
        return

    # Step 1: Read the StackOverflow questions
    questions = read_questions(QUESTIONS_FILE_PATH)
    if not questions:
        print("Failed to read questions or no questions found.")
        return

    print(f"Found {len(questions)} questions in the JSON file.")

    # Step 2: Get all image files from the images folder
    image_files = []
    image_filenames = []
    for filename in os.listdir(IMAGES_FOLDER_PATH):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            image_path = os.path.join(IMAGES_FOLDER_PATH, filename)
            image_files.append(image_path)
            image_filenames.append(filename)

    if not image_files:
        print("No image files found in the specified folder.")
        return

    print(f"Found {len(image_files)} image files to upload.")

    # Track uploaded images
    uploaded_images = {}
    # Track if any questions were updated
    questions_updated = False

    # Process each question
    for i, question in enumerate(questions):
        title = question.get("title", "Untitled Question")
        html_content = question.get("body", "")

        # Fix HTML entities in title
        title = BeautifulSoup(title, 'html.parser').get_text()

        print(f"\nProcessing question: {title}")

        # Check if the question already exists in Confluence
        existing_page = page_exists(token, title, SPACE_KEY)

        # Extract image filenames from the question
        question_image_filenames = extract_image_filenames_from_html(html_content)

        # Also extract image filenames from answers
        answers_html = ""
        if "answers" in question and question["answers"]:
            for answer in question["answers"]:
                answer_html = answer.get("body", "")
                answers_html += answer_html

            answer_image_filenames = extract_image_filenames_from_html(answers_html)
            question_image_filenames.extend(answer_image_filenames)
            # Remove duplicates
            question_image_filenames = list(set(question_image_filenames))

        if not question_image_filenames:
            print("No images found in this question or its answers")
            continue

        print(f"Found {len(question_image_filenames)} images in this question and its answers")

        if existing_page:
            page_id = existing_page["id"]
            print(f"Question already exists in Confluence with ID: {page_id}")

            # Upload images to the existing page
            for image_path in image_files:
                filename = os.path.basename(image_path)

                if filename in question_image_filenames:
                    print(f"Uploading image: {filename}")
                    download_url = upload_image_to_confluence(token, page_id, image_path)
                    if download_url:
                        uploaded_images[filename] = download_url

            # Get the current page content
            existing_content = existing_page["body"]["storage"]["value"]

            # Replace image URLs in the content
            updated_content, replaced_count, replacements = find_and_replace_image_urls(existing_content, uploaded_images, image_filenames)

            if replaced_count > 0:
                # Update the page with the new content
                print(f"Updating page with {replaced_count} replaced image URLs")
                current_version = existing_page["version"]["number"] if "version" in existing_page else None
                update_page_with_new_image_urls(token, page_id, updated_content, title, current_version)

                # Update the question in the JSON file
                questions[i] = update_question_content(question, replacements)
                questions_updated = True
            else:
                print("No image URLs were replaced in this question")

    # Save the updated questions back to the JSON file
    if questions_updated:
        save_questions(questions, QUESTIONS_FILE_PATH)
        print("Questions JSON file updated with new image URLs.")
    else:
        print("No questions were updated, JSON file remains unchanged.")

    print("\nQuestion image uploading and URL replacement complete.")

if __name__ == "__main__":
    main()