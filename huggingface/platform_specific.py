from typing import List, Dict, Optional, Any
from datetime import datetime
import requests
import os
import re # Import regex module
from step3_semantic_analyzer import SemanticAnalyzer
from huggingface_hub import HfApi, list_models, list_datasets, list_spaces # Import list_spaces

# Define a base URL for the Hugging Face API 
HUGGINGFACE_API_BASE_URL = "https://huggingface.co/api"

class PlatformSpecific:
    def __init__(self, semantic_analyzer, utils):
        self.semantic_analyzer = semantic_analyzer
        self.utils = utils
        self.hf_api_token = os.getenv("HF_API_TOKEN") 
        if not self.hf_api_token:
            raise ValueError("HF_API_TOKEN not found in .env file. Please generate a token and add it.")
        
        # Initialize Hugging Face Hub API client
        self.hf_client = HfApi(token=self.hf_api_token)

    # --- Hugging Face Specific Functions (using huggingface_hub) ---

    def _search_huggingface_items(self, query: str, limit: int = 100, item_type: str = "all") -> List[Dict]:
        """
        Search for Hugging Face models, datasets, and/or spaces based on a query using huggingface_hub.
        This function will prioritize searching for relevant items based on tags and descriptions.
        """
        all_found_items = {} # Use a dictionary to store unique items by their ID
        
        # Broad tags to filter models/datasets/spaces
        broad_hf_tags = [
            "nlp", "text-classification", "sentiment-analysis", "question-answering",
            "summarization", "translation", "language-modeling", "embeddings",
            "computer-vision", "image-classification", "object-detection",
            "audio", "speech-recognition", "reinforcement-learning",
            "tabular-classification", "tabular-regression", "timeseries",
            "diffusers", "stable-diffusion", "generative-ai", "foundation-model",
            "data", "ml", "database", "analytics", "integration", # Added more data-centric tags
            "demo", "app", "gradio", "streamlit", "streamlit-app", "interface" # Tags for spaces
        ]
        
        individual_terms = [term.strip().replace('(', '').replace(')', '') for term in query.split('OR') if term.strip()]
        for term in individual_terms:
            if term not in broad_hf_tags:
                broad_hf_tags.append(term)

        print(f"Fetching Hugging Face {item_type} using relevant tags: {broad_hf_tags}")

        # Helper to process fetched info and add to all_found_items
        def add_item_to_found(info_obj, current_type):
            item_id = getattr(info_obj, 'id', None)
            
            if not item_id: 
                item_id = info_obj.get('id') or info_obj.get('modelId')
            
            if item_id and item_id not in all_found_items:
                full_info = None
                try:
                    if current_type == 'model':
                        full_info = self.hf_client.get_model_info(item_id, full=True)
                    elif current_type == 'dataset':
                        full_info = self.hf_client.get_dataset_info(item_id, full=True)
                    elif current_type == 'space':
                        full_info = self.hf_client.get_space_info(item_id, full=True) # Get full space info
                except Exception as e:
                    # print(f"Warning: Could not fetch full info for {current_type} {item_id}: {e}")
                    full_info = info_obj 

                # Determine URL prefix based on type
                url_prefix = ""
                if current_type == 'model': url_prefix = "https://huggingface.co/"
                elif current_type == 'dataset': url_prefix = "https://huggingface.co/datasets/"
                elif current_type == 'space': url_prefix = "https://huggingface.co/spaces/"

                all_found_items[item_id] = {
                    'type': current_type,
                    'data': getattr(full_info, 'cardData', None) if current_type == 'model' else full_info.__dict__,
                    'id': item_id,
                    'url': f"{url_prefix}{item_id}",
                    'created_at': getattr(full_info, 'created_at', None),
                    'likes': getattr(full_info, 'likes', 0),
                    'downloads': getattr(full_info, 'downloads', 0) if current_type != 'space' else getattr(full_info, 'likes', 0), # Spaces use likes for popularity
                    'author': getattr(full_info, 'author', 'N/A'),
                    'tags': getattr(full_info, 'tags', [])
                }
                return True 
            return False 


        # Search for models
        if item_type in ["all", "model"]:
            current_model_count = 0
            for tag in broad_hf_tags:
                if current_model_count >= limit: break
                try:
                    models_by_search_or_tag = []
                    models_by_search_or_tag.extend(list_models(search=tag, token=self.hf_api_token, limit=limit))
                    models_by_search_or_tag.extend(list_models(filter=tag, token=self.hf_api_token, limit=limit))
                    
                    for model_info in models_by_search_or_tag:
                        if add_item_to_found(model_info, 'model'):
                            current_model_count += 1
                            if current_model_count >= limit: break
                except Exception as e:
                    print(f"Error fetching models for tag '{tag}': {e}")
            
            if current_model_count < limit: 
                try:
                    print(f"Fetching top downloaded models as fallback (need {limit - current_model_count}).")
                    models = list_models(sort="downloads", direction=-1, token=self.hf_api_token, limit=limit - current_model_count)
                    for model_info in models:
                        add_item_to_found(model_info, 'model')
                except Exception as e:
                    print(f"Error fetching top downloaded models: {e}")

        # Search for datasets
        if item_type in ["all", "dataset"]:
            current_dataset_count = 0
            for tag in broad_hf_tags:
                if current_dataset_count >= limit: break
                try:
                    datasets_by_search_or_tag = []
                    datasets_by_search_or_tag.extend(list_datasets(search=tag, token=self.hf_api_token, limit=limit))
                    datasets_by_search_or_tag.extend(list_datasets(filter=tag, token=self.hf_api_token, limit=limit))
                    
                    for dataset_info in datasets_by_search_or_tag:
                        if add_item_to_found(dataset_info, 'dataset'):
                            current_dataset_count += 1
                            if current_dataset_count >= limit: break
                except Exception as e:
                    print(f"Error fetching datasets for tag '{tag}': {e}")

            if current_dataset_count < limit: 
                try:
                    print(f"Fetching top downloaded datasets as fallback (need {limit - current_dataset_count}).")
                    datasets = list_datasets(sort="downloads", direction=-1, token=self.hf_api_token, limit=limit - current_dataset_count)
                    for dataset_info in datasets:
                        add_item_to_found(dataset_info, 'dataset')
                except Exception as e:
                    print(f"Error fetching top downloaded datasets: {e}")

        # Search for spaces
        if item_type in ["all", "space"]:
            current_space_count = 0
            for tag in broad_hf_tags:
                if current_space_count >= limit: break
                try:
                    print(f"Attempting HF API fetch for spaces with search/tag: '{tag}'")
                    spaces_by_search_or_tag = []
                    spaces_by_search_or_tag.extend(list_spaces(search=tag, token=self.hf_api_token, limit=limit))
                    spaces_by_search_or_tag.extend(list_spaces(filter=tag, token=self.hf_api_token, limit=limit))
                    
                    for space_info in spaces_by_search_or_tag:
                        if add_item_to_found(space_info, 'space'):
                            current_space_count += 1
                            if current_space_count >= limit: break
                except Exception as e:
                    print(f"Error fetching spaces for tag '{tag}': {e}")

            if current_space_count < limit: 
                try:
                    print(f"Fetching top liked spaces as fallback (need {limit - current_space_count}).")
                    # Spaces are typically sorted by likes for popularity, not downloads
                    spaces = list_spaces(sort="likes", direction=-1, token=self.hf_api_token, limit=limit - current_space_count)
                    for space_info in spaces:
                        add_item_to_found(space_info, 'space')
                except Exception as e:
                    print(f"Error fetching top liked spaces: {e}")

        print(f"Total unique items fetched from Hugging Face: {len(all_found_items)}")
        return list(all_found_items.values())

    def _get_item_description(self, item_id: str, item_type: str) -> str:
        """
        Fetches the full description (README) of a Hugging Face model, dataset, or space
        and extracts only meaningful English prose, stripping YAML front matter and structured data.
        """
        headers = {"Authorization": f"Bearer {self.hf_api_token}"}
        raw_markdown = ""
        try:
            if item_type == "model":
                readme_url = f"https://huggingface.co/{item_id}/raw/main/README.md"
            elif item_type == "dataset":
                readme_url = f"https://huggingface.co/datasets/{item_id}/raw/main/README.md"
            elif item_type == "space":
                readme_url = f"https://huggingface.co/spaces/{item_id}/raw/main/README.md" # Spaces also have README.md
            else:
                return ""

            response = requests.get(readme_url, headers=headers)
            response.raise_for_status()
            raw_markdown = response.text
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in [404, 403]:
                return ""
            return ""
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Network error fetching README for {item_type} {item_id}: {e}")
            return ""
        except Exception as e:
            print(f"An unexpected error occurred fetching README for {item_type} {item_id}: {e}")
            return ""

        # --- Content Cleaning and Extraction Logic ---
        cleaned_content = re.sub(r'^---\s*$(.*?)^---\s*$', '', raw_markdown, flags=re.MULTILINE | re.DOTALL)
        cleaned_content = re.sub(r'^#+\s*.*$', '', cleaned_content, flags=re.MULTILINE)
        cleaned_content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', cleaned_content)
        cleaned_content = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', cleaned_content)
        cleaned_content = re.sub(r'```.*?```', '', cleaned_content, flags=re.DOTALL)
        cleaned_content = re.sub(r'`(.*?)`', r'\1', cleaned_content)
        cleaned_content = re.sub(r'^[*-]{3,}$', '', cleaned_content, flags=re.MULTILINE)
        cleaned_content = re.sub(r'^[*-+\d\.]+\s+', '', cleaned_content, flags=re.MULTILINE)
        cleaned_content = re.sub(r'^\|.*\|$', '', cleaned_content, flags=re.MULTILINE)
        cleaned_content = re.sub(r'^\|-+$', '', cleaned_content, flags=re.MULTILINE)
        cleaned_content = re.sub(r'\s+', ' ', cleaned_content).strip()

        words = cleaned_content.split()
        if len(words) < 10 or not any(c.isalpha() for c in cleaned_content):
            return ""

        return cleaned_content

    def _extract_item_data(self, item: Dict, content_type: str) -> Dict:
        """Extract Hugging Face item metadata (model, dataset, or space) with desired fields."""
        extracted_data = {
            "platform": "huggingface",
            "title": item.get('id'),
            "content": "", 
            "author": item.get('author', 'N/A'),
            "url": item.get('url'),
            "created_date": item.get('created_at').isoformat() if item.get('created_at') else 'N/A',
            "score": item.get('downloads', 0), # Default to downloads for models/datasets
            "comments_count": 0, 
            "scraped_at": datetime.now().isoformat(),
            "content_type": content_type,
            "tags": item.get('tags', []),
            "likes": item.get('likes', 0),
            "relevance_score": 0.0,
            "matched_topic": ""
        }
        if content_type == "model":
            extracted_data["model_id"] = item.get('id')
        elif content_type == "dataset":
            extracted_data["dataset_id"] = item.get('id')
        elif content_type == "space":
            extracted_data["space_id"] = item.get('id')
            extracted_data["score"] = item.get('likes', 0) # Use likes for spaces as their popularity metric

        return extracted_data

    def _extract_and_analyze_discussions(self, item_id: str, item_type: str, global_keywords: str, stopwords_extra: set, top_n: int = 5) -> List[Dict]:
        """
        Fetches discussions (issues/pull requests) for a Hugging Face item and analyzes them for relevance.
        Note: Direct API for Hugging Face item discussions is not straightforward. Skipping discussion analysis for now.
        """
        return []

    # --- Original Stack Overflow Specific Functions (kept for context, will be removed if no longer needed) ---

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
        all_relevant_answers.sort(key=lambda x: x[0], reverse=True)
        return [a[1] for a in all_relevant_answers[:top_n]]