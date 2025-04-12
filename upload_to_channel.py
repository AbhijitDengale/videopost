#!/usr/bin/env python3

import os
import sys
import json
import random
import time
import http.client
import httplib2
import argparse
from typing import Any, Dict, List, Optional, Tuple

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

# Constants
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
MAPPINGS_FILE = "channel_mappings.json"
TOKENS_DIR = "channel_tokens"

# Maximum number of times to retry before giving up
MAX_RETRIES = 10

# Always retry when these exceptions are raised
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

def get_channel_mappings():
    """Load channel mappings from file."""
    if not os.path.exists(MAPPINGS_FILE):
        print(f"Error: {MAPPINGS_FILE} not found. Please run auth_channels.py first.")
        sys.exit(1)
        
    with open(MAPPINGS_FILE, 'r') as f:
        return json.load(f)

def list_available_channels():
    """List all channels that have saved authentication tokens."""
    try:
        mappings = get_channel_mappings()
        
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
    except Exception as e:
        print(f"Error listing channels: {e}")
        return {}

def get_youtube_service(token_file):
    """Build a YouTube service object from a token file."""
    if not os.path.exists(token_file):
        print(f"Error: Token file {token_file} not found.")
        return None
        
    try:
        with open(token_file, 'r') as f:
            creds_data = json.load(f)
            credentials = Credentials.from_authorized_user_info(creds_data)
            
        return build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

def get_channel_info(youtube):
    """Get information about the authenticated channel."""
    try:
        request = youtube.channels().list(
            part="snippet,statistics",
            mine=True
        )
        response = request.execute()
        
        if not response.get('items'):
            return None
        
        channel = response['items'][0]
        return {
            'id': channel['id'],
            'title': channel['snippet']['title'],
            'subscriber_count': channel['statistics'].get('subscriberCount', '0'),
            'video_count': channel['statistics'].get('videoCount', '0')
        }
    except Exception as e:
        print(f"Error getting channel info: {e}")
        return None

def initialize_upload(youtube, options):
    """Initialize the video upload and start the upload process."""
    tags = None
    if options.keywords:
        tags = options.keywords.split(",")

    body = {
        'snippet': {
            'title': options.title,
            'description': options.description,
            'tags': tags,
            'categoryId': options.category
        },
        'status': {
            'privacyStatus': options.privacyStatus
        }
    }

    # Call the API's videos.insert method to create and upload the video
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
    )

    return resumable_upload(insert_request)

def resumable_upload(insert_request):
    """Implement an exponential backoff strategy to resume a failed upload."""
    response = None
    error = None
    retry = 0
    
    while response is None:
        try:
            print("Uploading file...")
            status, response = insert_request.next_chunk()
            
            if response is not None:
                if 'id' in response:
                    print(f"Success! Video was uploaded.")
                    print(f"Video ID: {response['id']}")
                    print(f"Video URL: https://www.youtube.com/watch?v={response['id']}")
                    return response['id']
                else:
                    print(f"The upload failed with an unexpected response: {response}")
                    return None
                    
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"A retriable HTTP error {e.resp.status} occurred:\n{e.content}"
            else:
                print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
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

def upload_video_to_channel(channel_id, args):
    """Upload a video to a specific channel using its saved token."""
    # Get channel mappings
    mappings = get_channel_mappings()
    
    if channel_id not in mappings:
        print(f"Error: Channel ID {channel_id} not found in mappings.")
        return False
        
    channel_info = mappings[channel_id]
    token_file = channel_info['token_file']
    
    print(f"Uploading to channel: {channel_info['title']}")
    print(f"Using token file: {token_file}")
    
    # Get YouTube service for this channel
    youtube = get_youtube_service(token_file)
    if not youtube:
        return False
        
    # Verify we're using the correct channel
    current_channel = get_channel_info(youtube)
    if not current_channel:
        print("Error: Could not verify channel information.")
        return False
        
    if current_channel['id'] != channel_id:
        print(f"Warning: Token is for channel '{current_channel['title']}' (ID: {current_channel['id']})")
        print(f"         Expected channel '{channel_info['title']}' (ID: {channel_id})")
        confirm = input("Continue anyway? (y/n): ")
        if confirm.lower() != 'y':
            return False
    
    # Upload the video
    try:
        video_id = initialize_upload(youtube, args)
        if video_id:
            print(f"\nVideo successfully uploaded to {channel_info['title']}!")
            return True
    except Exception as e:
        print(f"Upload failed: {e}")
    
    return False

def select_channel_interactive():
    """Allow user to select a channel interactively."""
    mappings = list_available_channels()
    
    if not mappings:
        return None
        
    # Convert to list for easier indexing
    channels = list(mappings.items())
    
    try:
        choice = int(input("\nEnter the number of the channel to use: "))
        if 1 <= choice <= len(channels):
            selected_channel_id, selected_channel_info = channels[choice-1]
            return selected_channel_id
    except ValueError:
        pass
        
    print("Invalid selection.")
    return None

def main():
    parser = argparse.ArgumentParser(description="Upload videos to specific YouTube channels")
    
    # Required file argument
    parser.add_argument("--file", required=True, help="Video file to upload")
    
    # Channel selection
    channel_group = parser.add_argument_group("Channel Selection")
    channel_group.add_argument("--list-channels", action="store_true", help="List available channels and exit")
    channel_group.add_argument("--channel-id", help="Channel ID to upload to")
    channel_group.add_argument("--channel-name", help="Channel name to upload to (will try to match)")
    
    # Video details
    video_group = parser.add_argument_group("Video Details")
    video_group.add_argument("--title", help="Video title", default="Test Title")
    video_group.add_argument("--description", help="Video description", default="Test Description")
    video_group.add_argument("--category", default="22", help="Numeric video category. See https://developers.google.com/youtube/v3/docs/videoCategories/list")
    video_group.add_argument("--keywords", help="Video keywords, comma separated", default="")
    video_group.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES, default=VALID_PRIVACY_STATUSES[0], help="Video privacy status.")
    
    args = parser.parse_args()
    
    # Just list channels if requested
    if args.list_channels:
        list_available_channels()
        return
    
    # Check if the video file exists
    if not os.path.exists(args.file):
        print(f"Error: The file '{args.file}' does not exist.")
        sys.exit(1)
    
    # Determine which channel to use
    channel_id = None
    
    if args.channel_id:
        # Use specified channel ID
        channel_id = args.channel_id
    elif args.channel_name:
        # Try to find channel by name
        mappings = get_channel_mappings()
        for cid, info in mappings.items():
            if args.channel_name.lower() in info['title'].lower():
                channel_id = cid
                break
        
        if not channel_id:
            print(f"No channel matching '{args.channel_name}' was found.")
            return
    else:
        # Interactive selection
        channel_id = select_channel_interactive()
    
    if not channel_id:
        print("No channel selected. Exiting.")
        return
    
    # Upload the video
    upload_video_to_channel(channel_id, args)

if __name__ == "__main__":
    main()
