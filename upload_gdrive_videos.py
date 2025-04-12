#!/usr/bin/env python3

import os
import json
import sys
import time
import datetime
import argparse
import io
import requests  # Added for Telegram API calls
import shutil  # Added for file cleanup operations
import random  # Added for random video selection

# Set console encoding for proper emoji display
if sys.stdout.encoding != 'utf-8':
    try:
        # Force UTF-8 encoding for console output
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # For older Python versions
        pass

# Google Drive and Sheets APIs
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload

# YouTube upload related imports
import google.oauth2.credentials
import googleapiclient.discovery
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
import httplib2
import random
import http.client

# Constants from Google Drive script
DRIVE_SHEETS_SCOPES = ['https://www.googleapis.com/auth/drive', 
                       'https://www.googleapis.com/auth/spreadsheets']
EXISTING_SHEET_ID = '15QuEt5e2LrrZljaDSp-YbY96nzMmD7MH6TEVsdyrXyw'
TARGET_FOLDER_NAME = 'GeminiStories'
TEMP_DIR = 'temp_download'

# YouTube upload constants
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)
MAX_RETRIES = 10
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")
CHANNEL_TOKENS_DIR = 'channel_tokens'
CHANNEL_MAPPINGS_FILE = 'channel_mappings.json'

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = "7425850499:AAFeqvSXe-KRaBCEvRlrpfdSbExSoGeMiCI"
TELEGRAM_CHAT_ID = "-1002493560505"
TELEGRAM_THREAD_ID = 177
TELEGRAM_NOTIFICATIONS_ENABLED = True  # Set to False to disable notifications

# New spreadsheet columns for tracking uploads
UPLOAD_TRACKING_COLUMNS = [
    'Upload Status',    # Yes/No/Failed
    'Upload Date',      # Timestamp 
    'YouTube URL',      # Full video URL
    'YouTube Channel',  # Channel name used
    'YouTube Video ID', # Video ID
    'Error Message'     # Only populated if failed
]

def get_google_drive_credentials():
    """Get credentials for Google Drive and Sheets API."""
    # Google Drive link for credentials.json
    CREDENTIALS_DRIVE_LINK = "https://drive.google.com/file/d/10geScM7zk-QMCNG-WBXMQpoFVQOoFILL/view?usp=sharing"
    credentials_file = os.path.join('gd', 'credentials.json')
    
    # Try to download from Google Drive first
    try:
        print("Downloading Google Drive credentials from Google Drive...")
        
        # Convert view URL to direct download URL
        file_id = CREDENTIALS_DRIVE_LINK.split('/d/')[1].split('/view')[0]
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # Create temp directory if it doesn't exist
        os.makedirs(TEMP_DIR, exist_ok=True)
        temp_credentials_file = os.path.join(TEMP_DIR, 'temp_credentials.json')
        
        # Download the file
        response = requests.get(download_url)
        if response.status_code == 200:
            with open(temp_credentials_file, 'wb') as f:
                f.write(response.content)
            
            # Load the credentials from the downloaded file
            credentials = service_account.Credentials.from_service_account_file(
                temp_credentials_file, scopes=DRIVE_SHEETS_SCOPES)
            
            # Clean up the temporary file
            os.remove(temp_credentials_file)
            return credentials
        else:
            print(f"Failed to download credentials from Google Drive: {response.status_code}")
            # Fall back to local file
    except Exception as e:
        print(f"Error downloading credentials from Google Drive: {e}")
        # Fall back to local file
    
    # Fall back to local file if download fails
    if os.path.exists(credentials_file):
        print("Using local credentials file...")
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=DRIVE_SHEETS_SCOPES)
        return credentials
    else:
        raise FileNotFoundError(f"Google Drive credentials file not found: {credentials_file}")

