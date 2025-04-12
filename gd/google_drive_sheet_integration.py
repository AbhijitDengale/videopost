import os
import requests
import io
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import datetime
import json
import time

# Define the scopes for Google Drive and Sheets APIs
DRIVE_SHEETS_SCOPES = ['https://www.googleapis.com/auth/drive', 
                      'https://www.googleapis.com/auth/spreadsheets']

# Set the credentials file ID
CREDENTIALS_FILE_ID = '1Hi2I3wlbA6mWtNK_OFYZwEqqRV7fKJgY'

# Existing Google Sheet to update
EXISTING_SHEET_ID = '15QuEt5e2LrrZljaDSp-YbY96nzMmD7MH6TEVsdyrXyw'

# Target folder name
TARGET_FOLDER_NAME = 'GeminiStories'

# Temporary directory for downloaded files
TEMP_DIR = 'temp_files'

def download_credentials_from_gdrive(file_id):
    """Download the credentials file directly from Google Drive link."""
    # Extract file ID from a Google Drive link if full URL provided
    if '/' in file_id:
        file_id = file_id.split('/')[-2]
    
    print(f"Downloading credentials file with ID: {file_id}")
    
    # Direct download URL format for Google Drive
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    try:
        # First attempt - direct download for small files
        response = requests.get(url)
        
        # Check if we got the download warning page (for larger files)
        if 'Content-Disposition' not in response.headers:
            print("Trying to handle large file download...")
            # Handle the download warning page if needed
            confirm_token = None
            for line in response.text.split('\n'):
                if 'confirm=' in line:
                    confirm_token = line.split('confirm=')[1].split('&')[0]
                    break
            
            if confirm_token:
                url = f"{url}&confirm={confirm_token}"
                response = requests.get(url)
            else:
                print("Could not extract confirmation token, may need manual download")
        
        # Save the credentials file
        if response.status_code == 200:
            with open('credentials.json', 'wb') as f:
                f.write(response.content)
            print("Successfully downloaded credentials.json")
            return True
        else:
            print(f"Failed to download file: HTTP {response.status_code}")
            return False
    
    except Exception as e:
        print(f"Error downloading credentials file: {e}")
        print("\nPlease download the file manually from the link and save it as 'credentials.json'")
        return False

def get_credentials():
    """Get credentials using the service account JSON file for Drive and Sheets."""
    # Ensure credentials.json exists
    if not os.path.exists('credentials.json'):
        success = download_credentials_from_gdrive(CREDENTIALS_FILE_ID)
        if not success:
            raise FileNotFoundError("Failed to download credentials.json. Please download it manually.")
    
    # Use service account credentials
    credentials = service_account.Credentials.from_service_account_file(
        'credentials.json', scopes=DRIVE_SHEETS_SCOPES)
    
    return credentials

def find_folder_by_name(folder_name):
    """Find a folder by name in Google Drive."""
    credentials = get_credentials()
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # Search for the folder
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = drive_service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, parents)'
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        print(f"Folder '{folder_name}' not found.")
        return None
    
    print(f"Found folder: {folder_name} (ID: {items[0]['id']})")
    return items[0]

def list_subfolders(folder_id):
    """List all subfolders within a specific folder."""
    credentials = get_credentials()
    drive_service = build('drive', 'v3', credentials=credentials)
    
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = drive_service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, modifiedTime)'
    ).execute()
    
    items = results.get('files', [])
    return items

def list_files_in_folder(folder_id):
    """List all files (non-folders) in a specific folder."""
    credentials = get_credentials()
    drive_service = build('drive', 'v3', credentials=credentials)
    
    query = f"'{folder_id}' in parents and mimeType!='application/vnd.google-apps.folder' and trashed=false"
    results = drive_service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name, mimeType, modifiedTime, size)'
    ).execute()
    
    items = results.get('files', [])
    return items

def download_file_from_drive(file_id, file_name):
    """Download a file from Google Drive."""
    credentials = get_credentials()
    drive_service = build('drive', 'v3', credentials=credentials)
    
    # Ensure temp directory exists
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
    
    # Create a file-like object for the downloaded content
    request = drive_service.files().get_media(fileId=file_id)
    file_path = os.path.join(TEMP_DIR, file_name)
    
    with open(file_path, 'wb') as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print(f"Download {int(status.progress() * 100)}%")
    
    return file_path

def get_files_by_type(files, mime_type_pattern):
    """Get files that match a specific MIME type pattern."""
    return [f for f in files if mime_type_pattern in f.get('mimeType', '')]

