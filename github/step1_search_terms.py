import json
from typing import List

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
    # This function is not used in the main flow for generating search queries,
    # but could be used to inspect the raw booleans.
    return categories[category_idx]['booleans']

def get_search_queries(category_idx: int = 2) -> List[str]:
    """
    Get search queries for a specific category, using all defined boolean strings.
    Each boolean string is chunked separately.
    """
    categories = load_categories()
    category = categories[category_idx]
    print(f"Generating search queries for category: {category['category']}")
    
    all_queries: List[str] = []
    # Iterate through all boolean strings for the category
    for boolean_str in category['booleans']:
        booleans_str_cleaned = boolean_str.strip('()')
        terms = [term.strip() for term in booleans_str_cleaned.split('OR')]
        
        # Chunk terms for search and add to the list of all queries
        chunked_terms = chunk_search_terms(terms, max_length=50)
        all_queries.extend(chunked_terms)
    
    return all_queries

if __name__ == "__main__":
    # Test Step 1
    # Example usage with category_idx = 0 (assuming Data Integration Challenges exists)
    queries = get_search_queries(category_idx=0)
    print("\nGenerated Search Queries:")
    for i, query in enumerate(queries):
        print(f"Query {i+1}: {query}")

    # You can also test with a non-existent category_idx to see error handling or out-of-bounds.
    # try:
    #     queries = get_search_queries(category_idx=999) # Assuming 999 is out of bounds
    # except IndexError:
    #     print("\nSuccessfully handled out-of-bounds category index.")