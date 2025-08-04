import json
import os
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv
from github import Github
from github.GithubException import (GithubException, RateLimitExceededException,
                                    UnknownObjectException)

from platform_specific import PlatformSpecific
from search_terms import get_topics_from_csv
from semantic_analyzer import SemanticAnalyzer
from utils import Utils
import time


class GitHubScraper:
    def __init__(self):
        """Initialize GitHub scraper with PyGithub."""
        load_dotenv()
        self.utils = Utils()
        self.platform_specific = PlatformSpecific()
        self.semantic_analyzer = SemanticAnalyzer()
        
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN not found in .env file. Please generate a PAT and add it.")
        
        self.g = Github(self.github_token)

        
        self.processed_urls = set(json.load(open('global_url.json', 'r')).get('articles_global_urls', []))

        self.global_keywords = ""
        self.stopwords_extra = set(json.load(open('stopwords_extra.json', 'r'))['stopwords_extra'])

        self.promotional_keywords = ['buy now', 'sale', 'discount', 'promotion', 'offer', 'webinar', 'course', 'free trial']
        self.blacklisted_domains = [
            # Common URL Shorteners
            'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'is.gd', 'ow.ly', 'buff.ly',
            'adf.ly', 'shorte.st', 'bc.vc',

            # Common Ad & Tracking Domains
            'doubleclick.net', 'adservice.google.com', 'googlesyndication.com',
            'analytics.google.com', 'criteo.com', 'taboola.com', 'outbrain.com'
        ]
        self.verbose_logging = True
        

    def process_search_query(self, search_query: str, max_items: int = 10000, all_items=None, save_callback=None, relevance_threshold: float = 0.35) -> List[Dict]:
        """Search GitHub for relevant issues, calling the filter function from platform_specific."""
        items = []
        try:
            print(f"Searching GitHub with query: '{search_query}'")
            
            query_str = f"{search_query} is:issue" 
            
            result_count = 0
            for item in self.g.search_issues(query=query_str, sort="updated", order="desc"):
                if result_count >= max_items:
                    break
                
                print("\n" + "="*70)
                print(f"Processing Item: {item.html_url}")
                
                if item.html_url in self.processed_urls:
                    if self.verbose_logging:
                        print("Status: SKIPPED - URL already processed.")
                    continue

                passes, reason = self.platform_specific._item_passes_filters(
                    item, self.promotional_keywords, self.blacklisted_domains
                )
                if not passes:
                    if self.verbose_logging:
                        print(f"Status: SKIPPED - Failed pre-filters. Reason: {reason}")
                        time.sleep(1)
                    continue
                
                print("Status: Passed Pre-filters. Analyzing for relevance...")
                time.sleep(1)

                item_text = f"{item.title or ''} {item.body or ''}"
                if item_text.strip():
                    is_item_relevant, relevance_score, new_keywords_from_item = self.semantic_analyzer._analyze_text_relevance(item_text, self.global_keywords, relevance_threshold=relevance_threshold)
                    print(f"Relevance Score: {relevance_score:.4f} (Threshold: {relevance_threshold})")
                    
                    if is_item_relevant:
                        print("Status: SCRAPED - Item is relevant.")
                        time.sleep(1)
                        item_data = self.platform_specific._extract_issue_data(item)
                        item_data['relevance_score'] = relevance_score
                        
                        # Updated call to include the verbose_logging flag
                        top_comments, new_keywords_from_comments = self.platform_specific._get_top_relevant_comments(
                            issue=item,
                            semantic_analyzer=self.semantic_analyzer,
                            global_keywords=self.global_keywords,
                            verbose_logging=self.verbose_logging,
                            relevance_threshold=relevance_threshold,
                            top_n=5
                        )
                        item_data['comments'] = top_comments

                        all_new_keywords = {**new_keywords_from_item, **new_keywords_from_comments}
                        if self.verbose_logging and all_new_keywords:
                            print(f"Found Phrases: {len(list(all_new_keywords.values()))} -  {list(all_new_keywords.values())}")


                        items.append(item_data)
                        self.processed_urls.add(item.html_url)
                        print(f"✓ Data for '{item_data['title'][:50]}...' saved.")
                        result_count += 1
                        
                        if all_items is not None:
                            all_items.append(item_data)
                            if save_callback is not None:
                                save_callback()
                            print(f"📊 Total relevant items so far: {len(all_items)}")
                        
                        self.global_keywords = self.utils._update_global_keywords(all_new_keywords, self.global_keywords, self.stopwords_extra)
                        self.utils.save_global_keywords(self.global_keywords)
                    else:
                        if self.verbose_logging:
                            print(f"Status: SKIPPED - Relevance score too low.")
                # Pause at the end of processing each item
                time.sleep(2)  
            # time.sleep(5)          

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
        
        # 1. Get all topics from the CSV file
        all_topics = get_topics_from_csv()
        all_items_for_run = []

        def save_if_needed():
            if len(all_items_for_run) > 0 and len(all_items_for_run) % 10 == 0:
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f'outputs/github_progress_{timestamp}.json'
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

        # 5. Save the final combined results at the end
        if all_items_for_run:
            final_filename = 'outputs/github_final_results.json'
            with open(final_filename, 'w', encoding='utf-8') as f:
                json.dump(all_items_for_run, f, indent=2)
            print(f"Saved {len(all_items_for_run)} final items to {final_filename}")

    
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Saving progress...")
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords, )
    except Exception as e:
        print(f"\nError during scraping: {e}")
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords, )
    finally:
        scraper.utils.close(scraper.processed_urls, scraper.global_keywords, )