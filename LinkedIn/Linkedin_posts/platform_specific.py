import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from urllib.parse import quote_plus

from dotenv import load_dotenv
from langdetect import LangDetectException, detect
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
import re

class PlatformSpecific:
    def __init__(self, semantic_analyzer, utils):
        """Initializes the Selenium WebDriver and logs into LinkedIn."""
        load_dotenv()
        self.semantic_analyzer = semantic_analyzer
        self.utils = utils

        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        # To run headless (without a browser window), uncomment the next line
        # options.add_argument("--headless")
        self.driver = webdriver.Chrome(service=webdriver.chrome.service.Service(ChromeDriverManager().install()), options=options)
        
        self.linkedin_email = os.getenv("LINKEDIN_EMAIL")
        self.linkedin_password = os.getenv("LINKEDIN_PASSWORD")
        if not self.linkedin_email or not self.linkedin_password:
            raise ValueError("LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in your .env file.")
        self._login()

    def _login(self):
        """Logs into LinkedIn using credentials from .env file."""
        try:
            self.driver.get("https://www.linkedin.com/login")
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "username")))
            self.driver.find_element(By.ID, "username").send_keys(self.linkedin_email)
            self.driver.find_element(By.ID, "password").send_keys(self.linkedin_password)
            self.driver.find_element(By.XPATH, "//button[@type='submit']").click()
            # After clicking, we simply wait a few seconds for the login to process
            # before the next function navigates to the search page.
            print("Login submitted. Pausing for 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"Error during LinkedIn login: {e}")
            self.close()
            raise

    def search_linkedin_posts(self, search_query: str, date_range: str, max_scrolls: int = 40) -> list:
        """Searches for posts on LinkedIn and returns a list of post elements."""
        print(f"Searching LinkedIn for posts with query: '{search_query}'")
        encoded_query = quote_plus(search_query)
        search_url = f"https://www.linkedin.com/search/results/content/?datePosted={date_range}&keywords={encoded_query}&sortBy=%22relevance%22"
        
        self.driver.get(search_url)
        try:
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "feed-shared-update-v2")))
            print("Search results page loaded.")
        except Exception:
            print(f"⚠️ No search results found for '{search_query}'.")
            return []

        last_height = self.driver.execute_script("return document.body.scrollHeight")
        for scroll_num in range(max_scrolls):
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print(f"Scrolling... ({scroll_num + 1}/{max_scrolls})")
            time.sleep(3)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Reached the end of the search results.")
                break
            last_height = new_height
        
        post_elements = self.driver.find_elements(By.CLASS_NAME, "feed-shared-update-v2")
        print(f"Found {len(post_elements)} potential post elements after scrolling.")
        return post_elements

    def _extract_post_data(self, post_element) -> dict:
        """Extracts all data from a single post element."""
        try:
            data_urn = post_element.get_attribute("data-urn")
            if not data_urn: return None

            content = ""
            try:
                content_element = post_element.find_element(By.CLASS_NAME, "update-components-text")
                try:
                    more_button = content_element.find_element(By.XPATH, ".//button[contains(@class, 'see-more')]")
                    self.driver.execute_script("arguments[0].click();", more_button)
                    time.sleep(0.5)
                except NoSuchElementException: pass
                content = content_element.text.strip()
            except NoSuchElementException: pass
            
            if not content: return None

            author = "N/A"
            try:
                author_span = post_element.find_element(By.CLASS_NAME, "update-components-actor__single-line-truncate")
                author = author_span.text.split('\n')[0].strip()
            except NoSuchElementException: pass

            date_string = "N/A"
            try:
                date_string = post_element.find_element(By.CLASS_NAME, "update-components-actor__sub-description").text.strip().split('•')[0].strip()
            except NoSuchElementException: pass
            
            likes_count, comments_count = 0, 0
            try:
                social_counts_container = post_element.find_element(By.CLASS_NAME, "social-details-social-counts")
                try:
                    likes_text = social_counts_container.find_element(By.CLASS_NAME, "social-details-social-counts__reactions-count").text.strip()
                    likes_count = int("".join(filter(str.isdigit, likes_text)))
                except (NoSuchElementException, ValueError): pass
                try:
                    comment_text = social_counts_container.find_element(By.XPATH, ".//button[contains(@aria-label, 'comment')]").text.strip()
                    comments_count = int("".join(filter(str.isdigit, comment_text)))
                except (NoSuchElementException, ValueError): pass
            except NoSuchElementException: pass

            return {
                "url": f"https://www.linkedin.com/feed/update/{data_urn}",
                "author": author, "content": content, "date_string": date_string,
                "scraped_at": datetime.now().isoformat(), "likes_count": likes_count,
                "comments_count": comments_count
            }
        except Exception:
            return None

    def _item_passes_filters(self, post_data: dict, filter_config: dict) -> Tuple[bool, str]:
        """Applies a series of pre-filters to the extracted LinkedIn post data."""
        content = post_data.get("content", "")
        
        if len(content) < filter_config.get('min_post_length', 100):
            return False, f"Content length less than {filter_config['min_post_length']}"
        if len(content.split()) < filter_config.get('min_word_count', 10):
            return False, f"Word count less than {filter_config['min_word_count']}"
        try:
            if detect(content) != 'en':
                return False, "Language not English"
        except LangDetectException:
            return False, "Language could not be detected"
        
        if any(kw in content.lower() for kw in filter_config.get('promo_keywords', [])):
            return False, "Detected as promotional content"
        
        word_count = len(content.split())
        link_count = len(re.findall(r'https?://', content))
        link_ratio = (link_count / word_count) if word_count else 0
        if link_ratio > filter_config.get('max_link_ratio', 0.3):
            return False, f"Exceeds max link ratio ({link_ratio:.2f})"
        
        return True, "Passed"

    def close(self):
        """Closes the Selenium WebDriver."""
        if self.driver:
            self.driver.quit()