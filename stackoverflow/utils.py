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
                return global_keywords
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

    def save_global_keywords(self, global_keywords: str):
        """Save the current global keywords to file."""
        try:
            with open('global_keywords.json', 'w') as f:
                json.dump({
                    'global_keywords': global_keywords,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2)
            print(f"💾 Saved global keywords to global_keywords.json")
        except Exception as e:
            print(f"Error saving global keywords: {e}")


    def _update_global_keywords(self, semantic_phrases: Dict[str, str], global_keywords: str, stopwords_extra: set):
        """Update global keywords with new ones found during analysis."""
        # 'global_keywords' is the "OR" separated string of phrases
        current_phrases = set(p.strip() for p in global_keywords.split(' OR '))

        newly_found_phrases = set(semantic_phrases.values())

        for phrase in newly_found_phrases:
            # Basic check to avoid adding stopwords or very short phrases
            if phrase.lower() not in stopwords_extra and len(phrase) > 3:
                current_phrases.add(phrase)
                
        # Join the unique phrases back into the "OR" separated string
        return ' OR '.join(sorted(list(current_phrases)))
        



    def close(self, processed_urls: list, global_keywords: str):
        """Save progress before closing."""
        self.save_processed_urls(processed_urls)
        self.save_global_keywords(global_keywords)
    
    