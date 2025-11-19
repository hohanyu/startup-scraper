"""
Web scraper for Startup SG profiles
Scrapes startup information from https://www.startupsg.gov.sg and uploads to Google Sheets
"""

import time
import json
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


class StartupSGScraper:
    """Scraper for Startup SG directory and profiles"""
    
    def __init__(self, headless: bool = True):
        """Initialize the scraper with Selenium WebDriver"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.base_url = "https://www.startupsg.gov.sg"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def get_all_startup_urls(self) -> List[str]:
        """
        Extract all startup profile URLs from the directory page
        Returns list of profile URLs
        """
        print("Fetching directory page...")
        self.driver.get(f"{self.base_url}/directory/startups")
        
        # Wait for page to load and JavaScript to execute
        time.sleep(5)
        
        # Try to find API endpoint or data in JavaScript
        profile_urls = set()
        
        # Check if there's an API endpoint we can call directly
        try:
            # Try to get profile IDs from JavaScript variables
            profile_ids = self.driver.execute_script("""
                // Look for profile data in window object
                if (window.__NUXT__ && window.__NUXT__.data) {
                    return window.__NUXT__.data;
                }
                // Look for any data structures with profile IDs
                return null;
            """)
            
            if profile_ids:
                # Extract IDs and build URLs
                ids = self._extract_ids_from_data(profile_ids)
                for profile_id in ids:
                    profile_urls.add(f"{self.base_url}/profiles/{profile_id}")
        except Exception as e:
            print(f"Could not extract from JavaScript: {e}")
        
        # Scroll to load more content (if pagination/infinite scroll)
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scrolls = 20  # Increased for more scrolling
        
        print("Scrolling to load all content...")
        while scroll_attempts < max_scrolls:
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Check if new content loaded
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1
            print(f"  Scroll {scroll_attempts}/{max_scrolls}, height: {new_height}")
        
        # Try to find all profile links in the DOM
        try:
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href")
                if href and "/profiles/" in href:
                    # Normalize URL
                    if href.startswith("/"):
                        href = f"{self.base_url}{href}"
                    profile_urls.add(href)
        except Exception as e:
            print(f"Error finding links: {e}")
        
        # Also check page source for profile URLs
        page_source = self.driver.page_source
        profile_pattern = r'["\']([^"\']*?/profiles/\d+)["\']'
        matches = re.findall(profile_pattern, page_source)
        for match in matches:
            if match.startswith("/"):
                match = f"{self.base_url}{match}"
            elif not match.startswith("http"):
                match = f"{self.base_url}/{match}"
            profile_urls.add(match)
        
        # Extract profile IDs from page source
        id_pattern = r'/profiles/(\d+)'
        id_matches = re.findall(id_pattern, page_source)
        for profile_id in id_matches:
            profile_urls.add(f"{self.base_url}/profiles/{profile_id}")
        
        # Remove duplicates and sort
        profile_urls = sorted(list(set(profile_urls)))
        
        print(f"Found {len(profile_urls)} unique profile URLs")
        return profile_urls
    
    def _extract_ids_from_data(self, data) -> List[str]:
        """Recursively extract profile IDs from nested data structures"""
        ids = []
        if isinstance(data, dict):
            if 'id' in data and isinstance(data['id'], (int, str)):
                ids.append(str(data['id']))
            for value in data.values():
                ids.extend(self._extract_ids_from_data(value))
        elif isinstance(data, list):
            for item in data:
                ids.extend(self._extract_ids_from_data(item))
        return ids
    
    def scrape_profile(self, profile_url: str) -> Optional[Dict]:
        """
        Scrape data from a single startup profile page
        Returns dictionary with startup information
        """
        try:
            print(f"  Scraping {profile_url}...")
            self.driver.get(profile_url)
            time.sleep(4)  # Wait for page to load and JavaScript to execute
            
            # Wait for main content
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                print(f"    Timeout loading {profile_url}")
                return None
            
            # Extract data from the page
            profile_data = {
                'url': profile_url,
                'profile_id': self._extract_profile_id(profile_url),
            }
            
            # Try to extract data from JavaScript/API first
            try:
                js_data = self.driver.execute_script("""
                    // Try to get data from window.__NUXT__
                    if (window.__NUXT__ && window.__NUXT__.data) {
                        return window.__NUXT__.data;
                    }
                    // Try to get from any global variables
                    if (window.$nuxt && window.$nuxt.$store) {
                        return window.$nuxt.$store.state;
                    }
                    return null;
                """)
                
                if js_data:
                    extracted = self._extract_profile_from_js(js_data)
                    profile_data.update(extracted)
            except Exception as e:
                print(f"    Could not extract from JavaScript: {e}")
            
            # Try to extract company name from visible elements
            name_selectors = [
                "h1",
                "h2",
                "[class*='company-name']",
                "[class*='startup-name']",
                "[class*='profile-name']",
                ".title",
                "[data-testid*='name']"
            ]
            
            for selector in name_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 0 and len(text) < 200:
                            if 'name' not in profile_data or not profile_data['name']:
                                profile_data['name'] = text
                            break
                    if 'name' in profile_data and profile_data['name']:
                        break
                except:
                    continue
            
            # Extract text content from common sections
            page_text = self.driver.find_element(By.TAG_NAME, "body").text
            
            # Try to extract structured information from visible text
            # Look for patterns like "Industry:", "Founded:", etc.
            text_sections = page_text.split('\n')
            current_label = None
            
            for line in text_sections:
                line = line.strip()
                if not line:
                    continue
                
                # Look for label-value pairs
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        label = parts[0].strip().lower()
                        value = parts[1].strip()
                        
                        # Map common labels to fields
                        field_mapping = {
                            'industry': 'industry',
                            'sector': 'sector',
                            'founded': 'founded',
                            'location': 'location',
                            'website': 'website',
                            'email': 'email',
                            'phone': 'phone',
                            'employees': 'employees',
                            'funding': 'funding',
                            'stage': 'stage',
                            'description': 'description',
                            'about': 'description',
                            'tags': 'tags'
                        }
                        
                        for key, field in field_mapping.items():
                            if key in label:
                                if field not in profile_data or not profile_data[field]:
                                    profile_data[field] = value
                                break
            
            # Extract description (usually longer text)
            if 'description' not in profile_data or not profile_data['description']:
                # Try to find description in paragraphs
                try:
                    paragraphs = self.driver.find_elements(By.TAG_NAME, "p")
                    descriptions = []
                    for p in paragraphs:
                        text = p.text.strip()
                        if len(text) > 50:  # Likely a description
                            descriptions.append(text)
                    if descriptions:
                        profile_data['description'] = ' '.join(descriptions[:3])  # First 3 paragraphs
                except:
                    pass
            
            # Extract links (website, social media, etc.)
            try:
                links = self.driver.find_elements(By.TAG_NAME, "a")
                websites = []
                emails = []
                for link in links:
                    href = link.get_attribute("href")
                    if href:
                        if href.startswith("http") and "startupsg.gov.sg" not in href:
                            websites.append(href)
                        elif href.startswith("mailto:"):
                            emails.append(href.replace("mailto:", ""))
                
                if websites and 'website' not in profile_data:
                    profile_data['website'] = websites[0]
                if emails and 'email' not in profile_data:
                    profile_data['email'] = emails[0]
            except:
                pass
            
            # Try to find structured data in page source
            page_source = self.driver.page_source
            
            # Look for JSON-LD or script tags with data
            soup = BeautifulSoup(page_source, 'html.parser')
            scripts = soup.find_all('script', type='application/json')
            
            for script in scripts:
                try:
                    if script.string:
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            flattened = self._flatten_dict(data)
                            # Only add fields that don't already exist
                            for key, value in flattened.items():
                                if key not in profile_data or not profile_data[key]:
                                    profile_data[key] = value
                except:
                    pass
            
            # Store full text as fallback (truncated)
            if page_text:
                profile_data['full_text'] = page_text[:3000]
            
            return profile_data
            
        except Exception as e:
            print(f"    Error scraping {profile_url}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_profile_from_js(self, js_data) -> Dict:
        """Extract profile information from JavaScript data structures"""
        extracted = {}
        
        def traverse(obj, path=""):
            if isinstance(obj, dict):
                # Look for common profile fields
                field_mapping = {
                    'name': 'name',
                    'companyName': 'name',
                    'title': 'name',
                    'description': 'description',
                    'about': 'description',
                    'industry': 'industry',
                    'sector': 'sector',
                    'location': 'location',
                    'website': 'website',
                    'url': 'website',
                    'email': 'email',
                    'phone': 'phone',
                    'founded': 'founded',
                    'foundedYear': 'founded',
                    'employees': 'employees',
                    'funding': 'funding',
                    'stage': 'stage',
                    'tags': 'tags'
                }
                
                for key, value in obj.items():
                    new_path = f"{path}.{key}" if path else key
                    
                    # Check if this key maps to a field we want
                    if key.lower() in field_mapping:
                        field_name = field_mapping[key.lower()]
                        if field_name not in extracted or not extracted[field_name]:
                            if isinstance(value, (str, int, float)):
                                extracted[field_name] = str(value)
                            elif isinstance(value, list) and value:
                                extracted[field_name] = ', '.join(str(v) for v in value)
                    
                    # Recursively traverse
                    traverse(value, new_path)
            
            elif isinstance(obj, list):
                for item in obj:
                    traverse(item, path)
        
        traverse(js_data)
        return extracted
    
    def _extract_profile_id(self, url: str) -> Optional[str]:
        """Extract profile ID from URL"""
        match = re.search(r'/profiles/(\d+)', url)
        return match.group(1) if match else None
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                items.append((new_key, ', '.join(str(x) for x in v)))
            else:
                items.append((new_key, v))
        return dict(items)
    
    def close(self):
        """Close the browser"""
        self.driver.quit()


if __name__ == "__main__":
    scraper = StartupSGScraper(headless=False)  # Set to True for headless mode
    try:
        # Get all startup URLs
        urls = scraper.get_all_startup_urls()
        print(f"\nFound {len(urls)} startup profiles")
        
        # Scrape first 3 as test
        for url in urls[:3]:
            data = scraper.scrape_profile(url)
            if data:
                print(f"\nScraped data: {json.dumps(data, indent=2)}")
    finally:
        scraper.close()

