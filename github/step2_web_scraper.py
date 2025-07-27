import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from github import Github
from github.GithubException import RateLimitExceededException, UnknownObjectException, GithubException

from step1_search_terms import get_search_queries
from step3_semantic_analyzer import SemanticAnalyzer
from utils import Utils
from platform_specific import PlatformSpecific


class GitHubScraper:
    def __init__(self):
        """Initialize GitHub scraper with PyGithub."""
        load_dotenv()  # Load environment variables
        self.utils = Utils()
        self.platform_specific = PlatformSpecific()
        self.semantic_analyzer = SemanticAnalyzer()
        
        # Initialize PyGithub with a Personal Access Token
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN not found in .env file. Please generate a PAT and add it.")
        
        self.g = Github(self.github_token)

        self.categories: List[Dict[str, Any]] = json.load(open('boolean_categories.json', 'r', encoding='utf-8'))
        self.category_idx = 0
        self.category_idx, self.processed_urls = 0, set(json.load(open('global_url.json', 'r')).get('articles_global_urls', []))

        # Load global keywords
        self.global_keywords = ""
        self.stopwords_extra = set(json.load(open('stopwords_extra.json', 'r'))['stopwords_extra'])


    def process_search_query(self, search_query: str, max_items: int = 10000, all_items=None, save_callback=None) -> List[Dict]:
        """Search GitHub for relevant issues and pull requests."""
        items = []
        try:
            print(f"Searching GitHub with query: '{search_query}'")
            
            query_str = f"{search_query} is:issue" 
            
            result_count = 0
            for item in self.g.search_issues(query=query_str, sort="updated", order="desc"):
                if result_count >= max_items:
                    break 

                print(f"\n--- Analyzing GitHub Item: {item.url} ---")
                
                if item.html_url in self.processed_urls:
                    print(f"Skipping item: URL '{item.html_url}' already processed.")
                    continue
                
                item_text = f"{item.title or ''} {item.body or ''}"
                if item_text.strip():
                    is_item_relevant, relevance_score, new_keywords = self.semantic_analyzer._analyze_text_relevance(item_text, self.global_keywords)
                    print(f"Item Relevance Score: {relevance_score:.4f} (Threshold: 0.35)")
                    
                    if is_item_relevant:
                        item_data = self.platform_specific._extract_issue_data(item)
                        item_data['relevance_score'] = relevance_score
                        
                        # Extract and analyze comments (now limited to top 10 relevant)
                        item_data['comments'] = self.platform_specific._extract_and_analyze_issue_comments(item, top_n=10)

                        items.append(item_data)
                        self.processed_urls.add(item.html_url)
                        print(f"✓ Scraped relevant item: '{item_data['title'][:50]}...'")
                        result_count += 1
                        
                        if all_items is not None:
                            all_items.append(item_data)
                            if save_callback is not None:
                                save_callback()
                            print(f"📊 Total relevant items so far: {len(all_items)}")
                        
                        # Update global keywords with new keywords from the item
                        self.global_keywords = self.utils._update_global_keywords(new_keywords, self.global_keywords, self.stopwords_extra)
                        self.utils.save_global_keywords(self.global_keywords, self.category_idx)
                    else:
                        print(f"Skipping item: Score is below relevance threshold.")

        except RateLimitExceededException:
            print("🚫 GitHub API rate limit exceeded. Please wait and try again later.")
        except UnknownObjectException as e:
            print(f"⚠️ Could not find object or access denied: {e}")
        except GithubException as e:
            print(f"Error accessing GitHub API: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during search or analysis: {e}")
        
        return items
                 

# Main function
if __name__ == "__main__":
    scraper = GitHubScraper() 
    
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
                        with open(f'outputs/github_items_{category_idx}_progress_{timestamp_str}.json', 'w') as f:
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
                with open(f'outputs/github_items_category_{category_idx}.json', 'w') as f:
                    json.dump(all_items_for_category, f, indent=2)
                print(f"Saved {len(all_items_for_category)} items to outputs/github_items_category_{category_idx}.json")
            
            #########################################################
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Saving progress...")
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords, scraper.category_idx)
    except Exception as e:
        print(f"\nError during scraping: {e}")
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords, scraper.category_idx)
    finally:
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords, scraper.category_idx)