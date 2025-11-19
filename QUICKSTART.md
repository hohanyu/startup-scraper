# Quick Start Guide

## 1. Install Dependencies

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

**Note:** Always activate the virtual environment before running the scraper:
```bash
source venv/bin/activate
```

## 2. Install ChromeDriver

**macOS:**
```bash
brew install chromedriver
```

**Or download from:** https://chromedriver.chromium.org/downloads

Make sure ChromeDriver version matches your Chrome browser version.

## 3. Set Up Google Sheets (Optional)

If you want to upload to Google Sheets:

1. Go to https://console.cloud.google.com/
2. Create a project
3. Enable **Google Sheets API** and **Google Drive API**
4. Create a Service Account and download the JSON key
5. Save it as `credentials.json` in this directory
6. Share your Google Spreadsheet with the service account email (found in the JSON)

## 4. Run the Scraper

### Test with a few profiles:
```bash
python main.py --headless --limit 5 --skip-upload
```

### Full scrape:
```bash
python main.py --headless
```

### With Google Sheets upload:
```bash
python main.py --headless --spreadsheet "My Startup Data"
```

## Output

- **JSON file**: `startups_data.json` (default)
- **Google Spreadsheet**: If credentials are set up

## Troubleshooting

**ChromeDriver not found:**
- Make sure ChromeDriver is in your PATH
- Or specify the path: `export PATH=$PATH:/path/to/chromedriver`

**No profiles found:**
- The website structure may have changed
- Try running without `--headless` to see what's happening

