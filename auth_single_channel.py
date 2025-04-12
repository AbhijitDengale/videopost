#!/usr/bin/env python3

import os
import json
import sys
import argparse
import google.oauth2.credentials
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors

# Define scopes needed for the API
SCOPES = [
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl',
    'https://www.googleapis.com/auth/youtube.upload'
]
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
CLIENT_SECRETS_FILE = 'client_secret.json'
TOKENS_DIR = 'channel_tokens'
MAPPINGS_FILE = 'channel_mappings.json'

def get_authenticated_service(token_filename=None):
    """
    Get an authenticated YouTube API service instance.
    
    Args:
        token_filename: Optional filename to load/save credentials
        
    Returns:
        YouTube API service instance and credentials
    """
    credentials = None
    
    # If token filename is provided, try to load from it
    if token_filename and os.path.exists(token_filename):
        try:
            with open(token_filename, 'r') as f:
                creds_data = json.loads(f.read())
                credentials = google.oauth2.credentials.Credentials.from_authorized_user_info(creds_data)
                print(f"Loaded existing credentials from {token_filename}")
        except Exception as e:
            print(f"Error loading stored credentials: {e}")
            credentials = None
    
    if credentials is None:
        # No stored credentials or they're invalid, need to authenticate
        print(f"\n{'='*60}")
        print(f"AUTHENTICATION REQUIRED")
        print(f"{'='*60}")
        print("\nWhen the browser opens:")
        print("1. Sign in with your Google account if prompted")
        print("2. SELECT THE SPECIFIC YOUTUBE CHANNEL you want to authenticate")
        print("3. Grant the requested permissions")
        print("\nAfter completion, the token will be saved for future use.")
        print(f"{'='*60}\n")
        
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, SCOPES)
        credentials = flow.run_local_server(port=8080)
        
        # Save credentials if token_filename is provided
        if token_filename:
            os.makedirs(os.path.dirname(token_filename), exist_ok=True)
            with open(token_filename, 'w') as f:
                f.write(credentials.to_json())
                print(f"Saved credentials to {token_filename}")
    
    return googleapiclient.discovery.build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials), credentials

def get_channel_info(youtube):
    """Get information about the authenticated channel."""
    request = youtube.channels().list(
        part="snippet,statistics",
        mine=True
    )
    response = request.execute()
    
    if not response.get('items'):
        return None
    
    channel = response['items'][0]
    channel_info = {
        'id': channel['id'],
        'title': channel['snippet']['title'],
        'description': channel['snippet'].get('description', ''),
        'subscriber_count': channel['statistics'].get('subscriberCount', '0'),
        'view_count': channel['statistics'].get('viewCount', '0'),
        'video_count': channel['statistics'].get('videoCount', '0')
    }
    
    return channel_info

def update_channel_mapping(channel_id, channel_title, token_file):
    """Update the channel mappings file with the new channel."""
    mappings = {}
    
    # Load existing mappings if available
    if os.path.exists(MAPPINGS_FILE):
        try:
            with open(MAPPINGS_FILE, 'r') as f:
                mappings = json.load(f)
        except:
            pass
    
    # Update or add the new channel
    mappings[channel_id] = {
        'title': channel_title,
        'token_file': token_file
    }
    
    # Save the updated mappings
    with open(MAPPINGS_FILE, 'w') as f:
        json.dump(mappings, f, indent=2)
    
    print(f"Updated channel mappings in {MAPPINGS_FILE}")

def authenticate_channel(channel_name):
    """Authenticate a specific channel and save its token."""
    # Create a sanitized filename from channel name
    safe_name = "".join(c if c.isalnum() else "_" for c in channel_name).lower()
    token_filename = os.path.join(TOKENS_DIR, f"{safe_name}_token.json")
    
    # Authenticate and get channel info
    youtube, credentials = get_authenticated_service(token_filename)
    channel_info = get_channel_info(youtube)
    
    if not channel_info:
        print("Error: Could not retrieve channel information after authentication.")
        return False
    
    # Update channel mappings
    update_channel_mapping(
        channel_info['id'], 
        channel_info['title'], 
        token_filename
    )
    
    print(f"\nSuccessfully authenticated: {channel_info['title']}")
    print(f"Channel ID: {channel_info['id']}")
    print(f"Subscribers: {channel_info['subscriber_count']}")
    print(f"Videos: {channel_info['video_count']}")
    print(f"Token file: {token_filename}")
    
    return True

def main():
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='Authenticate a YouTube channel')
    parser.add_argument('channel_name', help='Name to identify this channel (e.g., "Primary Channel")')
    args = parser.parse_args()
    
    # Check if client_secret.json exists
    if not os.path.exists(CLIENT_SECRETS_FILE):
        print(f"Error: {CLIENT_SECRETS_FILE} not found.")
        sys.exit(1)
    
    # Make sure tokens directory exists
    os.makedirs(TOKENS_DIR, exist_ok=True)
    
    try:
        # Disable OAuthlib's HTTPS verification when running locally
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        
        # Authenticate the channel
        if authenticate_channel(args.channel_name):
            print("\nAuthentication completed successfully!")
        else:
            print("\nAuthentication failed.")
            sys.exit(1)
        
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