def get_existing_folders_from_sheet(spreadsheet_id):
    """Get list of subfolder IDs that are already in the spreadsheet."""
    credentials = get_credentials()
    sheets_service = build('sheets', 'v4', credentials=credentials)
    
    try:
        # Get all values from column A (Folder ID) starting from row 2 (skipping header)
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!A2:A1000'  # Increased range to ensure we get all rows
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            print("No existing folders found in the spreadsheet")
            return []
            
        # Extract folder IDs and ensure they're strings for consistent comparison
        folder_ids = [str(row[0]).strip() for row in values if row and row[0]]
        
        print(f"Found {len(folder_ids)} existing folders in the spreadsheet")
        if folder_ids:
            print(f"First few folder IDs: {folder_ids[:3]}")
        
        return folder_ids
    
    except Exception as e:
        print(f"Error getting existing folders: {e}")
        return []

def get_subfolder_details_with_files():
    """Get comprehensive details of subfolders and their files."""
    # First, find the GeminiStories folder
    gemini_folder = find_folder_by_name(TARGET_FOLDER_NAME)
    
    if not gemini_folder:
        print(f"Cannot list subfolders: {TARGET_FOLDER_NAME} folder not found.")
        return None
    
    gemini_folder_id = gemini_folder['id']
    
    # Get all subfolders
    subfolders = list_subfolders(gemini_folder_id)
    
    if not subfolders:
        print(f"No subfolders found in {TARGET_FOLDER_NAME}.")
        return []
    
    print(f"Found {len(subfolders)} total subfolders in {TARGET_FOLDER_NAME}.")
    
    # Get existing folder IDs from the spreadsheet
    existing_folder_ids = get_existing_folders_from_sheet(EXISTING_SHEET_ID)
    
    # Filter out folders that are already in the spreadsheet
    # Convert IDs to strings to ensure consistent comparison
    new_subfolders = [folder for folder in subfolders if str(folder['id']).strip() not in existing_folder_ids]
    
    print(f"Found {len(new_subfolders)} NEW subfolders to process.")
    
    if not new_subfolders:
        print("No new subfolders to process. All are already in the spreadsheet.")
        return []
    
    # For each new subfolder, get its files
    all_data = []
    
    for subfolder in new_subfolders:
        subfolder_id = subfolder['id']
        subfolder_name = subfolder['name']
        subfolder_modified = subfolder.get('modifiedTime', '')
        
        # Get files in this subfolder
        files = list_files_in_folder(subfolder_id)
        
        # Create an entry for this subfolder
        subfolder_entry = {
            'id': subfolder_id,
            'name': subfolder_name,
            'type': 'folder',
            'parent_folder': TARGET_FOLDER_NAME,
            'modified_time': subfolder_modified,
            'file_count': len(files),
            'files': files
        }
        
        all_data.append(subfolder_entry)
        
        # Print subfolder name and file count
        print(f"  - {subfolder_name}: {len(files)} files")
        
        # Print file names within this subfolder
        if files:
            print(f"    Files in {subfolder_name}:")
            for file in files:
                print(f"      • {file['name']} ({file['mimeType']})")
    
    return all_data

