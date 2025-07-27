import os
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv
from github import Github # Import PyGithub library
from github.GithubException import RateLimitExceededException, UnknownObjectException, GithubException

# Import from your other files
from step1_search_terms import get_search_queries
from step3_semantic_analyzer import SemanticAnalyzer
from sentence_transformers import SentenceTransformer, util # Make sure this is imported for semantic analysis utilities

class GitHubScraper:
    def __init__(self):
        """Initialize GitHub scraper with PyGithub."""
        load_dotenv()  # Load environment variables
        
        # Initialize PyGithub with a Personal Access Token
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN not found in .env file. Please generate a PAT and add it.")
        
        self.g = Github(self.github_token)
        print("PyGithub instance initialized successfully.")

        # Initialize the semantic analyzer
        self.semantic_analyzer = SemanticAnalyzer()
        
        # Load categories from JSON file
        try:
            with open('boolean_categories.json', 'r', encoding='utf-8') as f:
                self.categories: List[Dict[str, Any]] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.categories = []
            
        self.category_idx = 0
        
        # Load existing processed URLs to avoid duplicates (now storing GitHub issue/PR URLs)
        try:
            with open('global_url.json', 'r') as f:
                data = json.load(f)
                self.processed_urls = set(data.get('articles_global_urls', []))
                print(f"📂 Loaded {len(self.processed_urls)} processed URLs from global_url.json")
        except (FileNotFoundError, json.JSONDecodeError):
            self.processed_urls = set()
            print("No saved processed URLs found.")

        # Load global keywords
        self.global_keywords = self.load_global_keywords()

        # Load extra stopwords for semantic analysis (handled by SemanticAnalyzer, but keeping for consistency if needed elsewhere)
        try:
            with open('stopwords_extra.json', 'r') as f:
                self.stopwords_extra = set(json.load(f)['stopwords_extra'])
                # print(f"📂 Loaded {len(self.stopwords_extra)} extra stopwords.") # Already printed by SemanticAnalyzer
        except (FileNotFoundError, json.JSONDecodeError):
            self.stopwords_extra = set()
            # print("No extra stopwords file found.")

    def load_global_keywords(self) -> str:
        """Load global keywords from file if available."""
        try:
            with open('global_keywords.json', 'r') as f:
                data = json.load(f)
                self.global_keywords = data.get('global_keywords', '')
                self.category_idx = data.get('category_idx', 0)
                print(f"📂 Loaded global keywords from global_keywords.json")
                return self.global_keywords
        except (FileNotFoundError, json.JSONDecodeError):
            print("No saved global keywords found. Using keywords from the boolean categories file.")
            if self.categories and len(self.categories) > self.category_idx:
                return self.categories[self.category_idx]['to_be_matched'][0]
            return ""

    def save_processed_urls(self):
        """Save the current set of processed URLs to file."""
        try:
            with open('global_url.json', 'w') as f:
                json.dump({'articles_global_urls': list(self.processed_urls)}, f, indent=2)
            print(f"💾 Saved {len(self.processed_urls)} URLs to global_url.json")
        except Exception as e:
            print(f"Error saving processed URLs: {e}")

    def save_global_keywords(self):
        """Save the current global keywords to file."""
        try:
            with open('global_keywords.json', 'w') as f:
                json.dump({
                    'global_keywords': self.global_keywords,
                    'category_idx': self.category_idx,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)
            print(f"💾 Saved global keywords to global_keywords.json")
        except Exception as e:
            print(f"Error saving global keywords: {e}")

    def search_and_get_issues(self, search_query: str, max_items: int = 100, all_items=None, save_callback=None) -> List[Dict]:
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
                    is_item_relevant, relevance_score, new_keywords = self._analyze_text_relevance(item_text, self.global_keywords)
                    print(f"Item Relevance Score: {relevance_score:.4f} (Threshold: 0.4)")
                    
                    if is_item_relevant:
                        item_data = self._extract_issue_data(item)
                        item_data['relevance_score'] = relevance_score
                        
                        # Extract and analyze comments (now limited to top 10 relevant)
                        item_data['comments'] = self._extract_and_analyze_issue_comments(item, top_n=10)

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
                        self._update_global_keywords(new_keywords)
                        self.save_global_keywords()
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

    def _analyze_text_relevance(self, text: str, keywords: str):
        """Helper to analyze relevance of a given text and extract new keywords."""
        if not text or not keywords:
            return False, 0, {}

        try:
            keywords_list = [term.strip() for term in keywords.replace('(', '').replace(')', '').split('OR')]
            to_be_matched_embeddings = self.semantic_analyzer.model.encode(keywords_list, convert_to_tensor=True)
            
            article_embeddings = self.semantic_analyzer.model.encode(text, convert_to_tensor=True)
            
            cosine_similarity = util.semantic_search(article_embeddings, to_be_matched_embeddings, top_k=1)[0][0]['score']

            if cosine_similarity >= 0.4:
                semantic_keywords = self.semantic_analyzer.extract_semantically_relevant_keywords(
                    text, keywords_list, threshold=0.80 
                )
                return True, cosine_similarity, semantic_keywords
            
            return False, cosine_similarity, {}
        except Exception as e:
            print(f"Error in semantic analysis: {e}")
            return False, 0, {}
    
    def _extract_and_analyze_issue_comments(self, issue, top_n: int = 10) -> List[Dict]:
        """
        Extract and analyze comments for relevance from a GitHub Issue/PR.
        Limits the output to the top_n most relevant comments.
        """
        all_relevant_comments_with_scores = []
        try:
            for comment in issue.get_comments():
                comment_text = comment.body
                if comment_text:
                    is_comment_relevant, relevance_score, new_keywords = self._analyze_text_relevance(comment_text, self.global_keywords)
                    # print(f"  Comment Relevance Score: {relevance_score:.4f} (Threshold: 0.35)") # Moved this print to _process_comment for consistency
                    
                    if is_comment_relevant:
                        # Store comment data along with its score
                        comment_data = {
                            'id': comment.id,
                            'author': str(comment.user.login) if comment.user else "N/A",
                            'text': comment_text,
                            'relevance_score': relevance_score,
                            'replies': [] # GitHub comments are not nested
                        }
                        all_relevant_comments_with_scores.append((relevance_score, comment_data, new_keywords))
                        # Update global keywords immediately when a relevant comment is found
                        self._update_global_keywords(new_keywords)

        except Exception as e:
            print(f"Error extracting comments for item {issue.id}: {e}")
        
        # Sort by relevance score in descending order
        all_relevant_comments_with_scores.sort(key=lambda x: x[0], reverse=True)
        
        # Select top N comments
        top_n_comments_data = [comment_tuple[1] for comment_tuple in all_relevant_comments_with_scores[:top_n]]
        
        # This print statement should happen for each individual comment analysis, not here for the list
        # For overall summary, we can print how many top comments were selected.
        print(f"  Selected top {len(top_n_comments_data)} relevant comments.")

        return top_n_comments_data


    def _process_comment(self, comment) -> Optional[Dict]:
        """
        Process a single GitHub comment.
        This function is now primarily for analyzing and extracting data,
        with the filtering/limiting done by _extract_and_analyze_issue_comments.
        """
        # The core logic for relevance analysis and keyword extraction for a single comment
        # is performed here. The decision to include it in the final list and limit the number
        # is handled by the calling function.
        relevant_comment_data = None
        comment_text = comment.body
        if comment_text:
            is_comment_relevant, relevance_score, new_keywords = self._analyze_text_relevance(comment_text, self.global_keywords)
            print(f"  Comment Relevance Score: {relevance_score:.4f} (Threshold: 0.4)")

            if is_comment_relevant:
                relevant_comment_data = {
                    'id': comment.id,
                    'author': str(comment.user.login) if comment.user else "N/A",
                    'text': comment_text,
                    'relevance_score': relevance_score,
                    'replies': [] # GitHub comments are not nested
                }
                # Note: Keyword updating for comments is now done in _extract_and_analyze_issue_comments
                # to ensure keywords are updated even if the comment isn't in the top N final list.
                # However, to be consistent with previous runs that updated global keywords on ANY relevant comment,
                # I'll keep the _update_global_keywords call here. If performance is an issue or
                # a stricter definition of "global" keywords is desired (only from top N comments),
                # this could be moved. For now, maintaining prior behavior of updating keywords for any relevant comment.
                self._update_global_keywords(new_keywords)
                
        return relevant_comment_data


    def _update_global_keywords(self, semantic_keywords: Dict[str, str]):
        """Update global keywords with new ones found during analysis."""
        if semantic_keywords:
            for matched_term, keyword in semantic_keywords.items():
                if keyword in self.stopwords_extra or keyword.lower() in self.global_keywords.lower():
                    continue
                
                keywords_list = [k.strip() for k in self.global_keywords.split('OR')]
                is_duplicate = False
                for existing_kw in keywords_list:
                    if keyword.lower() in existing_kw.lower() or existing_kw.lower() in keyword.lower():
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    self.global_keywords = f"{self.global_keywords} OR {keyword}"
                    print(f"➕ Added new keyword: '{keyword}' (matched with '{matched_term}')")
                    
    def _extract_issue_data(self, item) -> Dict:
        """Extract relevant data from a PyGithub Issue or Pull Request object."""
        # Safely get reaction_score
        reaction_score = 0
        if hasattr(item, 'reactions') and item.reactions is not None:
            if hasattr(item.reactions, 'total_count'):
                reaction_score = item.reactions.total_count
            else:
                try:
                    reaction_score = item.reactions.get('total_count', 0)
                except AttributeError:
                    reaction_score = 0

        return {
            'id': item.id,
            'url': item.html_url,
            'title': item.title,
            'content': item.body,
            'author': str(item.user.login) if item.user else "N/A",
            'date': item.created_at.isoformat(),
            'reaction_score': reaction_score, 
            'comments_count': item.comments 
        }

    def close(self):
        """Save progress before closing."""
        self.save_processed_urls()
        self.save_global_keywords()

if __name__ == "__main__":
    scraper = GitHubScraper() 
    
    try:
        os.makedirs('outputs', exist_ok=True)

        for category_idx in range(len(scraper.categories)):
            print(f"\n{'='*60}")
            category = scraper.categories[category_idx]
            print(f"Processing Category: {category['category']}")
            print(f"{'='*60}")
            
            scraper.category_idx = category_idx
            scraper.global_keywords = category['to_be_matched'][0]
            
            search_queries = get_search_queries(category_idx)
            
            all_items_for_category = []
            def save_if_needed():
                if len(all_items_for_category) > 0 and len(all_items_for_category) % 10 == 0:
                    try:
                        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        with open(f'outputs/github_items_{category_idx}_progress_{timestamp_str}.json', 'w') as f:
                            json.dump(all_items_for_category, f, indent=2)
                        scraper.save_processed_urls()
                        scraper.save_global_keywords()
                        print(f"💾 Saved progress: {len(all_items_for_category)} items at {timestamp_str}")
                    except Exception as e:
                        print(f"⚠️ Error saving progress: {e}")
            
            for query in search_queries:
                print(f"\n--- Query: {query} ---")
                scraper.search_and_get_issues(query, max_items=100, all_items=all_items_for_category, save_callback=save_if_needed)
                print(f"Found {len(all_items_for_category)} total relevant items so far for this category")

            print(f"\nTotal items found for category {category_idx}: {len(all_items_for_category)}")
            
            if all_items_for_category:
                with open(f'outputs/github_items_category_{category_idx}.json', 'w') as f:
                    json.dump(all_items_for_category, f, indent=2)
                print(f"Saved {len(all_items_for_category)} items to outputs/github_items_category_{category_idx}.json")
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Saving progress...")
        scraper.close()
    except Exception as e:
        print(f"\nError during scraping: {e}")
        scraper.close()
    finally:
        scraper.close()