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

class LinkedInJobsScraper:
    def __init__(self):
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
            'min_post_length': 100,
            'min_word_count': 10,
            'max_age_days': 30, # Setting a more reasonable default age
            'max_link_ratio': 0.3,
            'promo_keywords': [ # <-- RENAMED KEY TO MATCH platform_specific.py
                "multi-level marketing", "pyramid scheme", "get rich quick",
                "work from home scheme", "limited time opportunity", "act now",
                "free trial", "webinar", "course"
            ],
            'blacklisted_domains': ['bit.ly', 'tinyurl.com', 't.co']
        }

    def process_search_query(self, search_query: str, all_items: list, save_callback: callable):
        """Drives the job scraping and analysis process with an efficient workflow."""
        try:
            basic_job_listings = self.platform_scraper.search_jobs(search_query, max_jobs=250)
            
            for basic_job_data in basic_job_listings:
                print("\n" + "="*70)
                print(f"Processing Item: {basic_job_data['url']}")
                
                if basic_job_data['url'] in self.processed_urls:
                    if self.verbose_logging: print("Status: SKIPPED - URL already processed.")
                    continue

                full_content = self.platform_scraper.get_full_job_content(basic_job_data['url'])
                if not full_content:
                    if self.verbose_logging: print("Status: SKIPPED - Could not fetch full job description.")
                    continue
                
                job_data = {**basic_job_data, "content": full_content}

                passes, reason = self.platform_scraper._item_passes_filters(job_data, self.filter_config)
                if not passes:
                    if self.verbose_logging: print(f"Status: SKIPPED - Failed pre-filters. Reason: {reason}")
                else:
                    print("Status: Passed Pre-filters. Analyzing for relevance...")
                    job_text = f"{job_data.get('title', '')} {job_data.get('content', '')}".strip()
                    
                    relevance_threshold = self.filter_config.get('relevance_threshold', 0.35)
                    is_relevant, score, new_keywords = self.semantic_analyzer._analyze_text_relevance(
                        job_text, self.global_keywords, relevance_threshold=relevance_threshold
                    )
                    print(f"Relevance Score: {score:.4f} (Threshold: {relevance_threshold})")

                    if is_relevant:
                        print("Status: SCRAPED - Item is relevant.")
                        job_data["relevance_score"] = score
                        job_data["matched_topic"] = search_query
                        job_data["scraped_at"] = datetime.now().isoformat()
                        
                        if self.verbose_logging:
                            print(f"Found {len(new_keywords.values())} semantic phrases: {list(new_keywords.values())}")

                        all_items.append(job_data)
                        self.processed_urls.add(job_data['url'])
                        print(f"✓ Data for job '{job_data['title']}' saved.")
                        
                        if save_callback: save_callback()
                        print(f"📊 Total relevant items so far: {len(all_items)}")
                        
                        self.global_keywords = self.utils._update_global_keywords(new_keywords, self.global_keywords, self.stopwords_extra)
                        self.utils.save_global_keywords(self.global_keywords)
                    else:
                        if self.verbose_logging: print(f"Status: SKIPPED - Relevance score too low.")

                time.sleep(self.delay_seconds)
        except Exception as e:
            print(f"An unexpected error occurred during job search or analysis: {e}")

    def close(self):
        """Safely close platform-specific resources."""
        self.platform_scraper.close()

# The main execution block 
if __name__ == "__main__":
    scraper = LinkedInJobsScraper()
    try:
        os.makedirs('outputs', exist_ok=True)
        all_topics = get_topics_from_csv()
        all_items_for_run = []

        def save_if_needed():
            if len(all_items_for_run) > 0 and len(all_items_for_run) % 10 == 0:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f'outputs/linkedin_jobs_progress_{timestamp}.json'
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
            final_filename = 'outputs/linkedin_jobs_final_results.json'
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