def get_youtube_credentials(channel_id=None, channel_name=None):
    """Get credentials for YouTube API based on channel ID or name."""
    # Channel drive links mapping
    CHANNEL_DRIVE_LINKS = {
        "kidventure quest": "https://drive.google.com/file/d/1-v5o9of59XUCt35xaZmVDOxykY6BdM5H/view?usp=sharing",
        "magicmap tales": "https://drive.google.com/file/d/1av-x5XQ3JYb6b5kHTwqprgdO-MFMtr4U/view?usp=sharing",
        "tiny trailblazers": "https://drive.google.com/file/d/1hJ-bnM7nAlBQolgAwlOAKQK-p5ow2N9h/view?usp=sharing"
    }
    
    # Google Drive link for channel_mappings.json
    MAPPINGS_DRIVE_LINK = "https://drive.google.com/file/d/1B6Fi-9G5qquzeIjLycIzVHvmWY-TCFib/view?usp=sharing"
    
    # Load channel mappings - first try from Google Drive
    mappings = None
    try:
        print("Downloading channel mappings from Google Drive...")
        
        # Convert view URL to direct download URL
        file_id = MAPPINGS_DRIVE_LINK.split('/d/')[1].split('/view')[0]
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # Create temp directory if it doesn't exist
        os.makedirs(TEMP_DIR, exist_ok=True)
        temp_mappings_file = os.path.join(TEMP_DIR, 'temp_channel_mappings.json')
        
        # Download the file
        response = requests.get(download_url)
        if response.status_code == 200:
            with open(temp_mappings_file, 'wb') as f:
                f.write(response.content)
            
            # Load the mappings from the downloaded file
            with open(temp_mappings_file, 'r') as f:
                mappings = json.load(f)
            
            # Clean up the temporary file
            os.remove(temp_mappings_file)
        else:
            print(f"Failed to download channel mappings from Google Drive: {response.status_code}")
    except Exception as e:
        print(f"Error downloading channel mappings from Google Drive: {e}")
    
    # Fall back to local file if download fails
    if mappings is None:
        if os.path.exists(CHANNEL_MAPPINGS_FILE):
            print(f"Using local channel mappings file...")
            with open(CHANNEL_MAPPINGS_FILE, 'r') as f:
                mappings = json.load(f)
        else:
            raise FileNotFoundError(f"Channel mappings file not found: {CHANNEL_MAPPINGS_FILE}")
    
    # Find the correct token file and channel title
    token_file = None
    channel_title = None
    drive_link = None
    
    if channel_id and channel_id in mappings:
        token_file = mappings[channel_id]['token_file']
        channel_title = mappings[channel_id]['title']
        
        # Find matching Google Drive link by channel title
        for name, link in CHANNEL_DRIVE_LINKS.items():
            if name.lower() in channel_title.lower():
                drive_link = link
                break
    elif channel_name:
        # Try to find channel by name (case insensitive)
        for cid, info in mappings.items():
            if channel_name.lower() in info['title'].lower():
                token_file = info['token_file']
                channel_id = cid
                channel_title = info['title']
                
                # Find matching Google Drive link by channel title
                for name, link in CHANNEL_DRIVE_LINKS.items():
                    if name.lower() in channel_title.lower():
                        drive_link = link
                        break
                break
    
    if not channel_title:
        raise ValueError("No matching YouTube channel found.")
    
    # Download credentials from Google Drive instead of using local file
    if drive_link:
        print(f"Downloading credentials for {channel_title} from Google Drive...")
        
        # Convert view URL to direct download URL
        file_id = drive_link.split('/d/')[1].split('/view')[0]
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        
        # Create temp directory if it doesn't exist
        os.makedirs(TEMP_DIR, exist_ok=True)
        temp_token_file = os.path.join(TEMP_DIR, f"{channel_title.replace(' ', '_').lower()}_token.json")
        
        # Download the file
        response = requests.get(download_url)
        if response.status_code == 200:
            with open(temp_token_file, 'wb') as f:
                f.write(response.content)
            
            # Load the credentials from the downloaded file
            with open(temp_token_file, 'r') as f:
                creds_data = json.load(f)
                credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(creds_data)
                
            # Clean up the temporary file
            os.remove(temp_token_file)
            return credentials, channel_id, channel_title
        else:
            raise RuntimeError(f"Failed to download credentials from Google Drive: {response.status_code}")
    elif os.path.exists(token_file):
        # Fallback to local file if it exists
        print(f"Using local credentials for {channel_title}...")
        with open(token_file, 'r') as f:
            creds_data = json.load(f)
            credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(creds_data)
        return credentials, channel_id, channel_title
    else:
        raise FileNotFoundError(f"Could not find credentials for channel: {channel_title}")

