"""
Main script to scrape Startup SG profiles and upload to Google Sheets
"""

import argparse
import json
import os
from scraper import StartupSGScraper
from sheets_uploader import GoogleSheetsUploader


def main():
    parser = argparse.ArgumentParser(
        description='Scrape Startup SG profiles and upload to Google Sheets'
    )
    parser.add_argument(
        '--credentials',
        type=str,
        default='credentials.json',
        help='Path to Google Service Account credentials JSON file'
    )
    parser.add_argument(
        '--spreadsheet',
        type=str,
        default='Startup SG Profiles',
        help='Name of the Google Spreadsheet'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of profiles to scrape (for testing)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='startups_data.json',
        help='Output JSON file to save scraped data'
    )
    parser.add_argument(
        '--skip-upload',
        action='store_true',
        help='Skip uploading to Google Sheets (only save to JSON)'
    )
    
    args = parser.parse_args()
    
    scraper = None
    try:
        # Initialize scraper
        print("Initializing scraper...")
        scraper = StartupSGScraper(headless=args.headless)
        
        # Get all startup URLs
        print("\n" + "="*50)
        print("Step 1: Fetching all startup profile URLs...")
        print("="*50)
        urls = scraper.get_all_startup_urls()
        
        if not urls:
            print("No startup URLs found. Exiting.")
            return
        
        print(f"Found {len(urls)} startup profiles")
        
        # Limit if specified
        if args.limit:
            urls = urls[:args.limit]
            print(f"Limited to {args.limit} profiles for testing")
        
        # Scrape each profile
        print("\n" + "="*50)
        print("Step 2: Scraping startup profiles...")
        print("="*50)
        
        all_data = []
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] Processing: {url}")
            data = scraper.scrape_profile(url)
            if data:
                all_data.append(data)
            else:
                print(f"  Failed to scrape {url}")
        
        print(f"\nSuccessfully scraped {len(all_data)} out of {len(urls)} profiles")
        
        # Save to JSON file
        print("\n" + "="*50)
        print("Step 3: Saving data to JSON file...")
        print("="*50)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {args.output}")
        
        # Upload to Google Sheets
        if not args.skip_upload:
            print("\n" + "="*50)
            print("Step 4: Uploading to Google Sheets...")
            print("="*50)
            try:
                uploader = GoogleSheetsUploader(
                    credentials_path=args.credentials,
                    spreadsheet_name=args.spreadsheet
                )
                uploader.upload_data(all_data)
                print("\n✓ Upload complete!")
            except FileNotFoundError as e:
                print(f"\n✗ Error: {e}")
                print("Skipping Google Sheets upload. Data saved to JSON file.")
            except Exception as e:
                print(f"\n✗ Error uploading to Google Sheets: {e}")
                print("Data saved to JSON file.")
        else:
            print("\nSkipping Google Sheets upload (--skip-upload flag set)")
        
        print("\n" + "="*50)
        print("Scraping complete!")
        print("="*50)
        
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if scraper:
            scraper.close()


if __name__ == "__main__":
    main()

