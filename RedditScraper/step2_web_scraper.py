import praw
from dotenv import load_dotenv
import os
import json
import pandas as pd
from typing import List, Dict, Optional, Any
from datetime import datetime

# Import from your other files
from step1_search_terms import get_search_queries
from step3_semantic_analyzer import SemanticAnalyzer

class RedditScraper:
    def __init__(self):
        """Initialize Reddit scraper with PRAW."""
        load_dotenv()  # Load environment variables
        
        # Initialize PRAW with credentials from .env
        self.reddit = praw.Reddit(
            client_id=os.getenv('REDDIT_CLIENT_ID'),
            client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
            user_agent=os.getenv('REDDIT_USER_AGENT')
        )
        print("PRAW instance initialized successfully.")

        # Initialize the semantic analyzer
        self.semantic_analyzer = SemanticAnalyzer()
        
        # Load categories from JSON file
        try:
            with open('boolean_categories.json', 'r', encoding='utf-8') as f:
                self.categories: List[Dict[str, Any]] = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.categories = []
            
        self.category_idx = 0
        
        # Load existing processed IDs to avoid duplicates
        try:
            with open('processed_reddit_ids.json', 'r') as f:
                data = json.load(f)
                self.processed_ids = set(data.get('processed_ids', []))
        except (FileNotFoundError, json.JSONDecodeError):
            self.processed_ids = set()

        # Load global keywords
        self.global_keywords = self.load_global_keywords()

        # Load extra stopwords for semantic analysis
        try:
            with open('stopwords_extra.json', 'r') as f:
                self.stopwords_extra = set(json.load(f)['stopwords_extra'])
        except (FileNotFoundError, json.JSONDecodeError):
            self.stopwords_extra = set()

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
            print("No saved global keywords found.")
            # Default to the first category's to_be_matched terms
            if self.categories and len(self.categories) > self.category_idx:
                return self.categories[self.category_idx]['to_be_matched'][0]
            return ""

    def save_processed_ids(self):
        """Save the current set of processed IDs to file."""
        try:
            with open('processed_reddit_ids.json', 'w') as f:
                json.dump({'processed_ids': list(self.processed_ids)}, f, indent=2)
            print(f"Saved {len(self.processed_ids)} post IDs to processed_reddit_ids.json")
        except Exception as e:
            print(f"Error saving processed IDs: {e}")

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

    def search_and_get_posts(self, search_query: str, max_posts: int = 300, all_posts=None, save_callback=None) -> List[Dict]:
        """Search Reddit and get relevant posts and comments."""
        posts = []
        try:
            # Use PRAW's search method
            print(f"Searching Reddit with query: {search_query}")
            for submission in self.reddit.subreddit('all').search(search_query, limit=max_posts):
                if submission.id in self.processed_ids:
                    print(f"Post ID already processed: {submission.id}")
                    continue
                
                # Check for relevance of the post itself
                post_text = f"{submission.title} {submission.selftext}"
                if post_text:
                    is_post_relevant, relevance_score, new_keywords = self._analyze_text_relevance(post_text, self.global_keywords)
                    
                    if is_post_relevant:
                        post_data = self._extract_submission_data(submission)
                        post_data['relevance_score'] = relevance_score
                        
                        # Extract and analyze comments
                        post_data['comments'] = self._extract_and_analyze_comments(submission, new_keywords)

                        posts.append(post_data)
                        self.processed_ids.add(submission.id)
                        print(f"✓ Scraped relevant post: {post_data['title'][:50]}...")
                        
                        if all_posts is not None:
                            all_posts.append(post_data)
                            if save_callback is not None:
                                save_callback()
                            print(f"📊 Total posts so far: {len(all_posts)}")
                        
                        # Update global keywords with new keywords from the post
                        self._update_global_keywords(new_keywords)
                        self.save_global_keywords()

        except Exception as e:
            print(f"Error in search: {e}")
        
        return posts

    def _analyze_text_relevance(self, text: str, keywords: str):
        """Helper to analyze relevance of a given text and extract new keywords."""
        if not text or not keywords:
            return False, 0, {}

        try:
            # Prepare embeddings for semantic analysis
            keywords_list = [term.strip() for term in keywords.replace('(', '').replace(')', '').split('OR')]
            to_be_matched_embeddings = self.semantic_analyzer.model.encode(keywords, convert_to_tensor=True)
            
            # Check relevance using the entire post text
            article_embeddings = self.semantic_analyzer.model.encode(text, convert_to_tensor=True)
            cosine_similarity = self.semantic_analyzer.calculate_cosine_similarity(article_embeddings, to_be_matched_embeddings)

            if cosine_similarity >= 0.35:

                # Extract semantically relevant keywords from the text
                semantic_keywords = self.semantic_analyzer.extract_semantically_relevant_keywords(
                    text, keywords_list, threshold=0.65
                )
                print(f"✅ Relevant (Score: {cosine_similarity:.2f}): {text[:50]}...")
                return True, cosine_similarity, semantic_keywords
            else:
                print(f"❌ Skipped (Score: {cosine_similarity:.2f}): {text[:50]}...")
                return False, cosine_similarity, {}
        except Exception as e:
            print(f"Error in semantic analysis: {e}")
            return False, 0, {}
    
    def _extract_and_analyze_comments(self, submission, post_keywords: Dict[str, str]) -> List[Dict]:
        """Extract and analyze comments for relevance."""
        relevant_comments = []
        try:
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list():
                if isinstance(comment, praw.models.MoreComments):
                    continue
                    
                comment_text = comment.body
                if comment_text:
                    is_comment_relevant, relevance_score, new_keywords = self._analyze_text_relevance(
                        comment_text, self.global_keywords
                    )
                    
                    if is_comment_relevant:
                        relevant_comments.append({
                            "comment_id": comment.id,  # Changed from 'id'
                            "author": str(comment.author),
                            "body": comment_text,  # Changed from 'text'
                            "score": comment.score,  # Added
                            "created_utc": datetime.fromtimestamp(comment.created_utc).isoformat(),  # Added
                            "relevance_score": relevance_score,
                            "replies": []  # Added empty list for replies
                        })
                        self._update_global_keywords(new_keywords)
        except Exception as e:
            print(f"Error extracting comments: {e}")
        return relevant_comments

    def _update_global_keywords(self, semantic_keywords: Dict[str, str]):
        """Update global keywords with new ones found during analysis."""
        if semantic_keywords:
            for matched_term, keyword in semantic_keywords.items():
                if keyword in self.stopwords_extra or keyword.lower() in self.global_keywords.lower():
                    continue
                
                # Check for partial matches to prevent duplicates
                keywords_list = [k.strip() for k in self.global_keywords.split('OR')]
                is_duplicate = False
                for existing_kw in keywords_list:
                    if keyword.lower() in existing_kw.lower() or existing_kw.lower() in keyword.lower():
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    print(f"🔍 New Keyword: '{keyword}' (Matched: '{matched_term}')")
                    self.global_keywords = f"{self.global_keywords} OR {keyword}"
                    print(f"➕ Added new keyword: '{keyword}' (matched with '{matched_term}')")
                    
    def _extract_submission_data(self, submission) -> Dict:
        return {
            "platform": "reddit",  # Hardcoded as requested
            "post_id": submission.id,
            "url": f"https://www.reddit.com{submission.permalink}",
            "content": submission.selftext,
            "title": submission.title,
            "topic": self.categories[self.category_idx]['category'],  # Current category name
            "author": str(submission.author),
            "subreddit": str(submission.subreddit),
            "created_utc": datetime.fromtimestamp(submission.created_utc).isoformat(),
            "score": submission.score,
            "upvote_ratio": submission.upvote_ratio,
            "num_comments": submission.num_comments,
            "relevance_score": None,  # Will be set later
            "comments": []  # Will be populated later
        }

    def close(self):
        """Save progress before closing."""
        self.save_processed_ids()
        self.save_global_keywords()

