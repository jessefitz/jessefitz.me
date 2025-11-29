# Google Photos Picker - Azure Uploader

A web-based photo picker tool that allows you to select photos from Google Photos and upload them to Azure Blob Storage with custom filenames.

## Overview

This tool uses the Google Photos Picker API to provide a visual interface for selecting photos, then automatically downloads and uploads them to Azure Storage. It consists of two components:

1. **photo-picker.html** - Browser-based UI for selecting photos
2. **process_picker_metadata.py** - Python script for downloading and uploading

## Features

- ✅ Visual photo selection using Google Photos Picker
- ✅ OAuth 2.0 authentication with Google
- ✅ Custom filename support (with original filename as default)
- ✅ Automatic upload to Azure Blob Storage
- ✅ Session-based workflow (browser + server)
- ✅ Detailed activity logging
- ✅ Support for multiple image formats

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Required packages:
- `requests` - HTTP client
- `azure-storage-blob` - Azure Blob Storage SDK
- `google-auth` - Google OAuth authentication
- `google-auth-oauthlib` - OAuth flow helpers

### 2. Configure Azure Storage

Create `tools/azure-config.json`:

```json
{
  "storage_account_name": "yourstorageaccount",
  "storage_account_key": "your-storage-account-key",
  "container_name": "images"
}
```

> **Note:** This file is excluded from version control. Never commit credentials to the repository.

### 3. Configure Google OAuth

Ensure `tools/google-client-secret.json` exists with your OAuth 2.0 client configuration:

```json
{
  "web": {
    "client_id": "your-client-id.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "your-client-secret",
    "redirect_uris": ["http://localhost:4000/tools/photo-picker.html"]
  }
}
```

**Required OAuth Scope:**
- `https://www.googleapis.com/auth/photospicker.mediaitems.readonly`

### 4. Enable Azure CORS (One-time Setup)

Run the CORS configuration script to allow browser uploads:

```powershell
.\enable-azure-cors.ps1
```

Or manually configure CORS in Azure Portal to allow:
- **Allowed Origins:** `http://localhost:4000`
- **Allowed Methods:** `PUT, GET`
- **Allowed Headers:** `*`

## Usage

### Step 1: Start Your Jekyll Server

```bash
bundle exec jekyll serve --livereload
```

The site will be available at `http://localhost:4000`

### Step 2: Open the Photo Picker

Navigate to: `http://localhost:4000/tools/photo-picker.html`

### Step 3: Select and Upload Photos

1. Click **"Sign in with Google"**
   - Authenticate with your Google account
   - Grant photo picker permissions

2. Click **"Select Photos from Google Photos"**
   - Browser window opens with Google Photos Picker
   - Select one or more photos
   - Click "Done" in the picker

3. **Enter Custom Filename**
   - A prompt appears showing the original filename
   - Modify the filename or keep the original
   - Click "OK"

4. Click **"Upload to Azure"**
   - Session metadata (including access token and custom filename) saved to Azure
   - Note the session filename shown in the log

### Step 4: Process the Session

Run the Python script to download and upload:

```bash
cd tools
python process_picker_metadata.py --session-file picker-session-XXXXX.json
```

Replace `XXXXX` with the timestamp from Step 3.

### Alternative: List All Sessions

To see all available session files:

```bash
python process_picker_metadata.py --list-sessions
```

## How It Works

### Browser Flow (photo-picker.html)

1. **Authentication:** OAuth 2.0 implicit flow with Google
2. **Session Creation:** Creates a Picker session via REST API
3. **Photo Selection:** Opens Google Photos Picker in popup window
4. **Session Polling:** Polls session endpoint until user completes selection
5. **Filename Prompt:** Fetches media item details and prompts for custom filename
6. **Metadata Upload:** Saves session ID, access token, and custom filename to Azure

### Server Flow (process_picker_metadata.py)

1. **Read Session:** Downloads session metadata from Azure Blob Storage
2. **Fetch Media Items:** Calls Picker API `/mediaItems` endpoint with session ID
3. **Download Images:** Uses `baseUrl` from media items to download full-resolution images
4. **Upload to Azure:** Uploads images to Azure Blob Storage with custom or original filename

### Data Flow

