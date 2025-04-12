# Google Drive and Sheets Integration

This script lists all folders in your Google Drive and creates a Google Sheet containing their names and IDs.

## Prerequisites

- Python 3.6 or higher
- Google account with access to Google Drive and Google Sheets
- Google API credentials (OAuth client ID)

## Setup

1. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

2. Download your credentials file from the link provided and save it as `credentials.json` in the same directory as the script:
   - Link: https://drive.google.com/file/d/1l0SPInfFc3_JgJ3DYetXSq-yZunoEhZm/view?usp=sharing

3. Run the script:
   ```
   python google_drive_sheet_integration.py
   ```

4. The first time you run the script, it will open a browser window asking you to authorize the application to access your Google Drive and Sheets. After authorization, the script will save a token for future use.

## What the Script Does

1. Lists all folders in the root of your Google Drive
2. Creates a new Google Sheet with a list of all these folders
3. Outputs the URL of the newly created spreadsheet

## Troubleshooting

- If you encounter authentication issues, delete the `token.pickle` file and run the script again.
- Make sure your credentials file is named `credentials.json` and is in the same directory as the script.
