import os
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from search_terms import get_topics_from_csv
from semantic_analyzer import SemanticAnalyzer
from utils import Utils
from platform_specific import PlatformSpecific
import requests
import time

class StackOverflowScraper:
    def __init__(self):
        """Initialize Stackoverflow scraper."""
        load_dotenv()
        self.utils = Utils()
        self.semantic_analyzer = SemanticAnalyzer()
        self.platform_specific = PlatformSpecific(self.semantic_analyzer, self.utils)

        # API components
        self.stackoverflow_base_url = "https://api.stackexchange.com/2.3"
        self.stackoverflow_token = os.getenv('STACKOVERFLOW_API_TOKEN')
        if not self.stackoverflow_token:
            raise ValueError("Stack Overflow token not found in .env file.")

        # Scraper state
        
        self.processed_urls = set(json.load(open('global_url.json', 'r')).get('articles_global_urls', []))
        self.global_keywords = ""
        self.stopwords_extra = set(json.load(open('stopwords_extra.json', 'r'))['stopwords_extra'])

        # Filter and Logging Configuration
        self.verbose_logging = True
        self.filter_config = {
            'relevance_threshold': 0.35,
            'min_post_length': 100,
            'min_word_count': 10,
            'max_age_days': 730,  
            'min_score': 5,        # Relaxed to a score of 5
            'min_answers': 1,
            'max_link_ratio': 0.3,
            'blacklisted_domains': [
                # Common URL Shorteners
                'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'is.gd', 'ow.ly', 'buff.ly',
                'adf.ly', 'shorte.st', 'bc.vc',

                # Common Ad & Tracking Domains
                'doubleclick.net', 'adservice.google.com', 'googlesyndication.com',
                'analytics.google.com', 'criteo.com', 'taboola.com', 'outbrain.com'
            ]
            
        }
        # Delay in seconds between processing each item
        # self.delay_seconds = 3

    def process_search_query(self, search_query: str, max_items: int = 10000, all_items=None, save_callback=None) -> List[Dict]:
        """Search Stack Overflow with pre-filtering and clear, grouped logging."""
        items = []
        page = 1
        result_count = 0
        
        while result_count < max_items:
            try:
                params = {
                    'q': search_query, 'sort': 'relevance', 'order': 'desc', 'site': 'stackoverflow',
                    'filter': 'withbody', 'pagesize': 100, "key": self.stackoverflow_token, "page": page
                }
                response = requests.get(f"{self.stackoverflow_base_url}/search/advanced", params=params)
                response.raise_for_status()
                data = response.json()
                
                questions = data.get("items", [])
                if not questions:
                    break # No more results

                for post in questions:
                    if result_count >= max_items: break

                    print("\n" + "="*70)
                    print(f"Processing Item: {post['link']}")
                    
                    if post['link'] in self.processed_urls:
                        if self.verbose_logging: print("Status: SKIPPED - URL already processed.")
                        time.sleep(1)
                        continue

                    passes, reason = self.platform_specific._item_passes_filters(post, self.filter_config)
                    if not passes:
                        if self.verbose_logging: print(f"Status: SKIPPED - Failed pre-filters. Reason: {reason}")
                        time.sleep(1)
                        continue
                    
                    print("Status: Passed Pre-filters. Analyzing for relevance...")
                    
                    item_text = f"{post.get('title', '')} {post.get('body', '')}".strip()
                    relevance_threshold = self.filter_config.get('relevance_threshold', 0.35)
                    is_relevant, score, new_keywords_from_post = self.semantic_analyzer._analyze_text_relevance(item_text, self.global_keywords, relevance_threshold=relevance_threshold)
                    print(f"Relevance Score: {score:.4f} (Threshold: {relevance_threshold})")



                    if is_relevant:
                        print("Status: SCRAPED - Item is relevant.")
                        post_data = self.platform_specific._extract_post_data(post)
                        post_data["relevance_score"] = score

                        # 1. First, update keywords with phrases from the main post
                        keywords_after_post = self.utils._update_global_keywords(new_keywords_from_post, self.global_keywords, self.stopwords_extra)

                        # 2. Then, pass this updated list to the answer analyzer
                        final_keywords, relevant_answers = self.platform_specific._extract_and_analyze_answers(
                            post['question_id'], 
                            keywords_after_post, # <-- Use the updated keywords
                            self.stopwords_extra, 
                            relevance_threshold=relevance_threshold, 
                            top_n=10, 
                            verbose_logging=self.verbose_logging
                        )
                        
                        # 3. The function returns the final, fully updated keyword list
                        self.global_keywords = final_keywords 
                        post_data['comments'] = relevant_answers # 'comments' key now holds answers

                        if self.verbose_logging: print(f"Found {len(new_keywords_from_post.values())} semantic phrases from post: {list(new_keywords_from_post.values())}")

                        items.append(post_data)
                        self.processed_urls.add(post['link'])
                        print(f"✓ Data for '{post_data['title'][:50]}...' saved.")
                        result_count += 1
                        
                        if all_items is not None:
                            all_items.append(post_data)
                            if save_callback: save_callback()
                            print(f"📊 Total relevant items so far: {len(all_items)}")
                        
                        self.utils.save_global_keywords(self.global_keywords)
                    else:
                        if self.verbose_logging: print(f"Status: SKIPPED - Relevance score too low.")
                # --- ADDED DELAY ---
                time.sleep(2)        

                if not data.get('has_more', False):
                    break
                page += 1
                time.sleep(data.get('backoff', 0)) # Respect API backoff period

            except requests.exceptions.HTTPError as e:
                print(f"🚫 API HTTP Error: {e.response.status_code} - {e.response.text}")
                break
            except Exception as e:
                print(f"An unexpected error occurred during search: {e}")
                break
        
        return items

              

        
                 

# Main function
if __name__ == "__main__":
    scraper = StackOverflowScraper()
    try:
        os.makedirs('outputs', exist_ok=True)
        
        # 1. Get all topics from the new CSV function
        all_topics = get_topics_from_csv()
        all_items_for_run = []

        def save_if_needed():
            if len(all_items_for_run) > 0 and len(all_items_for_run) % 10 == 0:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f'outputs/stackoverflow_progress_{timestamp}.json'
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
            final_filename = 'outputs/stackoverflow_final_results.json'
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