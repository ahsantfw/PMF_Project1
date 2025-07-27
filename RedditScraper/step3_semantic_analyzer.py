import nltk
import spacy
from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Set, Tuple
from torch import Tensor
import numpy as np
import json

# Download required data
nltk.download('punkt', quiet=True)

class SemanticAnalyzer:
    def __init__(self):
        """Initialize semantic analyzer."""
        print('Loading MiniLM model...')
        self.model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        print('MiniLM model loaded.')
        
        self.nlp = spacy.load("en_core_web_sm")
        self.stopwords = self.nlp.Defaults.stop_words
        
        # Load extra stopwords if available
        try:
            with open('stopwords_extra.json', 'r') as f:
                data = json.load(f)
                extra_stopwords = set(data.get('stopwords_extra', []))
                self.stopwords.update(extra_stopwords)
                print(f"Loaded {len(extra_stopwords)} extra stopwords")
        except FileNotFoundError:
            print("No extra stopwords file found")
        except Exception as e:
            print(f"Error loading extra stopwords: {e}")
        
        # Pre-compute embeddings for common terms to speed up processing
        self.cached_embeddings = {}
    
    def check_relevance(self, article_text: str, search_terms: List[str]) -> bool:
        """Check if article is relevant to search terms."""
        return self.calculate_relevance(article_text, search_terms) >= 0.35

    def calculate_cosine_similarity(self, article_embeddings: Tensor, to_be_matched_embeddings: Tensor) -> float:
        """Calculate cosine similarity between article and to_be_matched."""
        similarity = util.cos_sim(article_embeddings, to_be_matched_embeddings)
        return similarity.item()

    def extract_candidates_fast(self, text: str) -> List[str]:
        """Extract candidate keywords from text using fast spaCy processing."""
        doc = self.nlp(text)
        candidates = set()
        
        # Extract noun chunks (most important)
        for chunk in doc.noun_chunks:
            if len(chunk.text.strip()) > 2:
                candidates.add(chunk.text.strip())
        
        # Extract named entities
        for ent in doc.ents:
            if len(ent.text.strip()) > 2:
                candidates.add(ent.text.strip())
        
        # Extract important nouns and proper nouns (filtered)
        for token in doc:
            if (token.pos_ in {"NOUN", "PROPN"} and 
                not token.is_stop and 
                len(token.text.strip()) > 2 and
                token.text.isalpha()):
                candidates.add(token.text.strip())
        
        return list(candidates)
    
    def extract_semantically_relevant_keywords(self, article_text: str, search_terms: str, threshold: float = 0.75) -> Dict[str, str]:
        """
        Extract semantically relevant keywords from article text with comprehensive preprocessing.
        """
        # Comprehensive preprocessing
        import re
        
        # 1. Clean and normalize text
        article_text = re.sub(r'[^\w\s]', ' ', article_text)  # Remove punctuation
        article_text = re.sub(r'\s+', ' ', article_text)  # Normalize whitespace
        article_text = article_text.lower().strip()
        
        # 2. Tokenize article into words (not sentences)
        article_words = article_text.split()
        
        # 3. Preprocess search terms - handle both string and list inputs
        if isinstance(search_terms, str):
            search_terms_clean = [term.strip() for term in search_terms.split(' OR ')]
        else:
            search_terms_clean = [term.strip() for term in search_terms]
        
        # 4. Extract and clean article tokens in one pass
        article_tokens_clean = []
        for word in article_words:
            # Clean the word
            clean_word = re.sub(r'[^\w]', '', word.lower())
            if (clean_word not in self.stopwords and 
                len(clean_word) > 2 and 
                clean_word.isalpha() and
                clean_word not in [term.lower() for term in search_terms_clean]):
                article_tokens_clean.append(clean_word)
        
        # 5. Remove duplicates
        article_tokens_clean = list(set(article_tokens_clean))
        
        # print(f"Debug: Found {len(article_tokens_clean)} candidate tokens: {article_tokens_clean[:10]}...")
        # print(f"Debug: Search terms: {search_terms_clean}")
        
        if not article_tokens_clean or not search_terms_clean:
            print("Debug: No candidate tokens or search terms found")
            return {}
        
        # 6. Batch encode all tokens and search terms at once
        all_texts = article_tokens_clean + search_terms_clean
        all_embeddings = self.model.encode(all_texts, convert_to_tensor=True, show_progress_bar=False)
        
        # 7. Split embeddings
        article_embeddings = all_embeddings[:len(article_tokens_clean)]
        search_terms_embeddings = all_embeddings[len(article_tokens_clean):]
        
        # 8. Calculate similarity matrix efficiently
        sim_matrix = util.cos_sim(article_embeddings, search_terms_embeddings)
        
        # 9. Find semantically relevant keywords with their matched search terms
        semantically_relevant_keywords = {}
        
        for i, article_token in enumerate(article_tokens_clean):
            # Get similarity scores to all search terms
            similarities = sim_matrix[i]
            max_similarity = similarities.max().item()
            matched_search_term_idx = similarities.argmax().item()
            
            # print(f"Debug: Token '{article_token}' - max similarity: {max_similarity:.3f} with '{search_terms_clean[matched_search_term_idx]}'")
            
            if max_similarity >= threshold:
                matched_search_term = search_terms_clean[matched_search_term_idx]
                semantically_relevant_keywords[matched_search_term] = article_token
                # print(f"Debug: Added keyword '{article_token}' matched with '{matched_search_term}' (similarity: {max_similarity:.3f})")
                
        print(f"Found {len(semantically_relevant_keywords)} semantically relevant keywords: {semantically_relevant_keywords}")
        return semantically_relevant_keywords

    
    

if __name__ == "__main__":
    # Test Step 3 with speed improvements
    analyzer = SemanticAnalyzer()
    
    # Test article with data silos example
    test_article = {
        'title': 'Breaking Down Data Silos in Enterprise',
        'content': 'Data silos are a major challenge in enterprise environments. Organizations struggle with isolated data repositories that prevent effective data integration and analytics. Modern data architecture solutions help break down these silos. Companies are implementing data lakes and data warehouses to centralize their information.'
    }
    
    search_terms = ['data silos', 'enterprise data', 'data integration']
    
    # Test fast processing
    import time
    start_time = time.time()
    
    is_relevant, keywords = analyzer.process_article_fast(test_article, search_terms)
    
    end_time = time.time()
    print(f"Processing time: {end_time - start_time:.3f} seconds")
    print(f"Relevant: {is_relevant}")
    print(f"Semantic keywords: {keywords}")