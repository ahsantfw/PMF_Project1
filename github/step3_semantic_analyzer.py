import nltk
import spacy
import json
from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Set, Tuple
from torch import Tensor
import numpy as np
import re # Import regex module

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
        
        self.cached_embeddings = {}

    def _clean_text_for_nlp(self, text: str) -> str:
        """Removes common HTML tags and URLs from text before NLP processing."""
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', text)
        # Remove URLs
        clean_text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', clean_text)
        # Remove markdown link syntax [text](url)
        clean_text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', clean_text)
        # Remove markdown image syntax ![alt text](url)
        clean_text = re.sub(r'!\[(.*?)\]\(.*?\)', r'\1', clean_text)
        # Replace multiple spaces with a single space
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text

    def extract_semantically_relevant_keywords(
        self,
        article_text: str,
        search_terms: List[str],
        threshold: float = 0.85 
    ) -> Dict[str, str]:
        """
        Extracts keywords from an article that are semantically similar to search terms.
        This includes robust cleaning and filtering of potential keywords.
        """
        semantically_relevant_keywords: Dict[str, str] = {}
        
        # Clean the article text before NLP processing
        cleaned_article_text = self._clean_text_for_nlp(article_text)
        doc = self.nlp(cleaned_article_text)
        
        # Extract potential keywords (nouns and named entities)
        potential_keywords_raw: List[str] = []
        for chunk in doc.noun_chunks:
            potential_keywords_raw.append(chunk.text)
        for ent in doc.ents:
            potential_keywords_raw.append(ent.text)
            
        # Add single nouns and proper nouns
        for token in doc:
            if token.pos_ in ['NOUN', 'PROPN'] and token.text.lower() not in self.stopwords:
                potential_keywords_raw.append(token.text)
        
        # Define common non-semantic prefixes to filter out
        non_semantic_prefixes = {
            'a ', 'an ', 'the ', 'some ', 'any ', 'this ', 'that ', 'these ', 'those ',
            'my ', 'your ', 'his ', 'her ', 'its ', 'our ', 'their ', 'more ', 'less ',
            'many ', 'few ', 'several ', 'such '
        }
        # Convert search terms to lowercase for efficient checking
        search_terms_lower = {term.lower() for term in search_terms}

        potential_keywords: List[str] = []
        unwanted_patterns = [
            r'</summary', r'</a>', r'\+[0-9]+', r'^\s*[-=]\s*$', 
            r'Context:', r'AI', r'Framework', r'Silos',
            r'^[0-9]+$', 
            r'^\W+$', 
            r'\b(?:http|https|www)\b', 
            r'\b[a-zA-Z]\b'
        ]

        for kw in set(potential_keywords_raw): # Use set to get unique keywords
            kw_stripped = kw.strip()
            if not kw_stripped:
                continue
            
            # Filter out very short keywords that are not meaningful
            if len(kw_stripped) < 2 and not kw_stripped.isalnum():
                continue

            # Filter out keywords containing HTML/XML tags
            if '<' in kw_stripped or '>' in kw_stripped:
                continue

            # Filter out keywords matching general unwanted patterns
            if any(re.search(pattern, kw_stripped, re.IGNORECASE) for pattern in unwanted_patterns):
                continue

            # Further filter out if the keyword is mostly non-alphanumeric (e.g., '---', '===' or just symbols)
            alphanumeric_chars = sum(c.isalnum() for c in kw_stripped)
            if len(kw_stripped) > 0 and alphanumeric_chars / len(kw_stripped) < 0.5:
                continue
            
            # --- NEW FILTERING LOGIC for prefixes like "more data silos" ---
            filtered_by_prefix = False
            for prefix in non_semantic_prefixes:
                if kw_stripped.lower().startswith(prefix):
                    core_keyword_candidate = kw_stripped[len(prefix):].strip()
                    
                    # If the core part is empty or a stopword, or if the original keyword
                    # is not an exact search term, and the prefix is one we want to specifically
                    # filter aggressively (like "more " or "your "), then filter it out.
                    if (not core_keyword_candidate or core_keyword_candidate.lower() in self.stopwords) or \
                       (prefix in ['more ', 'your '] and kw_stripped.lower() not in search_terms_lower):
                       filtered_by_prefix = True
                       break
            
            if filtered_by_prefix:
                continue
            # --- END NEW FILTERING LOGIC ---

            potential_keywords.append(kw_stripped)
            
        if not potential_keywords:
            return {}

        try:
            search_term_embeddings = self.model.encode(search_terms, convert_to_tensor=True)
            keyword_embeddings = self.model.encode(potential_keywords, convert_to_tensor=True)
            
            cosine_similarities = util.cos_sim(keyword_embeddings, search_term_embeddings)

            for i, keyword in enumerate(potential_keywords):
                max_similarity, matched_term_index = cosine_similarities[i].max(dim=0)
                
                if max_similarity >= threshold:
                    matched_search_term = search_terms[matched_term_index.item()]
                    
                    if matched_search_term not in semantically_relevant_keywords or \
                       max_similarity > util.cos_sim(self.model.encode(semantically_relevant_keywords[matched_search_term]), self.model.encode(matched_search_term)):
                        semantically_relevant_keywords[matched_search_term] = keyword
        
            print(f"Found {len(semantically_relevant_keywords)} semantically relevant keywords: {semantically_relevant_keywords}")
            return semantically_relevant_keywords

        except Exception as e:
            print(f"Error in keyword extraction: {e}")
            return {}

    def process_article_fast(self, article: Dict[str, str], search_terms: List[str]):
        pass
    
    def check_relevance(self, article_text: str, search_terms: List[str]) -> bool:
        pass
    
    def calculate_relevance(self, article_text: str, search_terms: List[str]) -> float:
        pass

if __name__ == "__main__":
    analyzer = SemanticAnalyzer()
    
    test_article_text = 'Data silos are a major challenge in enterprise environments. Organizations struggle with isolated data repositories that prevent effective data integration and analytics. Modern data architecture solutions help break down these silos. Companies are implementing data lakes and data warehouses to centralize their information. <p>Some irrelevant stuff.</p> Visit our <a href="http://example.com">website</a>. Context:</summary> This is some AI</a > related text. CODE is important. Which System? + 19 - = More data silos, your data silos, a data lake, the system, some solutions.'
    
    search_terms = ['data silo', 'data silos', 'data integration', 'AI', 'system', 'code', 'data lake', 'solutions']
    
    keywords = analyzer.extract_semantically_relevant_keywords(test_article_text, search_terms)
    print(f"Semantic keywords from test article: {keywords}")