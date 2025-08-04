import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

from langdetect import LangDetectException, detect


class PlatformSpecific:
    def __init__(self):
        pass

    def _item_passes_filters(self, item: Any, promotional_keywords: List[str], blacklisted_domains: List[str]) -> Tuple[bool, str]:
       
        post_content = item.body or ""
        post_title = item.title or ""
        full_text = f"{post_title} {post_content}"
        reaction_count = 0
        if hasattr(item, 'reactions'):
            if hasattr(item.reactions, 'total_count'):
                reaction_count = item.reactions.total_count
            elif isinstance(item.reactions, dict):
                reaction_count = item.reactions.get('total_count', 0)
        if len(post_content) < 100:
            return False, "Content length is less than 100 characters"
        if len(post_content.split()) < 10:
            return False, "Word count is less than 10 words"
        age_in_days = (datetime.now(item.created_at.tzinfo) - item.created_at).days
        if age_in_days > 730:
            return False, f"Post is too old ({age_in_days} days)"
        try:
            lang = detect(full_text)
            if lang != 'en':
                return False, f"Language not English (detected: {lang})"
        except LangDetectException:
            return False, "Language could not be detected"
        if not (reaction_count >= 2 or item.comments >= 3):
            return False, f"Low engagement (Reactions: {reaction_count}, Comments: {item.comments})"
        for keyword in promotional_keywords:
            if keyword in full_text.lower():
                return False, f"Contains promotional keyword: '{keyword}'"
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', post_content)
        num_links = len(urls)
        num_words = len(post_content.split())
        if num_words > 0:
            link_ratio = num_links / num_words
            if link_ratio > 0.30:
                return False, f"Exceeds max link ratio ({link_ratio:.2f} > 0.30)"
        for url in urls:
            domain = urlparse(url).netloc
            if domain in blacklisted_domains:
                return False, f"Contains blacklisted domain: '{domain}'"
        return True, "Passed"

    def _get_top_relevant_comments(self, issue: Any, semantic_analyzer: Any, global_keywords: str, verbose_logging: bool, relevance_threshold: float, top_n: int = 5) -> (List[Dict], Dict):
        """
        Updated to accept verbose_logging to control print statements.
        """
        scored_comments = []
        try:
            for comment in issue.get_comments():
                comment_text = comment.body
                if comment_text:
                    is_relevant, score, new_keywords = semantic_analyzer._analyze_text_relevance(comment_text, global_keywords, relevance_threshold=relevance_threshold)
                    if verbose_logging: # Use the passed-in parameter
                        print(f"  Comment Relevance Score: {score:.4f} (Threshold: 0.35)")
                    
                    if is_relevant:
                        scored_comments.append({
                            "score": score,
                            "comment_obj": comment,
                            "new_keywords": new_keywords
                        })
        except Exception as e:
            print(f"Error extracting comments for item {issue.id}: {e}")
            return [], {}
        
        scored_comments.sort(key=lambda x: x['score'], reverse=True)
        top_scored_comments = scored_comments[:top_n]
        
        final_comments_data = []
        final_new_keywords = {}
        for item in top_scored_comments:
            comment_obj = item['comment_obj']
            final_comments_data.append({
                'id': comment_obj.id,
                'author': str(comment_obj.user.login) if comment_obj.user else "N/A",
                'text': comment_obj.body,
                'relevance_score': item['score'],
                'replies': []
            })
            final_new_keywords.update(item['new_keywords'])

        if verbose_logging: 
            print(f"  Selected top {len(final_comments_data)} relevant comments and aggregated their keywords.")

        return final_comments_data, final_new_keywords

    def _extract_issue_data(self, item: Any) -> Dict:
        
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