if __name__ == "__main__":
    scraper = RedditScraper()
    
    try:
        for category_idx in range(len(scraper.categories)):
            print(f"\n{'='*60}")
            category = scraper.categories[category_idx]
            print(f"Processing Category: {category['category']}")
            print(f"{'='*60}")
            
            # Update category index and global keywords
            scraper.category_idx = category_idx
            scraper.global_keywords = category['to_be_matched'][0]
            
            # Get the single search query
            search_queries = get_search_queries(category_idx)
            
            all_posts = []
            def save_if_needed():
                if len(all_posts) > 0 and len(all_posts) % 10 == 0:
                    try:
                        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        df = pd.DataFrame(all_posts)
                        with open(f'outputs/reddit_posts_category_{category_idx}_progress_{timestamp_str}.json', 'w') as f:
                            json.dump(all_posts, f, indent=2)
                        scraper.save_processed_ids()
                        scraper.save_global_keywords()
                        print(f"💾 Saved progress: {len(all_posts)} posts at {timestamp_str}")
                    except Exception as e:
                        print(f"⚠️ Error saving progress: {e}")
            
            for query in search_queries:
                print(f"\n--- Query: {query} ---")
                scraper.search_and_get_posts(query, max_posts=300, all_posts=all_posts, save_callback=save_if_needed)
                print(f"Found {len(all_posts)} total relevant posts so far for this category")

            print(f"\nTotal posts found for category {category_idx}: {len(all_posts)}")
            
            # Save final results for this category
            if all_posts:
                with open(f'outputs/reddit_posts_category_{category_idx}.json', 'w') as f:
                    json.dump(all_posts, f, indent=2)
                print(f"Saved {len(all_posts)} posts to outputs/reddit_posts_{category_idx}.csv and .json")
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Saving progress...")
        scraper.close()
    except Exception as e:
        print(f"\nError during scraping: {e}")
        scraper.close()
    finally:
        scraper.close()