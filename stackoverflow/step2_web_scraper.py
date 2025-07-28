import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

from step1_search_terms import get_search_queries
from step3_semantic_analyzer import SemanticAnalyzer
from utils import Utils
from platform_specific import PlatformSpecific
import requests



class StackoverflowScraper:
    def __init__(self):
        """Initialize Stackoverflow scraper."""
        load_dotenv()  # Load environment variables
        self.utils = Utils()
        
        self.semantic_analyzer = SemanticAnalyzer()
        self.platform_specific = PlatformSpecific(self.semantic_analyzer, self.utils)

        
        # Initialize Stack Exchange API components
        self.stackoverflow_base_url = "https://api.stackexchange.com/2.3"
        self.stackoverflow_session = requests.Session()
        self.stackoverflow_token = os.getenv('STACKOVERFLOW_API_TOKEN')
        if not self.stackoverflow_token:
            raise ValueError("stack token not found in .env file. Please generate a PAT and add it.")
        
        

        self.categories: List[Dict[str, Any]] = json.load(open('boolean_categories.json', 'r', encoding='utf-8'))
        self.category_idx = 0
        self.category_idx, self.processed_urls = 0, set(json.load(open('global_url.json', 'r')).get('articles_global_urls', []))

        # Load global keywords
        self.global_keywords = ""
        self.stopwords_extra = set(json.load(open('stopwords_extra.json', 'r'))['stopwords_extra'])


    def process_search_query(self, search_query: str, max_items: int = 10000, all_items=None, save_callback=None) -> List[Dict]:
        """Search Stack Overflow for relevant questions and analyze top answers."""
        items = []
        try:
            print(f"Searching Stack Overflow with query: '{search_query}'")

            endpoint = f"{self.stackoverflow_base_url}/search/advanced"
            query_params = {
                'q': search_query,         # ✅ full-text natural language search
                'sort': 'relevance',
                'order': 'desc',
                'site': 'stackoverflow',
                'filter': 'withbody',
                'pagesize': 100,
                "key": self.stackoverflow_token
            }

            page = 1
            result_count = 0
            while result_count < max_items:
                query_params["page"] = page
                response = requests.get(endpoint, params=query_params)
                data = response.json()
                

                questions = data.get("items", [])

                if not questions:
                    break

                for post in questions:
                    if result_count >= max_items:
                        break

                    print(f"\n--- Analyzing Stack Overflow Post: {post['link']} ---")
                    if post['link'] in self.processed_urls:
                        print(f"Skipping post: URL '{post['link']}' already processed.")
                        continue

                    item_text = f"{post.get('title', '')} {post.get('body', '')}".strip()
                    if item_text:
                        is_relevant, score, new_keywords = self.semantic_analyzer._analyze_text_relevance(item_text, self.global_keywords)
                        print(f"Post Relevance Score: {score:.4f} (Threshold: 0.35)")

                        if is_relevant:
                            post_data = self.platform_specific._extract_post_data(post)
                            post_data["matched_topic"] = search_query  

                            post_data["relevance_score"] = score
                            relevant_comments = self.platform_specific._extract_and_analyze_answers(
                                post['question_id'], self.global_keywords, self.stopwords_extra, top_n=10)

                            post_data['comments'] = relevant_comments
                            

                            items.append(post_data)
                            self.processed_urls.add(post['link'])
                            print(f"✓ Scraped relevant post: '{post_data['title'][:50]}...'")
                            result_count += 1

                            if all_items is not None:
                                all_items.append(post_data)
                                if save_callback is not None:
                                    save_callback()
                                print(f"📊 Total relevant items so far: {len(all_items)}")

                            self.global_keywords = self.utils._update_global_keywords(new_keywords, self.global_keywords, self.stopwords_extra)
                            self.utils.save_global_keywords(self.global_keywords, self.category_idx)
                        else:
                            print("Skipping post: Score is below relevance threshold.")

                page += 1


        except requests.exceptions.HTTPError as e:
            print(f"🚫 Stack Overflow API HTTP Error: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Network or request error while scraping Stack Overflow: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during Stack Overflow search or analysis: {e}")

        return items               

        
                 

# Main function
if __name__ == "__main__":
    scraper = StackoverflowScraper() 
    
    try:
        os.makedirs('outputs', exist_ok=True)

        for category_idx in range(len(scraper.categories)):
            
            #########################################################
            # Print category info
            print(f"\n{'='*60}")
            category = scraper.categories[category_idx]
            print(f"Processing Category: {category['category']}")
            print(f"{'='*60}")
            
            scraper.category_idx = category_idx
            scraper.global_keywords = category['to_be_matched'][0]
            print(f"Global Keywords: length {len(scraper.global_keywords)}")
            
            search_queries = get_search_queries(category_idx)
            
            #########################################################
            # Save progress

            all_items_for_category = []
            def save_if_needed():
                if len(all_items_for_category) > 0 and len(all_items_for_category) % 10 == 0:
                    try:
                        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        with open(f'outputs/stackoverflow_items_{category_idx}_progress_{timestamp_str}.json', 'w') as f:
                            json.dump(all_items_for_category, f, indent=2)
                        scraper.utils.save_processed_urls(scraper.processed_urls)
                        scraper.utils.save_global_keywords(scraper.global_keywords, scraper.category_idx)
                        print(f"💾 Saved progress: {len(all_items_for_category)} items at {timestamp_str}")
                    except Exception as e:
                        print(f"⚠️ Error saving progress: {e}")
        
            #########################################################
            # Process each search query
            for query in search_queries:
                print(f"\n--- Query: {query} ---")
                scraper.process_search_query(query, max_items=10000, all_items=all_items_for_category, save_callback=save_if_needed)
                print(f"Found {len(all_items_for_category)} total relevant items so far for this category")

            #########################################################

            print(f"\nTotal items found for category {category_idx}: {len(all_items_for_category)}")
            
            #########################################################
            # Save category items
            if all_items_for_category:
                with open(f'outputs/stackoverflow_category_{category_idx}.json', 'w') as f:
                    json.dump(all_items_for_category, f, indent=2)
                print(f"Saved {len(all_items_for_category)} items to outputs/stackoverflow_items_category_{category_idx}.json")
            
            #########################################################
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Saving progress...")
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords, scraper.category_idx)
    except Exception as e:
        print(f"\nError during scraping: {e}")
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords, scraper.category_idx)
    finally:
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords, scraper.category_idx)