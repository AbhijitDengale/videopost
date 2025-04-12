# Automated YouTube Uploader with GitHub Actions

This guide explains how to set up GitHub Actions to automatically upload videos from Google Drive to multiple YouTube channels on a daily schedule.

## Overview

The GitHub Actions workflow will:
1. Run automatically once per day at 2:00 AM UTC
2. Scan your Google Drive for new videos
3. Randomly select 7-10 videos per channel
4. Upload them to each configured YouTube channel
5. Send Telegram notifications for each successful upload
6. Update the tracking spreadsheet
7. Clean up temporary files after successful uploads

## Required GitHub Secrets

You need to set up the following secrets in your GitHub repository:

### Authentication Secrets

1. `GOOGLE_SERVICE_ACCOUNT` - Your Google Service Account JSON file contents (for Google Drive/Sheets access)
2. `CLIENT_SECRET` - Your OAuth client secret JSON file contents (for YouTube API)

### Channel Configuration Secrets

1. `CHANNEL_TOKEN_NAMES` - Comma-separated list of your channel token names (without .json extension)
   Example: `channel1_token,channel2_token,channel3_token`

2. `YOUTUBE_CHANNEL_NAMES` - Comma-separated list of channel names matching those in channel_mappings.json
   Example: `MagicMap Tales,Tiny Trailblazers,Adventure Seekers`

3. Individual token secrets - For each token name in CHANNEL_TOKEN_NAMES, create a secret with that exact name
   containing the contents of the corresponding token JSON file
   
## Setup Instructions

1. Push your code to a GitHub repository

2. Set up the required secrets:
   - Go to your GitHub repository → Settings → Secrets and variables → Actions
   - Add each required secret as described above

3. Prepare your authentication tokens locally first:
   - Run `auth_single_channel.py` for each channel to generate token files
   - These token files need to be stored as secrets

4. Test the workflow:
   - Go to Actions tab → Select "Daily YouTube Upload" workflow → Run workflow
   - Monitor the run to ensure everything works correctly

## Customization

You can customize the behavior by modifying these files:
- `.github/workflows/daily_youtube_upload.yml` - Change schedule or workflow steps
- `upload_gdrive_videos.py` - Add `--random` parameter to select random videos

## Troubleshooting

If the workflow fails:
1. Check the Actions logs for detailed error messages
2. Verify all secrets are properly configured
3. Ensure token files haven't expired (may need periodic refresh)
4. Check Google Drive permissions and YouTube API quotas

## Manual Trigger

You can manually trigger the workflow at any time by:
1. Going to the Actions tab
2. Selecting "Daily YouTube Upload" workflow
3. Clicking "Run workflow"
