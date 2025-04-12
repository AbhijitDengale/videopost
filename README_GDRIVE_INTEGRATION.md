# Google Drive to YouTube Integration

This system automatically uploads videos from your Google Drive 'GeminiStories' folder to your YouTube channels while maintaining a complete history of uploads in a Google Sheet.

## Features

- **Automated Video Discovery**: Scans your GeminiStories folder for new videos to upload
- **Complete Metadata Support**: Uses text files for video title, description, and tags
- **Thumbnail Support**: Automatically sets custom thumbnails for your videos
- **Multiple Channel Support**: Upload to any of your authenticated YouTube channels
- **Upload History Tracking**: Keeps a comprehensive record of all uploads in your Google Sheet
- **Error Handling**: Robust error handling with detailed logs

## Prerequisites

- Python 3.6 or higher
- Authenticated YouTube channels (using existing tokens)
- Google Drive service account credentials
- Google Sheet to track uploads (already set up)

## Setup

1. Make sure you have already authenticated your YouTube channels using the `auth_single_channel.py` script.

2. Ensure your Google Drive credentials are in place:
   - Place your service account credentials in `gd/credentials.json`

3. Install the required Python packages:
   ```
   pip install google-api-python-client google-auth google-auth-httplib2 google-auth-oauthlib
   ```

## File Structure in Google Drive

Each subfolder in your 'GeminiStories' folder should contain:

- `video.mp4` - The video file to upload
- `title.txt` - Contains the title for the video
- `description.txt` - Contains the description for the video
- `tags.txt` - Contains comma or space-separated tags
- `thumbnail.jpg` - Custom thumbnail image for the video

## Usage

### List Available YouTube Channels

```
python upload_gdrive_videos.py --list-channels
```

### Upload All Unuploaded Videos

```
python upload_gdrive_videos.py
```
This will interactively ask you to select which YouTube channel to use.

### Upload to a Specific Channel

```
python upload_gdrive_videos.py --channel-name "MagicMap Tales"
```
or
```
python upload_gdrive_videos.py --channel-id "UCho_M7XtPeCGrpmweUTD7xQ"
```

### Limit the Number of Uploads

```
python upload_gdrive_videos.py --limit 5
```

### Set Privacy Status

```
python upload_gdrive_videos.py --privacy-status unlisted
```
Options: `public`, `private`, `unlisted` (default is `unlisted`)

## Spreadsheet Integration

The script extends your existing Google Sheet with new columns to track:

- **Upload Status**: Yes, No, or Failed
- **Upload Date**: When the video was uploaded
- **YouTube URL**: Direct link to the uploaded video
- **YouTube Channel**: Which channel it was uploaded to
- **YouTube Video ID**: The unique ID for reference
- **Error Message**: Only populated if upload failed

## Troubleshooting

1. **Authentication Issues**:
   - Check that your YouTube channel tokens are valid
   - Ensure the Google Drive service account credentials are correct

2. **Missing Files**:
   - Ensure each subfolder has all required files (video.mp4, title.txt, etc.)

3. **Upload Failures**:
   - Check the spreadsheet's "Error Message" column for specific errors
   - For API quota issues, wait 24 hours before trying again

## Examples

### Typical Workflow

1. Create new content folders in Google Drive 'GeminiStories' with video and metadata files
2. Run the Google Drive scanning script to update the spreadsheet
3. Run `upload_gdrive_videos.py` to upload new videos to YouTube
4. Check the spreadsheet for upload status and YouTube URLs

### Batch Processing

For large numbers of videos, use the limit flag to process in batches:
```
python upload_gdrive_videos.py --limit 10 --channel-name "Tiny Trailblazers"
```

Run this multiple times until all videos are processed.

## Advanced Features

- **Resume Failed Uploads**: The script will not retry failed uploads automatically, but marking the Upload Status back to empty will allow retrying
- **Change Channels**: You can upload different videos to different channels by running the script multiple times with different channel parameters
