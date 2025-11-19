"""
Google Sheets uploader for startup data
"""

import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict
import os


class GoogleSheetsUploader:
    """Handles uploading data to Google Sheets"""
    
    def __init__(self, credentials_path: str, spreadsheet_name: str):
        """
        Initialize Google Sheets uploader
        
        Args:
            credentials_path: Path to Google Service Account JSON credentials file
            spreadsheet_name: Name of the Google Spreadsheet to create/use
        """
        self.credentials_path = credentials_path
        self.spreadsheet_name = spreadsheet_name
        self.client = None
        self.spreadsheet = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API"""
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_path}\n"
                "Please download your Google Service Account credentials JSON file.\n"
                "See README.md for instructions."
            )
        
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_file(
            self.credentials_path,
            scopes=scope
        )
        
        self.client = gspread.authorize(creds)
        
        # Try to open existing spreadsheet or create new one
        try:
            self.spreadsheet = self.client.open(self.spreadsheet_name)
            print(f"Opened existing spreadsheet: {self.spreadsheet_name}")
        except gspread.exceptions.SpreadsheetNotFound:
            self.spreadsheet = self.client.create(self.spreadsheet_name)
            print(f"Created new spreadsheet: {self.spreadsheet_name}")
            # Share with yourself (optional - remove if not needed)
            # self.spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')
    
    def upload_data(self, data: List[Dict], worksheet_name: str = "Startups"):
        """
        Upload startup data to Google Sheets
        
        Args:
            data: List of dictionaries containing startup information
            worksheet_name: Name of the worksheet to create/use
        """
        if not data:
            print("No data to upload")
            return
        
        # Get or create worksheet
        try:
            worksheet = self.spreadsheet.worksheet(worksheet_name)
            print(f"Using existing worksheet: {worksheet_name}")
        except gspread.exceptions.WorksheetNotFound:
            worksheet = self.spreadsheet.add_worksheet(
                title=worksheet_name,
                rows=1000,
                cols=20
            )
            print(f"Created new worksheet: {worksheet_name}")
        
        # Get all unique keys from all records
        all_keys = set()
        for record in data:
            all_keys.update(record.keys())
        
        # Sort keys for consistent column order
        headers = sorted(list(all_keys))
        
        # Prepare data rows
        rows = [headers]  # Header row
        
        for record in data:
            row = [str(record.get(key, '')) for key in headers]
            rows.append(row)
        
        # Clear existing data and upload
        worksheet.clear()
        worksheet.update('A1', rows)
        
        # Format header row
        worksheet.format('A1:Z1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
        })
        
        print(f"Uploaded {len(data)} records to {self.spreadsheet_name}/{worksheet_name}")
        print(f"Spreadsheet URL: {self.spreadsheet.url}")

