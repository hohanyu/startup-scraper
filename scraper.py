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
        Handles pagination to get all profiles
        Returns list of profile URLs
        """
        print("Fetching directory page...")
        self.driver.get(f"{self.base_url}/directory/startups")
        
        # Wait for page to load and JavaScript to execute
        time.sleep(5)
        
        # Wait for pagination to appear
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.v-pagination, [class*="pagination"]'))
            )
        except TimeoutException:
            print("Warning: Pagination element not found, proceeding anyway...")
        
        profile_urls = set()
        current_page = 1
        max_pages = 1000  # Safety limit
        no_more_pages = False
        
        print("Extracting profile URLs from all pages...")
        
        while current_page <= max_pages and not no_more_pages:
            print(f"\nProcessing page {current_page}...")
            
            # Wait a bit for page content to load
            time.sleep(3)
            
            # Extract profile URLs from current page
            page_urls = self._extract_urls_from_current_page()
            new_urls = page_urls - profile_urls
            
            if new_urls:
                profile_urls.update(new_urls)
                print(f"  Found {len(new_urls)} new profiles (total: {len(profile_urls)})")
            else:
                print(f"  No new profiles found on page {current_page}")
            
            # Try to navigate to next page
            next_page_success = self._navigate_to_next_page()
            
            if not next_page_success:
                print(f"  No more pages available")
                no_more_pages = True
            else:
                current_page += 1
        
        # Remove duplicates and sort
        profile_urls = sorted(list(set(profile_urls)))
        
        print(f"\n✓ Found {len(profile_urls)} unique profile URLs across {current_page} page(s)")
        return profile_urls
    
    def _extract_urls_from_current_page(self) -> set:
        """Extract all profile URLs from the current page"""
        urls = set()
        
        # Method 1: Find all links in the DOM
        try:
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                href = link.get_attribute("href")
                if href and "/profiles/" in href:
                    # Normalize URL
                    if href.startswith("/"):
                        href = f"{self.base_url}{href}"
                    elif not href.startswith("http"):
                        href = f"{self.base_url}/{href}"
                    urls.add(href)
        except Exception as e:
            print(f"    Error finding links: {e}")
        
        # Method 2: Extract from page source
        try:
            page_source = self.driver.page_source
            profile_pattern = r'["\']([^"\']*?/profiles/\d+)["\']'
            matches = re.findall(profile_pattern, page_source)
            for match in matches:
                if match.startswith("/"):
                    match = f"{self.base_url}{match}"
                elif not match.startswith("http"):
                    match = f"{self.base_url}/{match}"
                urls.add(match)
            
            # Also extract profile IDs
            id_pattern = r'/profiles/(\d+)'
            id_matches = re.findall(id_pattern, page_source)
            for profile_id in id_matches:
                urls.add(f"{self.base_url}/profiles/{profile_id}")
        except Exception as e:
            print(f"    Error extracting from page source: {e}")
        
        return urls
    
    def _navigate_to_next_page(self) -> bool:
        """
        Navigate to the next page of results
        Returns True if navigation was successful, False if no more pages
        """
        try:
            # Wait a bit for pagination to be ready
            time.sleep(1)
            
            # Try multiple strategies to find and click next button
            
            # Strategy 1: Look for "Next" button by text
            try:
                next_buttons = self.driver.find_elements(
                    By.XPATH, 
                    "//button[contains(text(), 'Next') or contains(text(), '→') or contains(text(), '>')]"
                )
                for btn in next_buttons:
                    if btn.is_enabled() and btn.is_displayed():
                        # Check if it's actually the next button (not disabled)
                        classes = btn.get_attribute("class") or ""
                        if "disabled" not in classes.lower():
                            btn.click()
                            time.sleep(3)  # Wait for page to load
                            return True
            except Exception as e:
                pass
            
            # Strategy 2: Look for pagination component and find next button
            try:
                pagination = self.driver.find_element(
                    By.CSS_SELECTOR, 
                    '.v-pagination, [class*="pagination"]'
                )
                
                # Find next button in pagination
                next_btn = pagination.find_elements(
                    By.CSS_SELECTOR,
                    'button:not([disabled]), a:not([aria-disabled="true"])'
                )
                
                # Look for button with arrow or "next" text, or the last enabled button
                for btn in next_btn:
                    text = btn.text.strip().lower()
                    classes = btn.get_attribute("class") or ""
                    aria_label = btn.get_attribute("aria-label") or ""
                    
                    # Skip if disabled
                    if "disabled" in classes.lower() or btn.get_attribute("disabled"):
                        continue
                    
                    # Check if it's a next button
                    if any(keyword in text for keyword in ["next", "→", ">", "forward"]):
                        btn.click()
                        time.sleep(3)
                        return True
                    elif any(keyword in aria_label.lower() for keyword in ["next", "forward"]):
                        btn.click()
                        time.sleep(3)
                        return True
                
                # Strategy 3: Click the next page number
                # Get current page number and click next one
                current_url = self.driver.current_url
                page_numbers = pagination.find_elements(
                    By.CSS_SELECTOR,
                    'button, a'
                )
                
                # Find the highest page number button that's enabled
                max_page = 0
                next_page_btn = None
                
                for btn in page_numbers:
                    text = btn.text.strip()
                    if text.isdigit():
                        page_num = int(text)
                        if page_num > max_page:
                            classes = btn.get_attribute("class") or ""
                            if "disabled" not in classes.lower() and btn.is_enabled():
                                max_page = page_num
                                next_page_btn = btn
                
                # If we found a higher page number, click it
                if next_page_btn:
                    # But first check if we're already on that page
                    # If current page is less than max, click the next one
                    # For now, let's try clicking the last enabled number button
                    # Actually, better approach: find buttons with numbers and click the one after current
                    pass
                
            except Exception as e:
                pass
            
            # Strategy 4: Use JavaScript to find and click next (most reliable)
            try:
                result = self.driver.execute_script("""
                    // Find pagination
                    const pagination = document.querySelector('.v-pagination, [class*="pagination"]');
                    if (!pagination) return {success: false, reason: 'no_pagination'};
                    
                    // Find all buttons/links
                    const buttons = Array.from(pagination.querySelectorAll('button, a'));
                    
                    // First, try to find explicit "Next" button
                    let nextButton = null;
                    for (let btn of buttons) {
                        const text = btn.textContent.trim().toLowerCase();
                        const classes = btn.className || '';
                        const ariaLabel = (btn.getAttribute('aria-label') || '').toLowerCase();
                        const disabled = btn.disabled || 
                                       classes.includes('disabled') || 
                                       btn.getAttribute('aria-disabled') === 'true' ||
                                       btn.classList.contains('v-pagination__prev');
                        
                        if (disabled) continue;
                        
                        // Look for next indicators
                        if (text.includes('next') || 
                            text === '→' || 
                            text === '>' ||
                            ariaLabel.includes('next')) {
                            nextButton = btn;
                            break;
                        }
                    }
                    
                    // If no explicit next button, find current page and click next number
                    if (!nextButton) {
                        let currentPage = null;
                        const pageNumbers = [];
                        
                        buttons.forEach(btn => {
                            const text = btn.textContent.trim();
                            const classes = btn.className || '';
                            
                            // Check if it's a number
                            if (/^\\d+$/.test(text)) {
                                const num = parseInt(text);
                                const isActive = classes.includes('v-pagination__item--active') || 
                                               btn.getAttribute('aria-current') === 'page' ||
                                               classes.includes('active');
                                
                                pageNumbers.push({num: num, button: btn, active: isActive});
                                
                                if (isActive) {
                                    currentPage = num;
                                }
                            }
                        });
                        
                        // If we found current page, click the next one
                        if (currentPage !== null) {
                            const nextPageNum = currentPage + 1;
                            const nextPageBtn = pageNumbers.find(p => p.num === nextPageNum);
                            
                            if (nextPageBtn) {
                                nextButton = nextPageBtn.button;
                            } else {
                                // Check if there are more pages available (max page > current)
                                const maxPage = Math.max(...pageNumbers.map(p => p.num));
                                if (currentPage >= maxPage) {
                                    return {success: false, reason: 'last_page'};
                                }
                            }
                        } else {
                            // Can't determine current page, try clicking the last number button
                            const sortedPages = pageNumbers.sort((a, b) => b.num - a.num);
                            if (sortedPages.length > 0) {
                                // Don't click the highest if we're not sure, but this is a fallback
                                return {success: false, reason: 'cannot_determine_current_page'};
                            }
                        }
                    }
                    
                    if (nextButton) {
                        // Scroll into view and click
                        nextButton.scrollIntoView({behavior: 'smooth', block: 'center'});
                        nextButton.click();
                        return {success: true, method: 'clicked_next'};
                    }
                    
                    return {success: false, reason: 'no_next_button_found'};
                """)
                
                if result and isinstance(result, dict) and result.get('success'):
                    time.sleep(3)  # Wait for page to load
                    return True
                else:
                    # Check if we're on the last page
                    if result and isinstance(result, dict) and result.get('reason') == 'last_page':
                        return False
            except Exception as e:
                print(f"    JavaScript navigation error: {e}")
                pass
            
            # Strategy 5: Check if URL changed (might be using query params)
            # If we're still on the same URL after trying to click, assume no more pages
            return False
            
        except Exception as e:
            print(f"    Error navigating to next page: {e}")
            return False
    
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

