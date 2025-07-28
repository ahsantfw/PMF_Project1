import json
from datetime import datetime
from typing import Dict

class Utils:
    def __init__(self):
        pass

    def load_global_keywords(self, global_keywords: str) -> str:
        """Load global keywords from file if available."""
        try:
            with open('global_keywords.json', 'r') as f:
                data = json.load(f)
                global_keywords = data.get('global_keywords', '')
                category_idx = data.get('category_idx', 0)
                print(f"📂 Loaded global keywords from global_keywords.json {len(global_keywords)}")
                return global_keywords, category_idx
        except (FileNotFoundError, json.JSONDecodeError):
            print("No saved global keywords found. Using keywords from the boolean categories file.")

    def save_processed_urls(self, processed_urls: list):
        """Save the current set of processed URLs to file."""
        try:
            with open('global_url.json', 'w') as f:
                json.dump({'articles_global_urls': list(processed_urls)}, f, indent=2)
            print(f"💾 Saved {len(processed_urls)} URLs to global_url.json")
        except Exception as e:
            print(f"Error saving processed URLs: {e}")

    def save_global_keywords(self, global_keywords: str, category_idx: int):
        """Save the current global keywords to file."""
        try:
            with open('global_keywords.json', 'w') as f:
                json.dump({
                    'global_keywords': global_keywords,
                    'category_idx': category_idx,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)
            print(f"💾 Saved global keywords to global_keywords.json")
        except Exception as e:
            print(f"Error saving global keywords: {e}")


    def _update_global_keywords(self, semantic_keywords: Dict[str, str], global_keywords: str, stopwords_extra: set):
        """Update global keywords with new ones found during analysis."""
        if semantic_keywords:
            for matched_term, keyword in semantic_keywords.items():
                if keyword in stopwords_extra:
                    continue
                if matched_term.lower() in global_keywords.lower():
                    updated_keywords = global_keywords.replace(matched_term, f"{matched_term} OR {keyword}")
                    # Remove duplicates by checking for partial matches
                    keywords_list = [k.strip() for k in updated_keywords.split(' OR ')]
                    unique_keywords = []
                    for i, kw1 in enumerate(keywords_list):
                        is_unique = True
                        for j, kw2 in enumerate(keywords_list):
                            if i != j and (kw1.lower() in kw2.lower() or kw2.lower() in kw1.lower()):
                                # Keep the longer keyword
                                if len(kw1) <= len(kw2):
                                    is_unique = False
                                    break
                        if is_unique:
                            unique_keywords.append(kw1)
                    updated_keywords = ' OR '.join(unique_keywords)
                    global_keywords = updated_keywords
        return global_keywords



    def close(self, processed_urls: list, global_keywords: str, category_idx: int):
        """Save progress before closing."""
        self.save_processed_urls(processed_urls)
        self.save_global_keywords(global_keywords, category_idx)
    
    