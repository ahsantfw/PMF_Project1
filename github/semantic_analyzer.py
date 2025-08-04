import nltk
import spacy
from sentence_transformers import SentenceTransformer, util
from typing import List, Dict, Set, Tuple
from torch import Tensor
import numpy as np
import json
import re

# Download required data
nltk.download('punkt', quiet=True)

class SemanticAnalyzer:
    def __init__(self):
        
        """Initialize semantic analyzer."""
        print("\n>>> Running SemanticAnalyzer with updated threshold support! <<<\n") 
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
    def _clean_text_for_nlp(self, text: str) -> str:
        """Removes common HTML tags, URLs, and markdown formatting from text before NLP processing."""
        # First, remove code blocks enclosed in triple backticks
        clean_text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', clean_text)
        # Remove URLs
        clean_text = re.sub(r'http[s]?://\S+', '', clean_text)
        # Remove markdown links and images
        clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', clean_text)
        clean_text = re.sub(r'\[.*?\]\(.*?\)', '', clean_text)
        
        # Remove emojis and other non-ASCII characters
        clean_text = clean_text.encode('ascii', 'ignore').decode('ascii')

        # Remove all characters except letters, numbers, spaces, and hyphens
        # This will get rid of JSON, special characters, escaped quotes, etc.
        clean_text = re.sub(r'[^\w\s-]', '', clean_text)

        # Replace multiple spaces/newlines with a single space
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        return clean_text
    
    
    def _analyze_text_relevance(self, text: str, keywords: str, relevance_threshold: float = 0.35):
        """Helper to analyze relevance of a given text and extract new keywords."""
        if not text or not keywords:
            return False, 0, {}

        try:
            # The 'keywords' are our topic phrases, split into a list
            topic_phrases = [phrase.strip() for phrase in keywords.split(' OR ')]
            topic_embeddings = self.model.encode(topic_phrases, convert_to_tensor=True)
            
            article_embeddings = self.model.encode(text, convert_to_tensor=True)
            
            cosine_similarity = util.semantic_search(article_embeddings, topic_embeddings, top_k=len(topic_phrases))
            
            # We'll consider the max score as the relevance score
            max_score = 0
            if cosine_similarity and cosine_similarity[0]:
                max_score = cosine_similarity[0][0]['score']


            if max_score >= relevance_threshold:
                semantic_phrases = self.extract_semantically_relevant_phrases(
                    text, topic_phrases, threshold=0.7
                )
                return True, max_score, semantic_phrases
            
            return False, max_score, {}
        except Exception as e:
            print(f"Error in semantic analysis: {e}")
            return False, 0, {}
    def extract_phrases_and_sentences(self, text: str) -> List[str]:
        """Extracts noun phrases from text using spaCy."""
        cleaned_text = self._clean_text_for_nlp(text)
        doc = self.nlp(cleaned_text)
        phrases = set()
        for chunk in doc.noun_chunks:
            phrase_text = chunk.text.strip()
            
            # Ensure phrase is not empty and has more than one word
            if not phrase_text or len(phrase_text.split()) <= 1:
                continue
            
            # Discard phrases that start with a stopword
            first_word = phrase_text.lower().split()[0]
            if first_word in self.stopwords:
                continue

            phrases.add(phrase_text)
            
        return list(phrases)       
    
    def extract_semantically_relevant_phrases(self, article_text: str, topic_phrases: List[str], 
                                           threshold: float = 0.7) -> Dict[str, str]:
        """
        Extract semantically relevant phrases from article text.
        """
        # Extract phrases from article
        article_phrases = self.extract_phrases_and_sentences(article_text)
    
        if not article_phrases or not topic_phrases:
            return {}
    
        # Encode all phrases
        all_phrases = article_phrases + topic_phrases
        all_embeddings = self.model.encode(all_phrases, convert_to_tensor=True, show_progress_bar=False)
    
        # Split embeddings
        article_embeddings = all_embeddings[:len(article_phrases)]
        topic_embeddings = all_embeddings[len(article_phrases):]
    
        # Calculate similarity matrix
        similarity_matrix = util.cos_sim(article_embeddings, topic_embeddings)
    
        # Find matches
        matches = {}
        for i, article_phrase in enumerate(article_phrases):
            similarities = similarity_matrix[i]
            max_similarity = similarities.max().item()
            best_topic_idx = similarities.argmax().item()
        
            if max_similarity >= threshold:
                topic_phrase = topic_phrases[best_topic_idx]
                # To avoid overwriting, let's store a list of matches per topic phrase
                if topic_phrase not in matches:
                    matches[topic_phrase] = []
                matches[topic_phrase].append(article_phrase)
        
        # For simplicity in the current project structure which expects one-to-one, we'll pick the best one.
        # This can be enhanced later if needed.
        final_matches = {}
        for topic, found_phrases in matches.items():
            if found_phrases:
                # Let's just take the first found phrase for now.
                final_matches[topic] = found_phrases[0]
                
        return final_matches

    
    

if __name__ == "__main__":
    # Test Step 3 with speed improvements
    analyzer = SemanticAnalyzer()
    
    # Test article with data silos example
   
    test_content = 'Data silos are a major challenge in enterprise environments. Organizations struggle with isolated data repositories that prevent effective data integration and analytics. Modern data architecture solutions help break down these silos. Companies are implementing data lakes and data warehouses to centralize their information.'
    topic_phrases_list = ['data silos', 'enterprise data', 'data integration']
    
    # In the main script, these are passed as a single "OR" separated string
    topic_phrases_str = ' OR '.join(topic_phrases_list)
    # Test fast processing
    import time
    start_time = time.time()
    
    is_relevant, score, found_phrases = analyzer._analyze_text_relevance(
        text=test_content, 
        keywords=topic_phrases_str, 
        relevance_threshold=0.35  
    )

    # Print the results
    print(f"Is Relevant: {is_relevant}")
    print(f"Relevance Score: {score:.4f}")
    print(f"Found Semantic Phrases: {found_phrases}")
    end_time = time.time()
    print(f"Processing time: {end_time - start_time:.3f} seconds")
  