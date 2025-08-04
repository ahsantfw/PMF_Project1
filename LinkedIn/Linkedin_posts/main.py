import os
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
import time

from search_terms import get_topics_from_csv
from semantic_analyzer import SemanticAnalyzer
from utils import Utils
from platform_specific import PlatformSpecific

class LinkedInScraper:
    def __init__(self):
        """Initialize the scraper for LinkedIn."""
        load_dotenv()
        self.utils = Utils()
        self.semantic_analyzer = SemanticAnalyzer()
        self.platform_scraper = PlatformSpecific(self.semantic_analyzer, self.utils)

        self.processed_urls = set(json.load(open('global_url.json', 'r')).get('articles_global_urls', []))
        self.global_keywords = ""
        self.stopwords_extra = set(json.load(open('stopwords_extra.json', 'r'))['stopwords_extra'])

        self.verbose_logging = True
        self.delay_seconds = 0.5
        self.filter_config = {
            'relevance_threshold': 0.35,
            'search_date_range': "r604800", # Past Week. Other options: r86400 (24h), r2592000 (Month)
            'min_post_length': 100,
            'min_word_count': 10,
            'max_link_ratio': 0.3,
            'promo_keywords': ["buy now", "subscribe", "free trial", "discount", "offer", "promo", "sale"],
            'blacklisted_domains': ['bit.ly', 'tinyurl.com', 't.co']
        }

    def process_search_query(self, search_query: str, all_items: list, save_callback: callable):
        """Drives the LinkedIn scraping and analysis process."""
        try:
            post_elements = self.platform_scraper.search_linkedin_posts(
                search_query, 
                self.filter_config['search_date_range']
            )
            
            for post_element in post_elements:
                print("\n" + "="*70)
                
                post_data = self.platform_scraper._extract_post_data(post_element)
                if not post_data or not post_data.get("url"):
                    if self.verbose_logging: print("Status: SKIPPED - Could not extract basic post data.")
                    continue

                print(f"Processing Item: {post_data['url']}")

                if post_data['url'] in self.processed_urls:
                    if self.verbose_logging: print("Status: SKIPPED - URL already processed.")
                else:
                    passes, reason = self.platform_scraper._item_passes_filters(post_data, self.filter_config)
                    if not passes:
                        if self.verbose_logging: print(f"Status: SKIPPED - Failed pre-filters. Reason: {reason}")
                    else:
                        print("Status: Passed Pre-filters. Analyzing for relevance...")
                        post_text = post_data.get("content", "")
                        
                        relevance_threshold = self.filter_config.get('relevance_threshold', 0.35)
                        is_relevant, score, new_keywords = self.semantic_analyzer._analyze_text_relevance(
                            post_text, self.global_keywords, relevance_threshold=relevance_threshold
                        )
                        print(f"Relevance Score: {score:.4f} (Threshold: {relevance_threshold})")

                        if is_relevant:
                            print("Status: SCRAPED - Item is relevant.")
                            post_data["relevance_score"] = score
                            post_data["matched_topic"] = search_query
                            
                            if self.verbose_logging:
                                print(f"Found {len(new_keywords.values())} semantic phrases: {list(new_keywords.values())}")

                            all_items.append(post_data)
                            self.processed_urls.add(post_data['url'])
                            print(f"✓ Data for post by {post_data['author']} saved.")
                            
                            if save_callback: save_callback()
                            print(f"📊 Total relevant items so far: {len(all_items)}")
                            
                            self.global_keywords = self.utils._update_global_keywords(new_keywords, self.global_keywords, self.stopwords_extra)
                            self.utils.save_global_keywords(self.global_keywords)
                        else:
                            if self.verbose_logging: print(f"Status: SKIPPED - Relevance score too low.")

                time.sleep(self.delay_seconds)
        except Exception as e:
            print(f"An unexpected error occurred during LinkedIn search or analysis: {e}")

    def close(self):
        """Closes the Selenium driver."""
        self.platform_scraper.close()

if __name__ == "__main__":
    scraper = LinkedInScraper()
    try:
        os.makedirs('outputs', exist_ok=True)
        all_topics = get_topics_from_csv()
        all_items_for_run = []

        def save_if_needed():
            if len(all_items_for_run) > 0 and len(all_items_for_run) % 10 == 0:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f'outputs/linkedin_posts_progress_{timestamp}.json'
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(all_items_for_run, f, indent=2)
                    scraper.utils.save_processed_urls(scraper.processed_urls)
                    scraper.utils.save_global_keywords(scraper.global_keywords)
                    print(f"💾 Saved progress: {len(all_items_for_run)} items to {filename}")
                except Exception as e:
                    print(f"⚠️ Error saving progress: {e}")
        
        for topic_info in all_topics:
            search_query = topic_info['topic']
            scraper.global_keywords = search_query

            print("\n" + "*"*70)
            print(f"Processing Topic: {search_query}")
            print(f"Initializing Global Keywords with: '{scraper.global_keywords}'")
            print("*"*70)

            scraper.process_search_query(
                search_query, 
                all_items=all_items_for_run, 
                save_callback=save_if_needed
            )
            print(f"Found {len(all_items_for_run)} total relevant items so far.")

        if all_items_for_run:
            final_filename = 'outputs/linkedin_posts_final_results.json'
            with open(final_filename, 'w', encoding='utf-8') as f:
                json.dump(all_items_for_run, f, indent=2)
            print(f"Saved {len(all_items_for_run)} final items to {final_filename}")

    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Saving progress...")
    except Exception as e:
        print(f"\nError during scraping: {e}")
    finally:
        scraper.close()