#!/usr/bin/env python3
"""
Process Google Photos Picker Metadata

This script reads JSON metadata files created by the photo-picker.html tool,
downloads the actual images from Google Photos, and uploads them to Azure Storage.
"""

import argparse
import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import requests
from azure.storage.blob import BlobServiceClient, ContentSettings
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent
TOKEN_FILE = SCRIPT_DIR / 'token.json'
AZURE_CONFIG_FILE = SCRIPT_DIR / 'azure-config.json'

# Google Photos API scope
SCOPES = ['https://www.googleapis.com/auth/photospicker.mediaitems.readonly']


def load_azure_config() -> dict:
    """Load Azure Storage configuration from JSON file."""
    if not AZURE_CONFIG_FILE.exists():
        logger.error(f"Azure config file not found: {AZURE_CONFIG_FILE}")
        sys.exit(1)
    
    with open(AZURE_CONFIG_FILE, 'r') as f:
        config = json.load(f)
    
    # Validate required keys
    required_keys = ['storage_account_name', 'storage_account_key', 'container_name']
    missing_keys = [key for key in required_keys if key not in config]
    
    if missing_keys:
        logger.error(f"Azure config missing required keys: {missing_keys}")
        logger.error(f"Config has keys: {list(config.keys())}")
        logger.error(f"Please check {AZURE_CONFIG_FILE}")
        sys.exit(1)
    
    logger.info(f"Loaded Azure config from {AZURE_CONFIG_FILE}")
    return config


def get_google_credentials() -> Credentials:
    """
    Get or refresh Google Photos API credentials.
    
    Returns:
        Credentials object for Google Photos API
    """
    creds = None
    
    # Check if token file exists
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            logger.warning(f"Could not load existing credentials: {e}")
            logger.info("Will delete old token file and require re-authentication")
            TOKEN_FILE.unlink()
            creds = None
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Refreshing expired credentials...")
                creds.refresh(Request())
                
                # Save refreshed credentials
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"Credentials refreshed and saved to {TOKEN_FILE}")
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}")
                logger.info(f"Deleting {TOKEN_FILE} - you'll need to re-authenticate")
                TOKEN_FILE.unlink()
                logger.error("Please run photo-picker.html to authenticate with the correct scope.")
                logger.error("The web app will create the necessary OAuth token.")
                sys.exit(1)
        else:
            logger.error("No valid credentials found.")
            logger.error("")
            logger.error("To authenticate:")
            logger.error("1. Open http://localhost:4000/tools/photo-picker.html in your browser")
            logger.error("2. Click 'Sign in with Google'")
            logger.error("3. Complete the OAuth flow")
            logger.error("4. The token will be saved for this script to use")
            logger.error("")
            logger.error("Note: The browser-based OAuth flow creates the token with the correct scope.")
            sys.exit(1)
    
    return creds


def list_metadata_files_from_azure(azure_config: dict) -> List[str]:
    """
    List all JSON metadata files in Azure Storage.
    
    Args:
        azure_config: Azure Storage configuration
        
    Returns:
        List of blob names (JSON metadata files)
    """
    try:
        storage_account_name = azure_config['storage_account_name']
        storage_account_key = azure_config['storage_account_key']
        container_name = azure_config['container_name']
        
        # Create blob service client
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=storage_account_key
        )
        
        container_client = blob_service_client.get_container_client(container_name)
        
        # List all JSON files
        json_blobs = []
        for blob in container_client.list_blobs():
            if blob.name.endswith('.json'):
                json_blobs.append(blob.name)
        
        logger.info(f"Found {len(json_blobs)} JSON metadata file(s) in Azure Storage")
        return json_blobs
        
    except Exception as e:
        logger.error(f"Error listing metadata files from Azure: {e}")
        return []


def download_metadata_from_azure(blob_name: str, azure_config: dict) -> Optional[Dict]:
    """
    Download a JSON metadata file from Azure Storage.
    
    Args:
        blob_name: Name of the blob to download
        azure_config: Azure Storage configuration
        
    Returns:
        Metadata dictionary or None if failed
    """
    try:
        storage_account_name = azure_config['storage_account_name']
        storage_account_key = azure_config['storage_account_key']
        container_name = azure_config['container_name']
        
        # Create blob service client
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=storage_account_key
        )
        
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        # Download blob content
        blob_data = blob_client.download_blob().readall()
        metadata = json.loads(blob_data)
        
        logger.info(f"Downloaded metadata: {blob_name}")
        return metadata
        
    except Exception as e:
        logger.error(f"Error downloading metadata from Azure: {e}")
        return None