def update_sheet_with_detailed_data(spreadsheet_id, folder_data):
    """Update the spreadsheet with detailed subfolder and file information.
    This version preserves existing data, especially upload history columns."""
    if not folder_data:
        print("No new data to update in the spreadsheet.")
        return None
        
    credentials = get_credentials()
    sheets_service = build('sheets', 'v4', credentials=credentials)
    
    # Get ALL existing data including Upload Status, Upload Date, and YouTube URL columns
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='Sheet1'  # Get the entire sheet to preserve all columns
        ).execute()
        
        existing_values = result.get('values', [])
        
        # If sheet is empty, add a header row
        if not existing_values:
            existing_values = [['Folder ID', 'Subfolder Name', 'Parent Folder', 'Last Modified', 'File Count', 
                              'File Names', 'File Types', 'File IDs', 'Upload Status', 'Upload Date', 'YouTube URL', 'YouTube Channel']]
        
        # Make sure header row is complete, but preserve any additional columns that might exist
        if existing_values and len(existing_values) > 0:
            header = existing_values[0]
            # Ensure our basic columns exist while preserving any others
            basic_columns = ['Folder ID', 'Subfolder Name', 'Parent Folder', 'Last Modified', 'File Count', 
                            'File Names', 'File Types', 'File IDs']
            
            # Check if any basic columns are missing
            for i, col in enumerate(basic_columns):
                if i >= len(header) or header[i] != col:
                    print(f"Fixing header: column {i} should be '{col}' but is '{header[i] if i < len(header) else 'missing'}'")
                    # Ensure header is long enough
                    while len(header) <= i:
                        header.append('')
                    header[i] = col
            
            existing_values[0] = header
        
        print(f"Found {len(existing_values)-1} existing rows in the spreadsheet")
        if existing_values and len(existing_values) > 0:
            print(f"Header has {len(existing_values[0])} columns: {existing_values[0]}")
        
    except Exception as e:
        print(f"Error getting existing data: {e}")
        # Create a new header row with our standard columns
        existing_values = [['Folder ID', 'Subfolder Name', 'Parent Folder', 'Last Modified', 'File Count', 
                          'File Names', 'File Types', 'File IDs', 'Upload Status', 'Upload Date', 'YouTube URL', 'YouTube Channel']]
    
    # Extract header row and existing data rows
    header = existing_values[0] if existing_values else []
    existing_data_rows = existing_values[1:] if len(existing_values) > 1 else []
    
    # Create a dictionary to store existing data by Folder ID for quick lookup
    # This will help us update only what we need to while preserving other columns
    existing_data_dict = {}
    for row in existing_data_rows:
        if row and len(row) > 0:  # Skip empty rows
            folder_id = row[0]  # First column is Folder ID
            existing_data_dict[folder_id] = row
    
    # Prepare the new/updated rows
    updated_rows = []
    updated_folder_ids = set()  # Keep track of folders we've updated
    
    # Process each folder in our new data
    for folder in folder_data:
        folder_id = folder.get('id', '')
        updated_folder_ids.add(folder_id)
        
        # Format modified time
        modified_time = folder.get('modified_time', '')
        if modified_time:
            try:
                dt = datetime.datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
                modified_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        # Get file names, types, and IDs as comma-separated lists
        file_names = ", ".join([f['name'] for f in folder.get('files', [])])
        file_types = ", ".join([f['mimeType'] for f in folder.get('files', [])])
        file_ids = ", ".join([f['id'] for f in folder.get('files', [])])
        
        # Prepare the basic data for this folder (columns A-H)
        new_data = [
            folder_id,
            folder.get('name', ''),
            folder.get('parent_folder', ''),
            modified_time,
            folder.get('file_count', 0),
            file_names,
            file_types,
            file_ids,
        ]
        
        # If this folder already exists in the sheet, preserve any additional columns (Upload Status, Date, URLs, etc.)
        if folder_id in existing_data_dict:
            existing_row = existing_data_dict[folder_id]
            
            # Add any extra columns from the existing row
            # This preserves Upload Status, Upload Date, YouTube URLs, etc.
            for i in range(len(new_data), len(existing_row)):
                if i < len(existing_row):
                    new_data.append(existing_row[i])
                else:
                    new_data.append('')  # Add empty cells if needed
            
            updated_rows.append(new_data)
        else:
            # This is a completely new folder, so we only have basic data
            # Add empty values for any additional columns in the header
            while len(new_data) < len(header):
                new_data.append('')
            updated_rows.append(new_data)
    
    # Add any existing rows that weren't in the new data (to preserve ALL existing data)
    for folder_id, row in existing_data_dict.items():
        if folder_id not in updated_folder_ids:
            updated_rows.append(row)
    
    # Sort rows by folder name for consistency (second column is Subfolder Name)
    updated_rows.sort(key=lambda row: row[1] if len(row) > 1 else '')
    
    # Combine header and data for the final result
    final_values = [header] + updated_rows
    
    # Update only specific columns (A-H) without clearing the entire sheet
    body = {
        'values': final_values
    }
    
    # Update the sheet WITHOUT clearing it first
    response = sheets_service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='Sheet1!A1',  # Start from A1 and update as many cells as needed
        valueInputOption='RAW',
        body=body
    ).execute()
    
    print(f"Spreadsheet updated preserving existing data. {len(updated_rows)} total subfolder entries.")
    print(f"URL: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
    return response

def main():
    try:
        print(f"Starting to gather detailed information about {TARGET_FOLDER_NAME} and its contents...")
        
        # Get detailed information about NEW subfolders and their files
        subfolder_data = get_subfolder_details_with_files()
        
        if not subfolder_data:
            print("\nNo new subfolders to process. Exiting.")
            return
        
        # Update the spreadsheet with the detailed data
        response = update_sheet_with_detailed_data(EXISTING_SHEET_ID, subfolder_data)
        
        if response:
            print("\nProcess completed successfully!")
            print(f"You can view the detailed subfolder and file information at: https://docs.google.com/spreadsheets/d/{EXISTING_SHEET_ID}")
        else:
            print("\nNo changes were made to the spreadsheet.")
        
    except Exception as e:
        print(f"\nError during operation: {e}")
        print("The script encountered an issue. Please check the error message above.")

if __name__ == '__main__':
    main()
