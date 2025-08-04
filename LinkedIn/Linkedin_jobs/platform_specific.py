import requests
from bs4 import BeautifulSoup
import time
import random
from urllib.parse import quote
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import re
from langdetect import detect, LangDetectException

class PlatformSpecific:
    """Handles all platform-specific logic for scraping LinkedIn Jobs without a login."""
    
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    JOBS_PER_PAGE = 25
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self, semantic_analyzer=None, utils=None):
        self.session = self._setup_session()
        # These dependencies can be passed for consistency, even if not used in this specific scraper
        self.semantic_analyzer = semantic_analyzer
        self.utils = utils

    def _setup_session(self) -> requests.Session:
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        return session

    def search_jobs(self, search_query: str, max_jobs: int = 250) -> List[Dict]:
        """Searches for jobs and extracts basic data from each job card."""
        basic_jobs_data = []
        start_index = 0
        
        print(f"Searching for jobs with keyword: '{search_query}'")
        while len(basic_jobs_data) < max_jobs:
            try:
                url = f"{self.BASE_URL}?keywords={quote(search_query)}&start={start_index}"
                response = self.session.get(url, headers=self.HEADERS, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, "html.parser")
                job_cards = soup.find_all("div", class_="base-card")

                if not job_cards:
                    print("No more job cards found. Ending search.")
                    break
                
                for card in job_cards:
                    try:
                        job_link = card.find("a", class_="base-card__full-link")["href"].split("?")[0]
                        title = card.find("h3", class_="base-search-card__title").text.strip()
                        company = card.find("h4", class_="base-search-card__subtitle").text.strip()
                        
                        # Simplified date extraction
                        date_iso = None
                        date_tag = card.find("time", class_="job-search-card__listdate")
                        if date_tag and 'datetime' in date_tag.attrs:
                            date_iso = datetime.fromisoformat(date_tag['datetime']).isoformat()

                        basic_jobs_data.append({
                            "url": job_link,
                            "title": title,
                            "author": company,
                            "date_iso": date_iso, # Only the useful ISO date is kept
                        })
                    except Exception:
                        continue
                
                print(f"Found {len(basic_jobs_data)} basic job listings so far...")
                start_index += self.JOBS_PER_PAGE
                time.sleep(random.uniform(1, 3))

            except Exception as e:
                print(f"An error occurred during scraping: {str(e)}")
                break
        return basic_jobs_data

    def get_full_job_content(self, url: str) -> str:
        """Fetches the full description text for a single job URL."""
        try:
            response = self.session.get(url, headers=self.HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            desc_container = soup.find("div", class_="description__text") or soup.find("div", class_="show-more-less-html__markup")
            return desc_container.get_text(strip=True) if desc_container else ""
        except Exception:
            return ""

    def _item_passes_filters(self, job_data: dict, filter_config: dict) -> Tuple[bool, str]:
        """Applies a series of pre-filters to a LinkedIn Job."""
        content = job_data.get("content", "")

        # Content Filters
        if len(content) < filter_config.get('min_post_length', 100):
            return False, f"Content length less than {filter_config['min_post_length']} characters"
        if len(content.split()) < filter_config.get('min_word_count', 10):
            return False, f"Word count less than {filter_config['min_word_count']} words"
        try:
            if detect(content) != 'en':
                return False, "Language not English"
        except LangDetectException:
            return False, "Language could not be detected"
        
        # Age Filter
        if job_data.get("date_iso"):
            post_date = datetime.fromisoformat(job_data["date_iso"])
            age_days = (datetime.now() - post_date).days
            if age_days > filter_config.get('max_age_days', 730):
                return False, f"Post is too old ({age_days} days)"
        
        # Spam Prevention
        if any(kw in content.lower() for kw in filter_config.get('promo_keywords', [])):
            return False, "Detected as promotional content"
        link_ratio = (len(re.findall(r'https?://', content)) / len(content.split())) if len(content.split()) > 0 else 0
        if link_ratio > filter_config.get('max_link_ratio', 0.3):
            return False, f"Exceeds max link ratio ({link_ratio:.2f})"
        if any(domain in content for domain in filter_config.get('blacklisted_domains', [])):
            return False, "Contains blacklisted domain"
        
        return True, "Passed"

    def close(self):
        self.session.close()
        print("LinkedIn Jobs scraper session closed.")