def download_image_from_google_photos(download_url: str, creds: Credentials) -> Optional[bytes]:
    """
    Download an image from Google Photos using the download URL.
    
    Args:
        download_url: The download URL from the metadata
        creds: Google API credentials
        
    Returns:
        Image data as bytes or None if failed
    """
    try:
        headers = {'Authorization': f'Bearer {creds.token}'}
        
        logger.info(f"Downloading image from Google Photos...")
        response = requests.get(download_url, headers=headers)
        response.raise_for_status()
        
        logger.info(f"Successfully downloaded image ({len(response.content)} bytes)")
        return response.content
        
    except Exception as e:
        logger.error(f"Error downloading image from Google Photos: {e}")
        return None


def upload_image_to_azure(
    image_data: bytes,
    blob_name: str,
    azure_config: dict,
    content_type: str = 'image/jpeg'
) -> bool:
    """
    Upload image data to Azure Blob Storage.
    
    Args:
        image_data: Image data as bytes
        blob_name: Name for the blob
        azure_config: Azure Storage configuration
        content_type: MIME type of the image
        
    Returns:
        True if successful, False otherwise
    """
    try:
        storage_account_name = azure_config['storage_account_name']
        storage_account_key = azure_config['storage_account_key']
        container_name = azure_config['container_name']
        
        # Create blob service client
        account_url = f"https://{storage_account_name}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(
            account_url=account_url,
            credential=storage_account_key
        )
        
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )
        
        # Upload blob
        blob_client.upload_blob(
            image_data,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type)
        )
        
        blob_url = blob_client.url
        logger.info(f"Successfully uploaded image to Azure: {blob_url}")
        return True
        
    except Exception as e:
        logger.error(f"Error uploading image to Azure: {e}")
        return False


