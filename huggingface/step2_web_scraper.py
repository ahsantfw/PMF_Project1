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
import time


class HuggingFaceScraper:
    def __init__(self):
        """Initialize Stackoverflow scraper."""
        load_dotenv()  # Load environment variables
        self.utils = Utils()
        
        self.semantic_analyzer = SemanticAnalyzer()
        self.platform_specific = PlatformSpecific(self.semantic_analyzer, self.utils)

        
        # Initialize Stack Exchange API components
        
        # self.hf_token = os.getenv('HF_API_TOKEN')
        # if not self.hf_token:
        #     raise ValueError("stack token not found in .env file. Please generate a PAT and add it.")
        
        

        self.categories: List[Dict[str, Any]] = json.load(open('boolean_categories.json', 'r', encoding='utf-8'))
        self.category_idx = 0
        self.category_idx, self.processed_urls = 0, set(json.load(open('global_url.json', 'r')).get('articles_global_urls', []))

        # Load global keywords
        self.global_keywords = ""
        self.stopwords_extra = set(json.load(open('stopwords_extra.json', 'r'))['stopwords_extra'])


    def process_search_query(self, search_query: str, max_items: int = 10000, all_items=None, save_callback=None) -> List[Dict]:
        """Search Hugging Face for relevant models/datasets and analyze their content.""" # Updated docstring
        items = []
        try:
            print(f"Searching Hugging Face models and datasets with query: '{search_query}'")
            
            # Use the new generalized search function from platform_specific
            # We'll search for both models and datasets here.
            hf_found_items = self.platform_specific._search_huggingface_items(search_query, limit=max_items, item_type="all")
            
            result_count = 0
            for hf_item in hf_found_items:
                if result_count >= max_items:
                    break

                item_url = hf_item['url']
                item_type = hf_item['type'] # 'model' or 'dataset'
                item_id = hf_item['id']

                print(f"\n--- Analyzing Hugging Face {item_type.capitalize()}: {item_url} ---")
                
                if item_url in self.processed_urls:
                    print(f"Skipping {item_type}: URL '{item_url}' already processed.")
                    continue

                # Fetch the full description (README) to use as the content for semantic analysis
                item_description = self.platform_specific._get_item_description(item_id, item_type)
                
                # Use the model_id/dataset_id as title and the fetched description as content
                item_text = f"{item_id} {item_description}".strip()
                
                if item_text:
                    is_relevant, score, new_keywords = self.semantic_analyzer._analyze_text_relevance(item_text, self.global_keywords)
                    print(f"{item_type.capitalize()} Relevance Score: {score:.4f} (Threshold: 0.35)")

                    if is_relevant:
                        # Use the new generalized extraction function
                        extracted_data = self.platform_specific._extract_item_data(hf_item, item_type)
                        extracted_data["content"] = item_description # Set the content here
                        extracted_data["relevance_score"] = score
                        extracted_data["matched_topic"] = search_query  
                        
                        # Discussions are currently skipped as per platform_specific.py
                        extracted_data['comments_count'] = 0 # Explicitly set
                        
                        items.append(extracted_data)
                        self.processed_urls.add(item_url)
                        print(f"✓ Scraped relevant {item_type}: '{extracted_data['title'][:50]}...'")
                        result_count += 1

                        if all_items is not None:
                            all_items.append(extracted_data)
                            if save_callback is not None:
                                save_callback()
                            print(f"📊 Total relevant items so far: {len(all_items)}")

                        self.global_keywords = self.utils._update_global_keywords(new_keywords, self.global_keywords, self.stopwords_extra)
                        self.utils.save_global_keywords(self.global_keywords, self.category_idx)
                    else:
                        print(f"Skipping {item_type}: Score is below relevance threshold.")
                else:
                    print(f"Skipping {item_type}: No content to analyze.")

        except requests.exceptions.HTTPError as e:
            print(f"🚫 Hugging Face API HTTP Error: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Network or request error while scraping Hugging Face: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during Hugging Face search or analysis: {e}")

        return items 


                         

# Main function
if __name__ == "__main__":
    scraper = HuggingFaceScraper() 
    
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
                        with open(f'outputs/huggingface_{category_idx}_progress_{timestamp_str}.json', 'w') as f:
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
                with open(f'outputs/huggingface_category_{category_idx}.json', 'w') as f:
                    json.dump(all_items_for_category, f, indent=2)
                print(f"Saved {len(all_items_for_category)} items to outputs/huggingface_items_category_{category_idx}.json")
            
            #########################################################
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Saving progress...")
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords, scraper.category_idx)
    except Exception as e:
        print(f"\nError during scraping: {e}")
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords, scraper.category_idx)
    finally:
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords, scraper.category_idx)