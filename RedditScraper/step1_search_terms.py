import json
from typing import List, Dict, Any

def load_categories() -> List[dict]:
    """Load categories from JSON file."""
    with open('boolean_categories.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def chunk_search_terms(terms: List[str], max_length: int = 50) -> List[str]:
    """Split search terms into chunks for web search."""
    chunks = []
    current_chunk = []
    current_length = 0
    
    for term in terms:
        term = term.strip()
        add_length = len(term) if not current_chunk else len(' OR ') + len(term)
        
        if current_length + add_length > max_length and current_chunk:
            chunks.append(' OR '.join(current_chunk))
            current_chunk = [term]
            current_length = len(term)
        else:
            if current_chunk:
                current_length += len(' OR ')
            current_chunk.append(term)
            current_length += len(term)
    
    if current_chunk:
        chunks.append(' OR '.join(current_chunk))
    
    return chunks

def get_boolean_search_terms(category_idx: int = 2) -> List[str]:
    """Get boolean search terms for a specific category."""
    categories = load_categories()
    return categories

def get_search_queries(category_idx: int = 2) -> List[str]:
    """Get a list of individual search queries for a specific category."""
    categories = load_categories()
    
    if len(categories) <= category_idx:
        print(f"Error: Category index {category_idx} is out of bounds.")
        return []

    category = categories[category_idx]
    
    # Extract terms by splitting the booleans string by 'OR'
    booleans_str = category['booleans'][0].strip('()')
    terms = [term.strip() for term in booleans_str.split('OR')]
    
    # Remove any empty strings from the list
    return [term for term in terms if term]

if __name__ == "__main__":
    # Test Step 1
    search_queries = get_search_queries(category_idx=0)
    print("Search queries:")
    for i, query in enumerate(search_queries):
        print(f"  {i+1}: {query}") 