def process_picker_session_with_token(session_id: str, access_token: str, azure_config: dict, custom_filename: Optional[str] = None) -> bool:
    """
    Process a Picker session using an access token: fetch media items and upload them to Azure.
    
    Args:
        session_id: The Picker session ID
        access_token: OAuth access token
        azure_config: Azure Storage configuration
        custom_filename: Optional custom filename to use instead of original
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing Picker Session: {session_id}")
    logger.info(f"Using access token from session file")
    if custom_filename:
        logger.info(f"Custom filename: {custom_filename}")
    logger.info(f"{'='*60}")
    
    try:
        # Fetch media items from the session using the access token
        media_items = fetch_session_media_items_with_token(session_id, access_token)
        
        if not media_items:
            logger.warning("No media items found in session")
            return False
        
        logger.info(f"Found {len(media_items)} media item(s) in session")
        
        # Process each media item
        successful = 0
        failed = 0
        
        for i, item in enumerate(media_items, 1):
            # Log the full item structure to understand what we got
            logger.info(f"\nMedia item {i} structure: {json.dumps(item, indent=2)}")
            
            # Extract data from the nested mediaFile object
            media_file = item.get('mediaFile', {})
            original_filename = media_file.get('filename', f'photo-{i}.jpg')
            
            # Use custom filename if provided, otherwise use original
            filename = custom_filename if custom_filename else original_filename
            
            download_url = media_file.get('baseUrl')
            mime_type = media_file.get('mimeType', 'image/jpeg')
            
            logger.info(f"\n[{i}/{len(media_items)}] Processing: {filename}")
            if custom_filename:
                logger.info(f"  Original: {original_filename}")
                logger.info(f"  Custom: {filename}")
            
            if not download_url:
                logger.error("No baseUrl found for media item")
                failed += 1
                continue
            
            # Download image using access token
            download_url_with_param = f"{download_url}=d"
            image_data = download_image_with_token(download_url_with_param, access_token)
            
            if not image_data:
                failed += 1
                continue
            
            # Upload to Azure
            if upload_image_to_azure(image_data, filename, azure_config, mime_type):
                successful += 1
            else:
                failed += 1
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"SESSION PROCESSING COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total items: {len(media_items)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        
        return failed == 0
        
    except Exception as e:
        logger.error(f"Error processing session: {e}")
        return False


def fetch_session_media_items_with_token(session_id: str, access_token: str) -> List[Dict]:
    """
    Fetch all media items from a Picker session using an access token.
    
    Args:
        session_id: The Picker session ID
        access_token: OAuth access token
        
    Returns:
        List of media item dictionaries
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        base_url = 'https://photospicker.googleapis.com/v1/mediaItems'
        
        all_items = []
        page_token = None
        
        while True:
            # Build query parameters
            params = {'sessionId': session_id}
            if page_token:
                params['pageToken'] = page_token
            
            logger.info(f"Fetching media items from: {base_url}?sessionId={session_id}")
            
            response = requests.get(base_url, headers=headers, params=params)
            
            if not response.ok:
                logger.error(f"HTTP {response.status_code}: {response.reason}")
                try:
                    error_data = response.json()
                    logger.error(f"Error response: {json.dumps(error_data, indent=2)}")
                except:
                    logger.error(f"Error response: {response.text}")
                
                # Check if session exists by querying session status
                logger.info("Checking session status...")
                session_url = f'https://photospicker.googleapis.com/v1/sessions/{session_id}'
                session_response = requests.get(session_url, headers=headers)
                if session_response.ok:
                    session_data = session_response.json()
                    logger.info(f"Session status: {json.dumps(session_data, indent=2)}")
                    
                    # Check for pickup token or other properties
                    if 'pickupToken' in session_data:
                        logger.info(f"Found pickup token: {session_data['pickupToken']}")
                        logger.error("This session uses a pickup token - you may need to use the Library API instead")
                    
                    if not session_data.get('mediaItemsSet'):
                        logger.error("Session exists but mediaItemsSet is false - user may not have completed selection")
                    else:
                        logger.error("Session shows mediaItemsSet=true but /mediaItems endpoint returns 404")
                        logger.error("This may be a limitation of the Picker API - it might not support listing media items")
                else:
                    logger.error(f"Session not found or expired (HTTP {session_response.status_code})")
                
                response.raise_for_status()
            
            data = response.json()
            items = data.get('mediaItems', [])
            all_items.extend(items)
            
            logger.info(f"Fetched {len(items)} items (total: {len(all_items)})")
            
            page_token = data.get('nextPageToken')
            if not page_token:
                break
        
        return all_items
        
    except Exception as e:
        logger.error(f"Error fetching session media items: {e}")
        return []


def download_image_with_token(download_url: str, access_token: str) -> Optional[bytes]:
    """
    Download an image from Google Photos using an access token.
    
    Args:
        download_url: The download URL with parameters
        access_token: OAuth access token
        
    Returns:
        Image data as bytes or None if failed
    """
    try:
        headers = {'Authorization': f'Bearer {access_token}'}
        
        logger.info(f"Downloading image from Google Photos...")
        response = requests.get(download_url, headers=headers)
        response.raise_for_status()
        
        logger.info(f"Successfully downloaded image ({len(response.content)} bytes)")
        return response.content
        
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None


