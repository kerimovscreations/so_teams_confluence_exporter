# Stack Overflow Teams Export Tool

This tool helps export content (questions, answers, articles, and comments) from Stack Overflow Teams into markdown format for backup or migration purposes.

## Overview

The project consists of several scripts that:

1. Fetch data from Stack Overflow Teams API
2. Store raw data in JSON format
3. Convert JSON data to human-readable Markdown
4. Extract image URLs for downloading
5. Provide utilities for importing content to Confluence (optional)

## Directory Structure

```
so_teams_export/
├── README.md                   # This file
├── articles/                   # Scripts for exporting SO Teams articles
│   ├── client_key.txt          # API client key (required)
│   ├── so_articles_export.py   # Script to export articles to JSON
│   ├── json_to_markdown.py     # Convert JSON to Markdown
│   ├── image_urls.txt          # Generated list of image URLs
│   ├── stackoverflow_articles.json  # Raw data in JSON format
│   ├── stackoverflow_articles.md    # Formatted data in Markdown
│   └── images/                 # Folder for downloaded images
├── questions/                  # Scripts for exporting SO Teams questions
│   ├── client_key.txt          # API client key (required)
│   ├── so_teams_export.py      # Script to export questions to JSON
│   ├── json_to_markdown.py     # Convert JSON to Markdown
│   ├── image_urls.txt          # Generated list of image URLs
│   ├── stackoverflow_questions.json  # Raw data in JSON format
│   ├── stackoverflow_export.md      # Formatted data in Markdown
│   └── images/                 # Folder for downloaded images
└── confluence-import/          # Optional scripts for importing to Confluence
    ├── article-import/         # Import articles to Confluence
    │   ├── confluence_importer.py    # Script to import articles
    │   ├── image_uploader.py         # Upload images to Confluence
    │   ├── pat.txt                   # Personal Access Token (required)
    │   └── article-images/           # Directory with images to upload
    └── question-import/         # Import questions to Confluence
        ├── confluence_questions_importer.py   # Script to import questions
        ├── question_image_uploader.py         # Upload images to Confluence
        ├── pat.txt                   # Personal Access Token (required)
        └── question-images/          # Directory with images to upload
```

## Prerequisites

- Python 3.6 or higher
- `requests` library: `pip install requests`
- A Stack Overflow Teams account with API access
- Client key for Stack Overflow Teams API

## Setup Instructions

### 1. Obtain API Client Key

1. Login to your Stack Overflow Teams account
2. Go to your profile settings
3. Navigate to the API section
4. Generate a client key
5. Copy the client key

### 2. Configure API Key Files

1. For questions export:
   - Create or edit `/questions/client_key.txt`
   - Paste your client key as plain text
   - Save the file

2. For articles export:
   - Create or edit `/articles/client_key.txt`
   - Paste your client key as plain text
   - Save the file

## Usage

### Exporting Questions & Answers

1. Change to the questions directory:
   ```bash
   cd /path/to/so_teams_export/questions/
   ```

2. Run the export script:
   ```bash
   python so_teams_export.py
   ```
   This will:
   - Fetch all questions from Stack Overflow Teams
   - Download question details, answers, and comments
   - Save raw data to `stackoverflow_questions.json`
   - Generate a formatted Markdown file at `stackoverflow_export.md`
   - Create a list of image URLs in `image_urls.txt`

### Exporting Articles

1. Change to the articles directory:
   ```bash
   cd /path/to/so_teams_export/articles/
   ```

2. Run the export script:
   ```bash
   python so_articles_export.py
   ```
   This will:
   - Fetch all articles from Stack Overflow Teams
   - Download article details and comments
   - Save raw data to `stackoverflow_articles.json`

3. Convert the JSON to Markdown:
   ```bash
   python json_to_markdown.py
   ```
   This will:
   - Process the JSON data
   - Create a formatted Markdown file at `stackoverflow_articles.md`
   - Extract image URLs to `image_urls.txt`

### Downloading Images

After running the export scripts, you'll have a list of image URLs in `image_urls.txt` files. You can use a tool like wget or curl to download these images:

```bash
# Example using wget
cd /path/to/so_teams_export/articles/images/
wget -i ../image_urls.txt

# For questions images
cd /path/to/so_teams_export/questions/images/
wget -i ../image_urls.txt
```

Or you can use a Python script to download them:

```python
#!/usr/bin/env python3
import requests
import os

def download_images(urls_file, output_dir):
    with open(urls_file, 'r') as f:
        urls = f.read().splitlines()

    os.makedirs(output_dir, exist_ok=True)

    for url in urls:
        filename = url.split('/')[-1]
        output_path = os.path.join(output_dir, filename)

        print(f"Downloading {url} to {output_path}")
        response = requests.get(url)

        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded {filename}")
        else:
            print(f"Failed to download {url}")

# Example usage
download_images('image_urls.txt', 'images/')
```

## Confluence Import (Optional)

If you want to import the exported content to Confluence, you can use the scripts in the `confluence-import` directory:

### Setting up Confluence Access

1. Generate a Personal Access Token (PAT) in Confluence
2. Save the token to:
   - `/confluence-import/article-import/pat.txt` for articles
   - `/confluence-import/question-import/pat.txt` for questions

### Importing to Confluence

1. For articles:
   ```bash
   cd /path/to/so_teams_export/confluence-import/article-import/
   python confluence_importer.py
   ```

2. For questions:
   ```bash
   cd /path/to/so_teams_export/confluence-import/question-import/
   python confluence_questions_importer.py
   ```

## Troubleshooting

### API Rate Limiting

If you encounter rate limiting issues, the scripts will automatically wait before retrying. However, you may need to:
- Increase the sleep time between requests
- Run the scripts during off-peak hours

### SSL Certificate Errors

If you encounter SSL certificate errors:
- Ensure your system has up-to-date SSL certificates installed
- You might need to configure the system to trust the Stack Overflow Teams certificate
- If needed for internal/development environments, you can modify the scripts to add `verify=False` to the requests.get() calls, but note that this reduces security and should be used cautiously

### Missing Images

If some images are missing:
- Check if the URLs in `image_urls.txt` are accessible
- Ensure you have permission to access the images
- Some images might require authentication

## Maintenance

- Keep your client key secure and do not share it
- Update your client key if it expires or is compromised
- Check for updates to this tool periodically

## Security Notes

- The client key provides access to your Stack Overflow Teams content
- The scripts store the key as plain text, so ensure file permissions are restricted
- If using the Confluence import feature, the PAT should also be kept secure

## License

This project is licensed under the MIT License - see the LICENSE file for details.