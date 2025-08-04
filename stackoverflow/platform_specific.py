from typing import List, Dict, Any, Set, Tuple
from datetime import datetime
import requests
import os
import re
from urllib.parse import urlparse
from langdetect import detect, LangDetectException

class PlatformSpecific:
    def __init__(self, semantic_analyzer, utils):
        self.semantic_analyzer = semantic_analyzer
        self.utils = utils

    def _item_passes_filters(self, item: Dict, filter_config: Dict) -> Tuple[bool, str]:
        """Applies a series of pre-filters to a Stack Overflow question."""
        title = item.get('title', '')
        body = item.get('body', '')
        item_text = f"{title} {body}".strip()

        # Content Filters
        if len(item_text) < filter_config.get('min_post_length', 100):
            return False, f"Content length less than {filter_config['min_post_length']} characters"
        if len(item_text.split()) < filter_config.get('min_word_count', 10):
            return False, f"Word count less than {filter_config['min_word_count']} words"
        try:
            if detect(item_text) != 'en':
                return False, "Language not English"
        except LangDetectException:
            return False, "Language could not be detected"

        # Age Filter
        creation_ts = item.get('creation_date', 0)
        post_age_days = (datetime.utcnow() - datetime.utcfromtimestamp(creation_ts)).days
        if post_age_days > filter_config.get('max_age_days', 730):
            return False, f"Post is too old ({post_age_days} days)"

        # Engagement Filters
        if item.get('score', 0) < filter_config.get('min_score', 10):
            return False, f"Low score (Score: {item.get('score', 0)})"
        if item.get('answer_count', 0) < filter_config.get('min_answers', 1):
            return False, "Fewer than 1 answer"

        # Spam Prevention
        link_count = len(re.findall(r'https?://', item_text))
        word_count = len(item_text.split())
        link_ratio = (link_count / word_count) if word_count else 0
        if link_ratio > filter_config.get('max_link_ratio', 0.3):
            return False, f"Exceeds max link ratio ({link_ratio:.2f})"
        if any(domain in item_text for domain in filter_config.get('blacklisted_domains', [])):
            return False, "Contains blacklisted domain"

        return True, "Passed"

    def _extract_post_data(self, post: Dict) -> Dict:
        """Extracts and formats key data from a Stack Overflow post."""
        return {
            'id': post['question_id'],
            'url': post['link'],
            'title': post['title'],
            'content': post.get('body', ''),
            'author': post.get('owner', {}).get('display_name', 'N/A'),
            'date': datetime.fromtimestamp(post.get('creation_date')).isoformat() if post.get('creation_date') else 'N/A',
            'score': post.get('score', 0),
            'views': post.get('view_count', 0),
            'comments_count': post.get('answer_count', 0)
        }

    def _extract_and_analyze_answers(self, question_id: int, global_keywords: str, stopwords_extra: Set[str], relevance_threshold: float, top_n: int = 10, verbose_logging: bool = False) -> Tuple[str, List[Dict]]:
        """Fetches, analyzes, and selects the top N most relevant answers."""
        scored_answers = []
        try:
            response = requests.get(
                f"https://api.stackexchange.com/2.3/questions/{question_id}/answers",
                params={
                    "order": "desc", "sort": "votes", "site": "stackoverflow",
                    "filter": "withbody", "key": os.getenv("STACKOVERFLOW_API_TOKEN")
                }
            )
            response.raise_for_status()
            answers = response.json().get('items', [])

            for answer in answers:
                answer_text = answer.get('body', '')
                is_relevant, score, new_keywords = self.semantic_analyzer._analyze_text_relevance(answer_text, global_keywords, relevance_threshold=relevance_threshold)
                if verbose_logging:
                    print(f"  Answer Relevance Score: {score:.4f} (Threshold: {relevance_threshold})")
                if is_relevant:
                    scored_answers.append({'score': score, 'answer': answer, 'keywords': new_keywords})
        except Exception as e:
            print(f"Error retrieving answers for question {question_id}: {e}")
            return global_keywords, []

        # Sort by relevance and select top N
        scored_answers.sort(key=lambda x: x['score'], reverse=True)
        top_answers = scored_answers[:top_n]

        # Aggregate keywords and format data from ONLY the top N answers
        final_answers_data = []
        updated_keywords = global_keywords
        for item in top_answers:
            answer_obj = item['answer']
            final_answers_data.append({
                'id': answer_obj['answer_id'],
                'author': answer_obj.get('owner', {}).get('display_name', 'N/A'),
                'text': answer_obj.get('body', ''),
                'relevance_score': item['score'],
                'replies': []
            })
            updated_keywords = self.utils._update_global_keywords(item['keywords'], updated_keywords, stopwords_extra)

        if verbose_logging:
            print(f"  Selected top {len(final_answers_data)} relevant answers and aggregated their keywords.")

        return updated_keywords, final_answers_data