def process_picker_session(session_id: str, azure_config: dict, creds: Credentials) -> bool:
    """
    Process a Picker session: fetch media items and upload them to Azure.
    
    Args:
        session_id: The Picker session ID
        azure_config: Azure Storage configuration
        creds: Google API credentials
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Processing Picker Session: {session_id}")
    logger.info(f"{'='*60}")
    
    try:
        # Fetch media items from the session
        media_items = fetch_session_media_items(session_id, creds)
        
        if not media_items:
            logger.warning("No media items found in session")
            return False
        
        logger.info(f"Found {len(media_items)} media item(s) in session")
        
        # Process each media item
        successful = 0
        failed = 0
        
        for i, item in enumerate(media_items, 1):
            filename = item.get('filename', f'photo-{i}.jpg')
            download_url = item.get('baseUrl')
            mime_type = item.get('mimeType', 'image/jpeg')
            
            logger.info(f"\n[{i}/{len(media_items)}] Processing: {filename}")
            
            if not download_url:
                logger.error("No baseUrl found for media item")
                failed += 1
                continue
            
            # Download image
            download_url_with_param = f"{download_url}=d"
            image_data = download_image_from_google_photos(download_url_with_param, creds)
            
            if not image_data:
                failed += 1
                continue
            
            # Upload to Azure
            if upload_image_to_azure(image_data, filename, azure_config, mime_type):
                successful += 1
            else:
                failed += 1
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"SESSION PROCESSING COMPLETE")
        logger.info(f"{'='*60}")
        logger.info(f"Total items: {len(media_items)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        
        return failed == 0
        
    except Exception as e:
        logger.error(f"Error processing session: {e}")
        return False


def fetch_session_media_items(session_id: str, creds: Credentials) -> List[Dict]:
    """
    Fetch all media items from a Picker session.
    
    Args:
        session_id: The Picker session ID
        creds: Google API credentials
        
    Returns:
        List of media item dictionaries
    """
    try:
        headers = {'Authorization': f'Bearer {creds.token}'}
        base_url = 'https://photospicker.googleapis.com/v1/mediaItems'
        
        all_items = []
        page_token = None
        
        while True:
            # Build query parameters
            params = {'sessionId': session_id}
            if page_token:
                params['pageToken'] = page_token
            
            logger.info(f"Fetching media items from: {base_url}?sessionId={session_id}")
            
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('mediaItems', [])
            all_items.extend(items)
            
            logger.info(f"Fetched {len(items)} items (total: {len(all_items)})")
            
            page_token = data.get('nextPageToken')
            if not page_token:
                break
        
        return all_items
        
    except Exception as e:
        logger.error(f"Error fetching session media items: {e}")
        return []


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='Process Google Photos Picker sessions and upload images to Azure'
    )
    parser.add_argument(
        '--session-id',
        help='Process a specific Picker session ID'
    )
    parser.add_argument(
        '--session-file',
        help='Process a session from a JSON file in Azure Storage (e.g., picker-session-123456.json)'
    )
    parser.add_argument(
        '--list-sessions',
        action='store_true',
        help='List all session files in Azure Storage'
    )
    
    args = parser.parse_args()
    
    # Load Azure configuration
    azure_config = load_azure_config()
    
    # List sessions mode
    if args.list_sessions:
        session_files = list_metadata_files_from_azure(azure_config)
        session_files = [f for f in session_files if f.startswith('picker-session-')]
        if not session_files:
            logger.info("No session files found in Azure Storage")
            return
        logger.info("\nPicker session files in Azure Storage:")
        for i, blob_name in enumerate(session_files, 1):
            logger.info(f"  {i}. {blob_name}")
        return
    
    # Determine session ID and access token
    session_id = None
    access_token = None
    custom_filename = None
    
    if args.session_id:
        session_id = args.session_id
        # No access token available, will need credentials
        creds = get_google_credentials()
    elif args.session_file:
        # Read session ID and access token from file
        metadata = download_metadata_from_azure(args.session_file, azure_config)
        if metadata:
            session_id = metadata.get('sessionId')
            access_token = metadata.get('accessToken')
            custom_filename = metadata.get('customFilename')  # Extract custom filename
            if not session_id:
                logger.error(f"No sessionId found in {args.session_file}")
                sys.exit(1)
            if not access_token:
                logger.error(f"No accessToken found in {args.session_file}")
                sys.exit(1)
            logger.info("Found access token in session file - will use it instead of credentials")
            if custom_filename:
                logger.info(f"Found custom filename in session file: {custom_filename}")
        else:
            sys.exit(1)
        creds = None  # Don't need credentials when we have access token
    else:
        logger.error("Please provide either --session-id or --session-file")
        logger.info("Use --list-sessions to see available session files")
        sys.exit(1)
    
    # Process the session
    logger.info(f"Processing Picker session: {session_id}")
    
    if access_token:
        # Use the access token from the session file
        success = process_picker_session_with_token(session_id, access_token, azure_config, custom_filename)
    else:
        # Use credentials (requires valid token.json)
        success = process_picker_session(session_id, azure_config, creds)
    
    if success:
        logger.info("\n✓ Successfully processed Picker session")
    else:
        logger.error("\n✗ Failed to process Picker session")
        sys.exit(1)


if __name__ == '__main__':
    main()
