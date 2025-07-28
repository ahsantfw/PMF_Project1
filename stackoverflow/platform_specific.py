from typing import List, Dict, Optional, Any
from datetime import datetime # For converting timestamps to ISO format
import requests
import os
from step3_semantic_analyzer import SemanticAnalyzer

class PlatformSpecific:
    def __init__(self, semantic_analyzer, utils):
        self.semantic_analyzer = semantic_analyzer
        self.utils = utils


        
        # pass
        

    # --- Stack Overflow Specific Functions (replacing GitHub ones, now receiving dependencies) ---

    def _extract_post_data(self, post: Dict) -> Dict:
        """Extract Stack Overflow question metadata in GitHub-style format."""
        return {
            'id': post['question_id'],
            'url': post['link'],
            'title': post['title'],
            'content': post.get('body', ''),
            'author': post.get('owner', {}).get('display_name', 'N/A'),
            'date': post.get('creation_date', 'N/A'),
            'reaction_score': post.get('score', 0),
            'comments_count': post.get('answer_count', 0)
        }

    def _extract_and_analyze_answers(self, question_id: int, global_keywords: str, stopwords_extra: set, top_n: int = 10) -> List[Dict]:
        """Fetch and analyze Stack Overflow answers for relevance."""
        all_relevant_answers = []

        try:
            response = requests.get(
                f"https://api.stackexchange.com/2.3/questions/{question_id}/answers",
                params={
                    "order": "desc",
                    "sort": "votes",
                    "site": "stackoverflow",
                    "filter": "withbody",
                    "key": os.getenv("STACKOVERFLOW_API_TOKEN")
                }
            )
            answers = response.json().get('items', [])

            updated_keywords = global_keywords

            for answer in answers:
                answer_text = answer.get('body', '')
                is_relevant, score, new_keywords = self.semantic_analyzer._analyze_text_relevance(answer_text, updated_keywords)

                if is_relevant:
                    answer_data = {
                        'id': answer['answer_id'],
                        'author': answer.get('owner', {}).get('display_name', 'N/A'),
                        'text': answer_text,
                        'relevance_score': score,
                        'replies': []
                    }
                    all_relevant_answers.append((score, answer_data, new_keywords))
                    updated_keywords = self.utils._update_global_keywords(new_keywords, updated_keywords, stopwords_extra)




        except Exception as e:
            print(f"Error retrieving answers for question {question_id}: {e}")

        # Sort and return top N answers
        all_relevant_answers.sort(key=lambda x: x[0], reverse=True)
        return [a[1] for a in all_relevant_answers[:top_n]]