def list_available_youtube_channels():
    """List all channels that have saved authentication tokens."""
    if not os.path.exists(CHANNEL_MAPPINGS_FILE):
        print(f"Error: {CHANNEL_MAPPINGS_FILE} not found. Run auth_single_channel.py first.")
        return {}
    
    with open(CHANNEL_MAPPINGS_FILE, 'r') as f:
        mappings = json.load(f)
    
    print("\nAvailable YouTube Channels:")
    print("=" * 60)
    
    for i, (channel_id, info) in enumerate(mappings.items(), 1):
        title = info['title']
        token_file = info['token_file']
        
        # Verify token file exists
        token_exists = os.path.exists(token_file)
        status = "Ready" if token_exists else "Token missing"
        
        print(f"{i}. {title}")
        print(f"   ID: {channel_id}")
        print(f"   Status: {status}")
        print(f"   Token: {os.path.basename(token_file)}")
        print()
    
    return mappings

def select_channel_interactive():
    """Allow user to select a channel interactively."""
    mappings = list_available_youtube_channels()
    
    if not mappings:
        return None, None
    
    # Convert to list for easier indexing
    channels = list(mappings.items())
    
    try:
        choice = int(input("\nEnter the number of the channel to use: "))
        if 1 <= choice <= len(channels):
            selected_channel_id, selected_channel_info = channels[choice-1]
            return selected_channel_id, selected_channel_info['title']
    except ValueError:
        pass
    
    print("Invalid selection.")
    return None, None

def get_spreadsheet_data():
    """Get all data from the Google Spreadsheet."""
    credentials = get_google_drive_credentials()
    sheets_service = build('sheets', 'v4', credentials=credentials)
    
    # Get spreadsheet headers
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=EXISTING_SHEET_ID,
        range='Sheet1!1:1'  # Headers
    ).execute()
    
    headers = result.get('values', [[]])[0]
    
    # Get all spreadsheet data
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=EXISTING_SHEET_ID,
        range='Sheet1!A2:Z1000'  # All data (adjust range as needed)
    ).execute()
    
    rows = result.get('values', [])
    
    # Convert to list of dictionaries with column headers as keys
    data = []
    for row in rows:
        # Pad row with empty strings if it's shorter than headers
        row_padded = row + [''] * (len(headers) - len(row))
        row_dict = {headers[i]: row_padded[i] for i in range(len(headers))}
        data.append(row_dict)
    
    # Also return headers for easy reference
    return {
        'headers': headers,
        'data': data,
        'row_count': len(data)
    }

def update_spreadsheet_structure():
    """Update the spreadsheet to include upload tracking columns if they don't exist."""
    credentials = get_google_drive_credentials()
    sheets_service = build('sheets', 'v4', credentials=credentials)
    
    try:
        # Get the current headers
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=EXISTING_SHEET_ID,
            range='Sheet1!1:1'  # First row (headers)
        ).execute()
        
        headers = result.get('values', [[]])[0]
        
        # Check which columns we need to add
        columns_to_add = []
        for col in UPLOAD_TRACKING_COLUMNS:
            if col not in headers:
                columns_to_add.append(col)
        
        if not columns_to_add:
            print("Spreadsheet already has all required tracking columns.")
            return True
            
        # Add the new columns
        new_headers = headers + columns_to_add
        
        body = {
            'values': [new_headers]
        }
        
        response = sheets_service.spreadsheets().values().update(
            spreadsheetId=EXISTING_SHEET_ID,
            range='Sheet1!1:1',  # First row
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"Updated spreadsheet structure, added columns: {', '.join(columns_to_add)}")
        return True
        
    except Exception as e:
        print(f"Error updating spreadsheet structure: {e}")
        return False