```
Browser                    Google Photos API              Azure Blob Storage
   |                              |                               |
   |-- Authenticate ------------->|                               |
   |<-- Access Token -------------|                               |
   |                              |                               |
   |-- Create Session ----------->|                               |
   |<-- Session ID + Picker URL --|                               |
   |                              |                               |
   |-- User selects photos ------>|                               |
   |<-- Selection complete -------|                               |
   |                              |                               |
   |-- Fetch media items -------->|                               |
   |<-- Media item details -------|                               |
   |                              |                               |
   |-- Upload session metadata ----------------------->|          |
   |                              |                    |          |
                                                       |          |
Python Script                                          |          |
   |                              |                    |          |
   |-- Download session metadata ------------------->|          |
   |<-- Session ID + Access Token -------------------|          |
   |                              |                               |
   |-- Fetch media items -------->|                               |
   |<-- baseUrl + filename -------|                               |
   |                              |                               |
   |-- Download image ----------->|                               |
   |<-- Image bytes --------------|                               |
   |                              |                               |
   |-- Upload image ------------------------------------------>|   |
```

## File Naming

- **Default:** Uses original filename from Google Photos (e.g., `PXL_20251127_150928736~3.jpg`)
- **Custom:** User can specify any filename in the browser prompt
- **Uploaded as:** Exact filename chosen by user (original or custom)

## Command-Line Reference

### Process a Session File

```bash
python process_picker_metadata.py --session-file picker-session-1234567890.json
```

### List All Sessions

```bash
python process_picker_metadata.py --list-sessions
```

### Process by Session ID (Advanced)

```bash
python process_picker_metadata.py --session-id abc123-def456-ghi789
```

> **Note:** This mode requires a valid `token.json` file with Picker API credentials.

## Session Metadata Format

Session files stored in Azure contain:

```json
{
  "sessionId": "abc123-def456-ghi789",
  "accessToken": "ya29.a0...",
  "customFilename": "my-photo.jpg",
  "pickerApiEndpoint": "https://photospicker.googleapis.com/v1/sessions",
  "createdAt": "2025-11-29T12:34:56.789Z",
  "note": "Process this session using process_picker_metadata.py"
}
```

## Error Handling

The tool handles:

- **CORS errors:** Properly configured Azure CORS required
- **Authentication failures:** Automatic re-authentication flow
- **Session expiration:** Sessions expire after ~1 hour
- **Network errors:** Retry logic and detailed error messages
- **Missing files:** Validates all required configuration files
- **API errors:** Detailed logging of Google API responses

## Security Notes

- ✅ `google-client-secret.json` - Excluded from version control
- ✅ `azure-config.json` - Excluded from version control
- ✅ `token.json` - Excluded from version control
- ✅ OAuth tokens - Short-lived, stored in session files
- ✅ Access tokens - Passed from browser to Python script securely via Azure
- ⚠️ Session files in Azure contain access tokens (expire after ~1 hour)

## Troubleshooting

### "No baseUrl found for media item"

- Ensure the media item structure includes `mediaFile.baseUrl`
- Check that the session hasn't expired
- Verify the Picker API response structure

### "CORS error" in browser

- Run `enable-azure-cors.ps1` to configure CORS
- Verify CORS settings in Azure Portal
- Ensure origin is `http://localhost:4000`

### "Session not found or expired"

- Sessions expire after creation
- Create a new session by re-running the photo picker
- Don't reuse old session files

### "OAuth authentication failed"

- Delete `token.json` and re-authenticate in browser
- Verify `google-client-secret.json` is valid
- Check redirect URI matches `http://localhost:4000/tools/photo-picker.html`

### "Azure configuration missing"

- Ensure `azure-config.json` exists in `tools/` directory
- Verify all required keys are present:
  - `storage_account_name`
  - `storage_account_key`
  - `container_name`

## Migration from download_and_upload.py

The old `download_and_upload.py` script has been replaced by this picker-based workflow. Key differences:

| Old Script | New Workflow |
|------------|--------------|
| Command-line arguments | Visual photo picker |
| Library API | Picker API |
| Album + filename lookup | Direct selection |
| Manual media item IDs | Automatic session handling |
| Single file at a time | Multiple files supported |

## Files

- `photo-picker.html` - Web interface for photo selection
- `process_picker_metadata.py` - Python script for download/upload
- `azure-config.json` - Azure Storage credentials (not in repo)
- `google-client-secret.json` - OAuth client config (not in repo)
- `enable-azure-cors.ps1` - PowerShell script for CORS setup
- `requirements.txt` - Python dependencies

## API Documentation

- [Google Photos Picker API](https://developers.google.com/photos/picker/guides/get-started-picker-api)
- [Azure Blob Storage REST API](https://learn.microsoft.com/en-us/rest/api/storageservices/blob-service-rest-api)

## License

Part of jessefitz.me personal website project.

