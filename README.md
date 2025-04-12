# YouTube Video Uploader

A Python script for uploading videos to YouTube using the YouTube Data API v3.

## Prerequisites

- Python 3.6 or higher
- Google account with YouTube channel
- Google Cloud project with YouTube Data API enabled

## Setup

1. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Create a Google Cloud Project and enable the YouTube Data API**:

   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Navigate to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3" and enable it

3. **Create OAuth 2.0 credentials**:

   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Web application" as the application type
   - Add a name for your application
   - For "Authorized redirect URIs," add: `http://localhost:8080/`
   - Click "Create"
   - Download the JSON file and save it as `client_secrets.json` in the same directory as the script

## Usage

```bash
python upload_video.py --file="path/to/video.mp4" --title="Video Title" --description="Video Description" --keywords="keyword1,keyword2" --category="22" --privacyStatus="public"
```

### Command-line Arguments

- `--file`: (Required) The path to the video file you want to upload
- `--title`: The title of the video (default: "Test Title")
- `--description`: The description of the video (default: "Test Description")
- `--category`: The numeric category ID for the video (default: "22" which is "People & Blogs")
  - See [Video Categories](https://developers.google.com/youtube/v3/docs/videoCategories/list) for a full list
- `--keywords`: Comma-separated keywords/tags for the video (default: "")
- `--privacyStatus`: The privacy status of the video (options: "public", "private", "unlisted", default: "public")

## First-time Authorization

When you run the script for the first time, it will open a browser window asking you to authorize the application to access your YouTube account. After authorization, the credentials will be saved locally for future use.

## Example

```bash
python upload_video.py --file="vacation.mp4" --title="Summer Vacation 2025" --description="Family trip to Hawaii" --keywords="vacation,hawaii,beach" --privacyStatus="unlisted"
```

## Troubleshooting

- If you see an error about missing client secrets, make sure your `client_secrets.json` file is in the same directory as the script and contains the correct OAuth 2.0 credentials.
- If you encounter quota errors, check your Google Cloud Console to ensure you haven't exceeded your daily quota for the YouTube Data API.
- For other errors, check the error message for details on what went wrong.

## Notes

- The YouTube Data API has quotas that limit the number of requests you can make per day. Monitor your usage in the Google Cloud Console.
- Video uploads count as expensive operations against your quota.
