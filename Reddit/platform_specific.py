from datetime import datetime
from typing import Dict, List, Tuple
import praw
import re
from langdetect import detect, LangDetectException

class PlatformSpecific:
    def __init__(self, semantic_analyzer=None, utils=None):
        self.semantic_analyzer = semantic_analyzer
        self.utils = utils

    def _item_passes_filters(self, submission: praw.models.Submission, filter_config: Dict) -> Tuple[bool, str]:
        """Applies a series of pre-filters to a Reddit submission."""
        post_text = f"{submission.title} {submission.selftext}".strip()

        # Content Filters
        if len(post_text) < filter_config.get('min_post_length', 100):
            return False, f"Content length less than {filter_config['min_post_length']}"
        if len(post_text.split()) < filter_config.get('min_word_count', 10):
            return False, f"Word count less than {filter_config['min_word_count']}"
        try:
            if detect(post_text) != 'en':
                return False, "Language not English"
        except LangDetectException:
            return False, "Language could not be detected"
        
        post_date = datetime.fromtimestamp(submission.created_utc)
        age_days = (datetime.now() - post_date).days
        if age_days > filter_config.get('max_age_days', 730):
            return False, f"Post is too old ({age_days} days)"

        # Engagement Thresholds
        if submission.score < filter_config.get('reddit_min_score', 50):
            return False, f"Low score (Score: {submission.score})"
        if submission.num_comments < filter_config.get('reddit_min_comments', 10):
            return False, f"Not enough comments (Comments: {submission.num_comments})"

        # Spam Prevention
        if any(kw in post_text.lower() for kw in filter_config.get('promo_keywords', [])):
            return False, "Detected as promotional content"
        link_ratio = (len(re.findall(r'https?://', post_text)) / len(post_text.split())) if len(post_text.split()) > 0 else 0
        if link_ratio > filter_config.get('max_link_ratio', 0.3):
            return False, f"Exceeds max link ratio ({link_ratio:.2f})"
        if any(domain in post_text for domain in filter_config.get('blacklisted_domains', [])):
            return False, "Contains blacklisted domain"

        return True, "Passed"

    def _extract_submission_data(self, submission: praw.models.Submission) -> Dict:
        """Extracts key data from a PRAW submission object."""
        return {
            "platform": "reddit", "post_id": submission.id,
            "url": f"https://www.reddit.com{submission.permalink}",
            "content": submission.selftext, "title": submission.title,
            "author": str(submission.author), "subreddit": str(submission.subreddit),
            "created_utc": datetime.fromtimestamp(submission.created_utc).isoformat(),
            "score": submission.score, "upvote_ratio": submission.upvote_ratio,
            "num_comments": submission.num_comments
        }

    def _extract_and_analyze_comments(self, submission: praw.models.Submission, global_keywords: str, verbose_logging: bool, relevance_threshold: float, top_n: int = 20) -> List[Dict]:
        """Extracts and analyzes the top N comments for relevance."""
        relevant_comments = []
        try:
            submission.comment_sort = 'top'
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list()[:top_n]:
                if isinstance(comment, praw.models.MoreComments) or not comment.body:
                    continue
                is_comment_relevant, score, _ = self.semantic_analyzer._analyze_text_relevance(comment.body, global_keywords, relevance_threshold=relevance_threshold)
                if verbose_logging: print(f"  Comment Relevance Score: {score:.4f} (Threshold: {relevance_threshold})")
                
                if is_comment_relevant:
                    relevant_comments.append({
                        "comment_id": comment.id, "author": str(comment.author),
                        "body": comment.body, "score": comment.score,
                        "created_utc": datetime.fromtimestamp(comment.created_utc).isoformat(),
                        "relevance_score": score
                    })
        except Exception as e:
            print(f"Error extracting comments: {e}")
        return relevant_comments