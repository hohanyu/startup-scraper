# Startup SG Scraper

A web scraper that extracts startup information from [Startup SG](https://www.startupsg.gov.sg) and uploads it to Google Sheets.

## Features

- Scrapes all startup profiles from the Startup SG directory
- Extracts relevant information from each profile
- Saves data to JSON file
- Uploads data to Google Sheets automatically

## Setup

### 1. Install Dependencies

Create a virtual environment (recommended):

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or: venv\Scripts\activate  # On Windows

pip install -r requirements.txt
```

**Note:** On macOS, you may need to use `python3` and `pip3` instead of `python` and `pip`. If you get an "externally-managed-environment" error, use a virtual environment as shown above.

### 2. Install ChromeDriver

The scraper uses Selenium with Chrome. You need to have ChromeDriver installed:

**macOS (using Homebrew):**
```bash
brew install chromedriver
```

**Or download manually:**
- Download from [ChromeDriver downloads](https://chromedriver.chromium.org/downloads)
- Make sure the version matches your Chrome browser version

### 3. Google Sheets API Setup

To upload data to Google Sheets, you need to set up Google Service Account credentials:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing one)
3. Enable the **Google Sheets API** and **Google Drive API**
4. Go to "Credentials" → "Create Credentials" → "Service Account"
5. Create a service account and download the JSON key file
6. Save the JSON file as `credentials.json` in the project directory
7. Share your Google Spreadsheet with the service account email (found in the JSON file)

## Usage

### Basic Usage

Make sure your virtual environment is activated:

```bash
source venv/bin/activate  # On macOS/Linux
python main.py
```

This will:
- Scrape all startup profiles from Startup SG
- Save data to `startups_data.json`
- Upload to a Google Spreadsheet named "Startup SG Profiles"

### Options

```bash
# Run in headless mode (no browser window)
python main.py --headless

# Limit number of profiles to scrape (for testing)
python main.py --limit 10

# Use custom credentials file
python main.py --credentials path/to/credentials.json

# Use custom spreadsheet name
python main.py --spreadsheet "My Startup Data"

# Save to custom JSON file
python main.py --output my_data.json

# Skip Google Sheets upload (only save to JSON)
python main.py --skip-upload
```

### Example

```bash
# Test with 5 profiles, headless mode
python main.py --headless --limit 5

# Full scrape with custom settings
python main.py --headless --spreadsheet "Startup SG 2024" --output startups_2024.json
```

## Output

The scraper generates:

1. **JSON file** (`startups_data.json` by default): Contains all scraped data in JSON format
2. **Google Spreadsheet**: Uploads the same data to a Google Sheet with formatted headers

## Data Fields

The scraper extracts the following information from each startup profile:

- Profile ID
- URL
- Company Name
- Description
- Industry/Sector
- Location
- Website
- Contact Information (email, phone)
- Funding Information
- And other available fields

## Notes

- The scraper uses Selenium to handle JavaScript-rendered content
- Scraping may take some time depending on the number of profiles
- Be respectful of the website's resources - the scraper includes delays between requests
- Make sure you comply with Startup SG's terms of service and robots.txt

## Troubleshooting

**ChromeDriver issues:**
- Make sure ChromeDriver version matches your Chrome browser version
- Update ChromeDriver: `brew upgrade chromedriver` (macOS)

**Google Sheets upload fails:**
- Verify your `credentials.json` file is in the correct location
- Make sure you've shared the spreadsheet with the service account email
- Check that Google Sheets API and Drive API are enabled in your Google Cloud project

**No profiles found:**
- The website structure may have changed
- Check if the directory page URL is still valid
- Run with `--headless false` to see what's happening in the browser

## License

MIT