def download_files_from_folder(folder_id, folder_name):
    """Download all files from a Google Drive folder."""
    credentials = get_google_drive_credentials()
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # Create temp folder if it doesn't exist
    folder_path = os.path.join(TEMP_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    try:
        # Get all files in the folder
        query = f"'{folder_id}' in parents and trashed=false"
        results = drive_service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType, size)'
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            print(f"No files found in folder {folder_name}")
            return None
            
        downloaded_files = {}
        
        for file in files:
            file_id = file['id']
            file_name = file['name']
            file_path = os.path.join(folder_path, file_name)
            
            # Skip if file already exists
            if os.path.exists(file_path):
                print(f"File already exists: {file_path}")
                downloaded_files[file_name] = file_path
                continue
                
            try:
                request = drive_service.files().get_media(fileId=file_id)
                
                with open(file_path, 'wb') as f:
                    downloader = MediaIoBaseDownload(f, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                        print(f"Downloading {file_name}: {int(status.progress() * 100)}%")
                
                downloaded_files[file_name] = file_path
                
            except Exception as e:
                print(f"Error downloading {file_name}: {e}")
        
        return downloaded_files
        
    except Exception as e:
        print(f"Error downloading files from folder {folder_name}: {e}")
        return None

def read_text_file(file_path, default=""):
    """Read text content from a file, with a default if file doesn't exist."""
    if not os.path.exists(file_path):
        return default
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return default

def upload_video_to_youtube(video_path, title, description, tags, category="22", 
                          privacy_status="unlisted", credentials=None, channel_title=None):
    """Upload a video to YouTube using the provided credentials."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
        
    if not credentials:
        raise ValueError("No YouTube credentials provided")
    
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
    
    # Prepare tags
    if not isinstance(tags, list):
        # Split comma or space separated tags
        tags = [tag.strip() for tag in tags.replace(',', ' ').split() if tag.strip()]
    
    # Prepare the request body
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category
        },
        'status': {
            'privacyStatus': privacy_status
        }
    }
    
    # Prepare the media upload
    media = MediaFileUpload(video_path, resumable=True,
                           chunksize=1024*1024, mimetype='video/mp4')
    
    # Create the video insert request
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )
    
    video_id = resumable_upload(insert_request, channel_title)
    return video_id

def set_thumbnail(youtube, video_id, thumbnail_path):
    """Set a custom thumbnail for a YouTube video."""
    if not os.path.exists(thumbnail_path):
        print(f"Thumbnail file not found: {thumbnail_path}")
        return False
    
    try:
        # Upload the thumbnail
        media = MediaFileUpload(thumbnail_path, mimetype='image/jpeg')
        
        # Set as video thumbnail
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=media
        ).execute()
        
        print(f"Custom thumbnail set for video ID: {video_id}")
        return True
    
    except Exception as e:
        print(f"Error setting thumbnail: {e}")
        return False

def resumable_upload(insert_request, channel_title=None):
    """Execute the resumable upload with retry logic."""
    response = None
    error = None
    retry = 0
    
    # Identify which channel is being used for the upload
    channel_msg = f" to {channel_title}" if channel_title else ""
    
    while response is None:
        try:
            print(f"Uploading video{channel_msg}...")
            status, response = insert_request.next_chunk()
            if response is not None:
                if 'id' in response:
                    video_id = response['id']
                    print(f"Video successfully uploaded! Video ID: {video_id}")
                    print(f"Video URL: https://www.youtube.com/watch?v={video_id}")
                    return video_id
                else:
                    print(f"Upload failed with unexpected response: {response}")
                    return None
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"
            else:
                print(f"HTTP error {e.resp.status} occurred:\n{e.content}")
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = f"A retriable error occurred: {e}"
            
        if error is not None:
            print(error)
            retry += 1
            if retry > MAX_RETRIES:
                print("No longer attempting to retry.")
                return None
                
            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print(f"Sleeping {sleep_seconds:.1f} seconds and then retrying...")
            time.sleep(sleep_seconds)
            error = None
    
    return None

def update_spreadsheet_row(row_index, video_id, channel_title, status="Yes", error_message=""):
    """Update a specific row in the spreadsheet with upload details."""
    credentials = get_google_drive_credentials()
    sheets_service = build('sheets', 'v4', credentials=credentials)
    
    # First get current headers to know which columns to update
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=EXISTING_SHEET_ID,
        range='Sheet1!1:1'  # Headers
    ).execute()
    
    headers = result.get('values', [[]])[0]
    
    # Find indices for our tracking columns
    column_indices = {}
    for col in UPLOAD_TRACKING_COLUMNS:
        if col in headers:
            column_indices[col] = headers.index(col)
    
    if not column_indices:
        print("Error: Upload tracking columns not found in spreadsheet.")
        return False
    
    # Prepare the update values
    updates = []
    for col, idx in column_indices.items():
        # Calculate the cell reference (A1 notation)
        col_letter = chr(65 + idx)  # A=65, B=66, etc.
        cell_ref = f"Sheet1!{col_letter}{row_index+2}"  # +2 because row_index is 0-based and we skip header
        
        # Determine the value based on column
        if col == 'Upload Status':
            value = status
        elif col == 'Upload Date':
            value = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        elif col == 'YouTube URL':
            value = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
        elif col == 'YouTube Channel':
            value = channel_title or ""
        elif col == 'YouTube Video ID':
            value = video_id or ""
        elif col == 'Error Message':
            value = error_message
        else:
            continue
        
        updates.append({
            'range': cell_ref,
            'values': [[value]]
        })
    
    # Execute the updates
    body = {
        'valueInputOption': 'RAW',
        'data': updates
    }
    
    try:
        response = sheets_service.spreadsheets().values().batchUpdate(
            spreadsheetId=EXISTING_SHEET_ID,
            body=body
        ).execute()
        
        print(f"Updated spreadsheet row {row_index+2} with upload status.")
        return True
    except Exception as e:
        print(f"Error updating spreadsheet: {e}")
        return False

def send_telegram_notification(video_id, title, channel_title, folder_name):
    """Send a notification to Telegram when a video is uploaded."""
    if not TELEGRAM_NOTIFICATIONS_ENABLED:
        return
        
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Create notification message with simplified format to avoid Markdown parsing errors
        message = f"""🚨 Hey Boss! 🍇🌾

Your YouTube farm is blooming beautifully! 🎥✨  
Just spotted some fresh fruits 🍉 — check out this new video we just harvested and uploaded! 🚜📈

📝 Title: {title}
📂 Folder: {folder_name}
📺 Channel: {channel_title}
🔗 Watch here: {video_url}

Your pipeline is working like magic 🪄 — smooth, steady, and strong 💪.  
Let's plant a few more seeds 🌱 and expand the farm — more content, more growth, more wins! 🔥🚀

Stay tuned for the next harvest 🌟  
#FarmStatus #AutomationPower #YouTubeGrowth"""
        
        # Send message to Telegram
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "message_thread_id": TELEGRAM_THREAD_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Telegram notification sent successfully")
        else:
            print(f"⚠️ Telegram notification failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")

def cleanup_downloaded_files(folder_path):
    """Delete downloaded files after successful upload to save disk space."""
    if not os.path.exists(folder_path):
        return
        
    try:
        print(f"Cleaning up downloaded files in {folder_path}")
        shutil.rmtree(folder_path)
        print(f"✅ Successfully deleted temporary files")
    except Exception as e:
        print(f"⚠️ Error cleaning up files: {e}")

def process_folder_for_upload(folder_data, row_index, channel_id=None, channel_name=None):
    """Process a single folder for upload to YouTube."""
    folder_id = folder_data.get('Folder ID', '')
    folder_name = folder_data.get('Subfolder Name', '')
    
    # Skip if already uploaded - but verify YouTube URL exists
    if folder_data.get('Upload Status', '') == 'Yes':
        # Double-check if YouTube URL exists
        if folder_data.get('YouTube URL', ''):
            print(f"Skipping {folder_name}: Already uploaded to YouTube ({folder_data.get('YouTube URL', '')})")
            return True
        else:
            print(f"Warning: {folder_name} marked as uploaded but has no YouTube URL. Will attempt to re-upload.")
    
    print(f"\nProcessing folder: {folder_name} (ID: {folder_id})")
    
    # Download files from the folder
    files = download_files_from_folder(folder_id, folder_name)
    
    if not files:
        error_msg = "Failed to download files from folder."
        update_spreadsheet_row(row_index, None, None, "Failed", error_msg)
        return False
    
    # Check if we have the required files
    if 'video.mp4' not in files:
        error_msg = "No video.mp4 file found in folder."
        update_spreadsheet_row(row_index, None, None, "Failed", error_msg)
        return False
    
    # Extract metadata from text files
    video_path = files.get('video.mp4')
    title = read_text_file(files.get('title.txt', ''), folder_name)
    description = read_text_file(files.get('description.txt', ''), f"Video from {folder_name}")
    tags = read_text_file(files.get('tags.txt', ''), folder_name)
    
    # Get YouTube credentials
    try:
        credentials, actual_channel_id, channel_title = get_youtube_credentials(channel_id, channel_name)
    except Exception as e:
        error_msg = f"Failed to get YouTube credentials: {str(e)}"
        update_spreadsheet_row(row_index, None, None, "Failed", error_msg)
        return False
    
    # Create YouTube API service
    youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
    
    # Upload the video
    try:
        video_id = upload_video_to_youtube(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy_status="public",  # Default to unlisted
            credentials=credentials,
            channel_title=channel_title
        )
        
        if video_id:
            # Set thumbnail if available
            if 'thumbnail.jpg' in files:
                thumbnail_path = files.get('thumbnail.jpg')
                set_thumbnail(youtube, video_id, thumbnail_path)
            
            # Update spreadsheet with success
            update_spreadsheet_row(row_index, video_id, channel_title, "Yes")
            send_telegram_notification(video_id, title, channel_title, folder_name)
            
            # Clean up downloaded files
            folder_path = os.path.join(TEMP_DIR, folder_name)
            cleanup_downloaded_files(folder_path)
            
            return True
        else:
            error_msg = "Upload failed with unknown error."
            update_spreadsheet_row(row_index, None, channel_title, "Failed", error_msg)
            return False
            
    except Exception as e:
        error_msg = f"Upload failed: {str(e)}"
        update_spreadsheet_row(row_index, None, channel_title, "Failed", error_msg)
        return False

def process_unuploaded_videos(channel_id=None, channel_name=None, limit=None, random_selection=False):
    """Process all unuploaded videos from the spreadsheet."""
    # First ensure the spreadsheet has the necessary columns
    if not update_spreadsheet_structure():
        print("Failed to update spreadsheet structure. Aborting.")
        return False
    
    # Get all spreadsheet data
    spreadsheet_data = get_spreadsheet_data()
    
    if not spreadsheet_data:
        print("Failed to get spreadsheet data. Aborting.")
        return False
    
    # Filter for unuploaded videos only
    unuploaded_videos = [
        (i, data) for i, data in enumerate(spreadsheet_data['data'])
        if data.get('Upload Status', '') != 'Yes'
    ]
    
    print(f"Found {len(unuploaded_videos)} unuploaded videos.")
    
    # Apply limit and random selection if specified
    if unuploaded_videos:
        if random_selection and limit:
            # Randomly select videos up to the limit
            if limit > len(unuploaded_videos):
                limit = len(unuploaded_videos)
            
            print(f"Randomly selecting {limit} videos for upload.")
            selected_videos = random.sample(unuploaded_videos, limit)
            selected_videos.sort(key=lambda x: x[0])  # Sort by row index for consistent processing
        else:
            # Take the first N videos based on limit
            selected_videos = unuploaded_videos[:limit] if limit else unuploaded_videos
        
        print(f"Processing {len(selected_videos)} videos{' (limited by --limit)' if limit else ''}.")
        
        success_count = 0
        fail_count = 0
        
        for idx, (row_index, folder_data) in enumerate(selected_videos):
            print(f"\n============================================================")
            print(f"Processing {idx+1}/{len(selected_videos)}: {folder_data.get('Subfolder Name', '')}")
            print(f"============================================================\n")
            
            result = process_folder_for_upload(folder_data, row_index, channel_id, channel_name)
            
            if result:
                success_count += 1
            else:
                fail_count += 1
        
        print(f"\n============================================================")
        print(f"Upload Summary")
        print(f"============================================================")
        print(f"Total processed: {success_count + fail_count}")
        print(f"Successful: {success_count}")
        print(f"Failed: {fail_count}")
        print(f"============================================================\n")
        
        return success_count > 0
    else:
        print("No unuploaded videos found.")
        return False

def print_upload_history():
    """Print a summary of all previously uploaded videos."""
    spreadsheet_data = get_spreadsheet_data()
    
    if not spreadsheet_data:
        print("Failed to get spreadsheet data.")
        return
    
    # Filter for uploaded videos
    uploaded_videos = [
        data for data in spreadsheet_data['data']
        if data.get('Upload Status', '') == 'Yes' and data.get('YouTube URL', '')
    ]
    
    if not uploaded_videos:
        print("No previously uploaded videos found in the spreadsheet.")
        return
    
    print("\n============================================================")
    print("Upload History Summary")
    print("============================================================")
    print(f"Found {len(uploaded_videos)} previously uploaded videos:")
    
    for idx, video in enumerate(uploaded_videos):
        folder_name = video.get('Subfolder Name', 'Unknown')
        channel = video.get('YouTube Channel', 'Unknown')
        url = video.get('YouTube URL', 'No URL')
        upload_date = video.get('Upload Date', 'Unknown date')
        
        print(f"{idx+1}. {folder_name} → {channel} | {url} ({upload_date})")
    
    print("============================================================\n")

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Upload videos from Google Drive to YouTube")
    
    # Channel selection
    channel_group = parser.add_argument_group("Channel Selection")
    channel_group.add_argument("--list-channels", action="store_true", help="List available channels and exit")
    channel_group.add_argument("--channel-id", help="Channel ID to upload to")
    channel_group.add_argument("--channel-name", help="Channel name to upload to (will try to match)")
    
    # Upload options
    upload_group = parser.add_argument_group("Upload Options")
    upload_group.add_argument("--limit", type=int, help="Limit the number of videos to upload")
    upload_group.add_argument("--folder-name", help="Only upload from a specific folder name")
    upload_group.add_argument("--privacy-status", choices=VALID_PRIVACY_STATUSES, default="unlisted",
                            help="Privacy status for uploaded videos")
    upload_group.add_argument("--random", action="store_true", help="Randomly select videos for upload")
    upload_group.add_argument("--upload-history", action="store_true", help="Print upload history and exit")
    
    args = parser.parse_args()
    
    # Create temp directory if it doesn't exist
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Just list channels if requested
    if args.list_channels:
        list_available_youtube_channels()
        return
    
    # Print upload history if requested
    if args.upload_history:
        print_upload_history()
        return
    
    # Process unuploaded videos
    process_unuploaded_videos(
        channel_id=args.channel_id,
        channel_name=args.channel_name,
        limit=args.limit,
        random_selection=args.random
    )

if __name__ == "__main__":
    main()
