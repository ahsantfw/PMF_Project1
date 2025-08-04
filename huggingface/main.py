import os
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
import time

# Updated import to use the new CSV-based function
from search_terms import get_topics_from_csv
from semantic_analyzer import SemanticAnalyzer
from utils import Utils
from platform_specific import PlatformSpecific

class HuggingFaceScraper:
    def __init__(self):
        """Initialize Hugging Face scraper."""
        load_dotenv()
        self.utils = Utils()
        self.semantic_analyzer = SemanticAnalyzer()
        self.platform_scraper = PlatformSpecific(self.semantic_analyzer, self.utils)

        self.processed_urls = set(json.load(open('global_url.json', 'r')).get('articles_global_urls', []))
        self.global_keywords = ""
        self.stopwords_extra = set(json.load(open('stopwords_extra.json', 'r'))['stopwords_extra'])
        
        # Centralized Configuration
        self.verbose_logging = True
        self.delay_seconds = 0.5
        self.filter_config = {
            'relevance_threshold': 0.35,
            'min_post_length': 100, 'min_word_count': 10, 'max_age_days': 730,
            'min_engagement': 10, 'max_link_ratio': 0.3,
            'promo_keywords': ["buy now", "subscribe", "free trial", "discount", "offer", "promo", "sale"],
            'blacklisted_domains': [
                'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'is.gd', 'ow.ly', 'buff.ly', 'adf.ly',
                'shorte.st', 'bc.vc', 'doubleclick.net', 'adservice.google.com',
                'googlesyndication.com', 'analytics.google.com', 'criteo.com', 'taboola.com', 'outbrain.com'
            ]
        }

    def process_search_query(self, search_query: str, max_items: int = 10000, all_items=None, save_callback=None) -> List[Dict]:
        """Search Hugging Face with pre-filtering and clear, grouped logging."""
        
        try:
            print(f"Searching Hugging Face with query: '{search_query}'")
            # --- UPDATED: Pass stopwords to the search function ---
            hf_found_items = self.platform_scraper._search_huggingface_items(
                search_query, 
                self.stopwords_extra,
                limit=max_items
            )
            # hf_found_items = self.platform_scraper._search_huggingface_items(search_query, limit=max_items)
            
            result_count = 0
            for hf_item in hf_found_items:
                if result_count >= max_items: break

                print("\n" + "="*70)
                print(f"Processing Item: {hf_item['url']}")

                if hf_item['url'] in self.processed_urls:
                    if self.verbose_logging: print("Status: SKIPPED - URL already processed.")
                else:
                    description = self.platform_scraper._get_item_description(hf_item['id'], hf_item['type'])
                    passes, reason = self.platform_scraper._item_passes_filters(hf_item, description, self.filter_config)
                    
                    if not passes:
                        if self.verbose_logging: print(f"Status: SKIPPED - Failed pre-filters. Reason: {reason}")
                    else:
                        print("Status: Passed Pre-filters. Analyzing for relevance...")
                        item_text = f"{hf_item.get('id', '')} {description}".strip()
                        # Pull the threshold from your config
                        relevance_threshold = self.filter_config.get('relevance_threshold', 0.35)

                        # Make a single, correct call to the semantic analyzer
                        is_relevant, score, new_keywords = self.semantic_analyzer._analyze_text_relevance(item_text, self.global_keywords, relevance_threshold=relevance_threshold)
                        print(f"Relevance Score: {score:.4f} (Threshold: {relevance_threshold})")

                        if is_relevant:
                            print("Status: SCRAPED - Item is relevant.")
                            extracted_data = self.platform_scraper._extract_item_data(hf_item, hf_item['type'])
                            extracted_data["content"] = description
                            extracted_data["relevance_score"] = score
                            extracted_data["matched_topic"] = search_query
                            
                            if self.verbose_logging: print(f"Found {len(new_keywords)} semantic keywords: {new_keywords}")
                            
                            all_items.append(extracted_data)
                            self.processed_urls.add(hf_item['url'])
                            print(f"✓ Data for '{extracted_data['title'][:50]}...' saved.")
                            result_count += 1
                            
                            if save_callback: save_callback()
                            print(f"📊 Total relevant items so far: {len(all_items)}")
                            
                            self.global_keywords = self.utils._update_global_keywords(new_keywords, self.global_keywords, self.stopwords_extra)
                            self.utils.save_global_keywords(self.global_keywords)
                        else:
                            if self.verbose_logging: print(f"Status: SKIPPED - Relevance score too low.")

                time.sleep(self.delay_seconds)
        
        except Exception as e:
            print(f"An unexpected error occurred during Hugging Face search or analysis: {e}")

    def close(self):
        """Safely close and save progress."""
        self.utils.save_processed_urls(self.processed_urls)
        self.utils.save_global_keywords(self.global_keywords)

# --- MAIN EXECUTION BLOCK (Refactored to use CSV) ---
if __name__ == "__main__":
    scraper = HuggingFaceScraper()
    try:
        os.makedirs('outputs', exist_ok=True)
        
        # 1. Get all topics from the new CSV function
        all_topics = get_topics_from_csv()
        all_items_for_run = []

        def save_if_needed():
            if len(all_items_for_run) > 0 and len(all_items_for_run) % 10 == 0:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f'outputs/huggingface_progress_{timestamp}.json'
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(all_items_for_run, f, indent=2)
                    scraper.utils.save_processed_urls(scraper.processed_urls)
                    scraper.utils.save_global_keywords(scraper.global_keywords)
                    print(f"💾 Saved progress: {len(all_items_for_run)} items to {filename}")
                except Exception as e:
                    print(f"⚠️ Error saving progress: {e}")
        
        # 2. Loop through each topic from the CSV
        for topic_info in all_topics:
            search_query = topic_info['topic']
            
            # 3. Initialize global_keywords with the topic itself.
            scraper.global_keywords = search_query
                

            print("\n" + "*"*70)
            print(f"Processing Topic: {search_query}")
            print(f"Initializing Global Keywords with {len(scraper.global_keywords)} characters.")
            print("*"*70)

            # 4. Call the existing process function for the current topic
            scraper.process_search_query(
                search_query, 
                all_items=all_items_for_run, 
                save_callback=save_if_needed
            )
            print(f"Found {len(all_items_for_run)} total relevant items so far.")

        # 5. Save the final combined results at the end of the run
        if all_items_for_run:
            final_filename = 'outputs/huggingface_final_results.json'
            with open(final_filename, 'w', encoding='utf-8') as f:
                json.dump(all_items_for_run, f, indent=2)
            print(f"Saved {len(all_items_for_run)} final items to {final_filename}")

    
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Saving progress...")
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords)
    except Exception as e:
        print(f"\nError during scraping: {e}")
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords)
    finally:
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords)