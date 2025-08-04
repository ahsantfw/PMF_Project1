import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Set
from urllib.parse import urlparse

from huggingface_hub import HfApi, list_datasets, list_models, list_spaces
from langdetect import LangDetectException, detect
import requests


class PlatformSpecific:
    def __init__(self, semantic_analyzer, utils):
        self.semantic_analyzer = semantic_analyzer
        self.utils = utils
        self.hf_api_token = os.getenv("HF_API_TOKEN")
        if not self.hf_api_token:
            raise ValueError("HF_API_TOKEN not found in .env file.")
        self.hf_client = HfApi(token=self.hf_api_token)

    def _item_passes_filters(self, item: Dict, description: str, filter_config: Dict) -> (bool, str):
        """Applies a series of pre-filters to a Hugging Face item using its description."""
        # Content Filters
        if len(description) < filter_config.get('min_post_length', 100):
            return False, f"Content too short ({len(description)} chars)."
        if len(description.split()) < filter_config.get('min_word_count', 10):
            return False, f"Not enough words ({len(description.split())} words)."
        try:
            if detect(description) != 'en':
                return False, "Language not English."
        except LangDetectException:
            return False, "Language detection failed."

        # Age Filter
        created_at = item.get('created_at')
        if created_at:
            age_days = (datetime.now(timezone.utc) - created_at).days
            if age_days > filter_config.get('max_age_days', 730):
                return False, f"Too old ({age_days} days)."

        # Engagement Filter
        item_type = item.get('type')
        reactions = item.get('downloads', 0) if item_type != 'space' else item.get('likes', 0)
        if reactions < filter_config.get('min_engagement', 10):
            return False, f"Not enough engagement ({reactions})."

        # Spam Prevention
        link_count = len(re.findall(r'https?://', description))
        word_count = len(description.split())
        link_ratio = (link_count / word_count) if word_count else 0
        if link_ratio > filter_config.get('max_link_ratio', 0.3):
            return False, f"Too many links (ratio: {link_ratio:.2f})."
        if any(domain in description for domain in filter_config.get('blacklisted_domains', [])):
            return False, "Contains blacklisted domain."
        if any(kw in description.lower() for kw in filter_config.get('promo_keywords', [])):
            return False, "Detected as promotional content."

        return True, "Passed"

    def _search_huggingface_items(self, query: str, stopwords_extra: set, limit: int = 100) -> List[Dict]:
        """
        Searches Hugging Face first with the full query for precision, 
        then with refined keywords as a fallback for broader reach.
        """
        all_found_items = {}

        def add_item_to_found(info_obj, current_type):
            item_id = getattr(info_obj, 'id', None)
            if not item_id or item_id in all_found_items: return False
            
            url_prefix_map = {'model': "https://huggingface.co/", 'dataset': "https://huggingface.co/datasets/", 'space': "https://huggingface.co/spaces/"}
            all_found_items[item_id] = {
                'type': current_type, 'id': item_id, 'url': f"{url_prefix_map.get(current_type, '')}{item_id}",
                'created_at': getattr(info_obj, 'created_at', None), 'likes': getattr(info_obj, 'likes', 0),
                'downloads': getattr(info_obj, 'downloads', 0), 'author': getattr(info_obj, 'author', 'N/A'),
                'tags': getattr(info_obj, 'tags', [])
            }
            return True

        # --- NEW: Two-Step Search Strategy ---
        # 1. First, try searching with the full, original query for the most relevant results.
        print(f"Attempting precise search with full query: '{query}'")
        for item_type, list_func in [('model', list_models), ('dataset', list_datasets), ('space', list_spaces)]:
            try:
                results = list_func(search=query, token=self.hf_api_token, limit=limit)
                for info in results:
                    add_item_to_found(info, item_type)
            except Exception as e:
                print(f"Error during precise search for {item_type}s: {e}")
        
        # 2. If the precise search yields very few results, use the keyword fallback.
        if len(all_found_items) < 5:
            print("Precise search yielded few results. Expanding search with keywords.")
            words = re.findall(r'\b\w+\b', query.lower())
            search_keywords = [word for word in words if word not in stopwords_extra and len(word) > 2]
            if not search_keywords: search_keywords = [query] # Fallback if all words are stopwords
            
            print(f"Refined search keywords for Hugging Face: {search_keywords}")

            for keyword in search_keywords:
                # Avoid re-searching the full query if it was the only keyword
                if keyword == query and len(all_found_items) > 0:
                    continue
                for item_type, list_func in [('model', list_models), ('dataset', list_datasets), ('space', list_spaces)]:
                    try:
                        results = list_func(search=keyword, token=self.hf_api_token, limit=limit)
                        for info in results:
                            add_item_to_found(info, item_type)
                    except Exception as e:
                        print(f"Error fetching {item_type}s for keyword '{keyword}': {e}")

        print(f"Total unique items fetched from Hugging Face: {len(all_found_items)}")
        return list(all_found_items.values())

    def _get_item_description(self, item_id: str, item_type: str) -> str:
        """Fetches and cleans the README of a Hugging Face item."""
        url_map = {
            "model": f"https://huggingface.co/{item_id}/raw/main/README.md",
            "dataset": f"https://huggingface.co/datasets/{item_id}/raw/main/README.md",
            "space": f"https://huggingface.co/spaces/{item_id}/raw/main/README.md"
        }
        readme_url = url_map.get(item_type)
        if not readme_url: return ""

        try:
            headers = {"Authorization": f"Bearer {self.hf_api_token}"}
            response = requests.get(readme_url, headers=headers)
            if response.status_code != 200: return ""
            # Basic cleaning
            content = re.sub(r'---(.|\n)*?---', '', response.text) # Remove YAML front matter
            content = re.sub(r'<[^>]+>', '', content) # Remove HTML
            return content.strip()
        except Exception as e:
            print(f"⚠️ Error fetching README for {item_type} {item_id}: {e}")
            return ""

    def _extract_item_data(self, item: Dict, content_type: str) -> Dict:
        """Extracts and formats key data from a Hugging Face item."""
        return {
            "platform": "huggingface", "title": item.get('id'), "content": "",
            "author": item.get('author', 'N/A'), "url": item.get('url'),
            "created_date": item.get('created_at').isoformat() if item.get('created_at') else 'N/A',
            "score": item.get('downloads', 0) if content_type != 'space' else item.get('likes', 0),
            "comments_count": 0, "scraped_at": datetime.now().isoformat(), "content_type": content_type,
            "tags": item.get('tags', []), "likes": item.get('likes', 0),
            "relevance_score": 0.0, "matched_topic": ""
        }