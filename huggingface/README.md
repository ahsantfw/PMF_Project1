# Hugging Face Hub Scraper

A sophisticated Hugging Face scraper that uses semantic analysis to find relevant models, datasets, and AI/ML resources from the Hugging Face Hub.

## 🎯 Purpose

Extracts high-quality, relevant content from Hugging Face Hub by:

- Searching Hugging Face Hub for models and datasets
- Analyzing model descriptions and metadata for semantic relevance
- Filtering out low-quality content and spam
- Continuously learning and improving search capabilities

## 🚀 Features

- **Hugging Face Hub Search**: Searches models and datasets using Hugging Face API
- **Semantic Analysis**: Uses advanced NLP to understand content relevance
- **Smart Filtering**: Removes low-quality content and spam
- **Metadata Analysis**: Extracts model information and usage examples
- **Auto-Learning**: Updates global keywords based on found content
- **Progress Tracking**: Saves progress and avoids duplicate processing

## 📋 Requirements

### Dependencies

```bash
pip install selenium webdriver-manager sentence-transformers spacy nltk torch transformers huggingface-hub pandas python-dotenv langdetect
```

### spaCy Model

```bash
# Uncomment and run this command in requirements.txt
python -m spacy download en_core_web_sm
```

### NLTK Data

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

## 🔧 Setup

### 1. Environment Variables

Create a `.env` file in the HuggingFace directory:

```env
# No API token required for public access
# Optional: Add your Hugging Face token for higher rate limits
HUGGINGFACE_TOKEN=your_huggingface_token
```

### 2. Get Hugging Face Token (Optional)

1. Go to https://huggingface.co/settings/tokens
2. Create a new token
3. Copy the token to your `.env` file (optional for public access)

## 📁 File Structure

```
HuggingFace/
├── main.py                 # Main scraper logic
├── semantic_analyzer.py    # Semantic analysis engine
├── platform_specific.py    # Hugging Face-specific data extraction
├── utils.py               # Utility functions
├── search_terms.py        # Search query generation
├── requirements.txt       # Dependencies
├── .env                  # Environment variables
├── global_keywords.json  # Learned keywords
├── global_url.json       # Processed URLs tracking
├── stopwords_extra.json  # Additional stopwords
├── topics_with_descriptions.csv  # Search topics
└── outputs/              # Generated results
```

## 🔍 How It Works

### 1. Search Process

- Reads search topics from `topics_with_descriptions.csv`
- Searches Hugging Face Hub using Hugging Face API
- Processes models and datasets in batches to avoid rate limiting

### 2. Content Filtering

- **Pre-filters**: Downloads, likes, content quality
- **Content Quality**: Removes low-quality models/datasets
- **Metadata Analysis**: Analyzes descriptions and tags
- **Semantic Analysis**: Relevance scoring

### 3. Data Extraction

- **Model/Dataset Data**: Name, description, author, date, metrics
- **Metadata**: Tags, framework, task type, usage examples
- **Engagement**: Downloads, likes, relevance score

### 4. Learning System

- Extracts semantic keywords from relevant content
- Updates global keywords continuously
- Improves search accuracy over time

## ⚙️ Configuration

### Filter Configuration

```python
filter_config = {
    'relevance_threshold': 0.35,    # Minimum relevance score
    'min_post_length': 100,         # Minimum description length
    'min_word_count': 10,           # Minimum word count
    'max_age_days': 730,            # Maximum age (days)
    'min_engagement': 10,           # Minimum downloads/likes
    'max_link_ratio': 0.3,          # Maximum link ratio
    'promo_keywords': ["buy now", "subscribe", "free trial", "discount"],
    'blacklisted_domains': ['bit.ly', 'tinyurl.com', 't.co']
}
```

### Search Parameters

```python
max_items = 10000          # Maximum items per search
relevance_threshold = 0.35  # Minimum relevance score
verbose_logging = True     # Detailed logging
```

## 📊 Output Format

### Model/Dataset Data Structure

```json
{
  "id": "huggingface_model_id",
  "title": "Model/Dataset name",
  "content": "Description",
  "author": "username",
  "date": "2024-01-01T00:00:00",
  "url": "https://huggingface.co/model-name",
  "downloads": 15000,
  "likes": 250,
  "relevance_score": 0.85,
  "matched_topic": "search query",
  "metadata": {
    "tags": ["nlp", "transformer", "text-generation"],
    "framework": "pytorch",
    "task": "text-generation",
    "language": "en"
  }
}
```

## 🚀 Usage

### Basic Usage

```bash
cd HuggingFace
python main.py
```

### Custom Search

```python
# Modify search_terms.py to add custom topics
def get_custom_topics():
    return [
        "transformer models",
        "computer vision datasets",
        "natural language processing"
    ]
```

### Adjusting Filters
**File**: `HuggingFace/main.py` (lines 25-35)
```python
self.filter_config = {
    'relevance_threshold': 0.4,    # Higher threshold for relevance
    'min_post_length': 100,        # Minimum description length
    'min_word_count': 10,          # Minimum word count
    'max_age_days': 365,           # Recent content only (days)
    'min_engagement': 100,         # Higher engagement requirement
    'max_link_ratio': 0.3,         # Maximum link ratio
    'promo_keywords': ["buy now", "subscribe", "free trial", "discount", "offer", "promo", "sale"],
    'blacklisted_domains': ['bit.ly', 'tinyurl.com', 't.co']
}
```

### Modifying Search Parameters
**File**: `HuggingFace/main.py` (line 47)
```python
def process_search_query(self, search_query: str, max_items: int = 10000, all_items=None, save_callback=None):
    # Modify these parameters:
    # max_items = 5000          # Fewer items to process
```

### Modifying Search Topics
**File**: `HuggingFace/topics_with_descriptions.csv`
```csv
topic,description
machine learning,AI and ML related content
python programming,Python development topics
data science,Data analysis and science
```

### Modifying Search Queries
**File**: `HuggingFace/search_terms.py`
```python
def get_custom_topics():
    return [
        "transformer models",
        "computer vision datasets",
        "natural language processing"
    ]
```

## 📈 Progress Tracking

### Files Generated

- `outputs/huggingface_items_category_X.json` - Final results per category
- `outputs/huggingface_items_X_progress_TIMESTAMP.json` - Progress saves
- `global_keywords.json` - Updated keywords
- `global_url.json` - Processed URLs

### Monitoring Progress

```bash
# Check current progress
tail -f outputs/huggingface_items_0_progress_*.json

# Monitor global keywords
cat global_keywords.json
```

## 🚨 Error Handling

### Rate Limiting

- Automatic delays between requests
- Respects Hugging Face API rate limits
- Graceful handling of 429 errors

### Network Issues

- Retries failed requests
- Continues from last saved state
- Comprehensive error logging

### Data Validation

- Validates extracted data
- Handles missing fields gracefully
- Logs data quality issues

## 🔒 Best Practices

### API Usage

- Respect Hugging Face's API terms of service
- Use appropriate authentication
- Implement rate limiting
- Handle errors gracefully

### Data Privacy

- Only processes public content
- Respects user privacy
- No personal data collection

### Performance

- Batch processing for efficiency
- Progress saving every 10 items
- Memory-efficient data structures

## 🆘 Troubleshooting

### Common Issues

1. **API Authentication Error**

   ```
   Solution: Check .env file and Hugging Face token (optional)
   ```
2. **Rate Limiting**

   ```
   Solution: Increase delays or use authenticated requests
   ```
3. **No Results Found**

   ```
   Solution: Lower relevance_threshold or adjust filters
   ```
4. **Memory Issues**

   ```
   Solution: Reduce max_items or enable progress saving more frequently
   ```

### Debug Mode

```python
# Enable verbose logging
verbose_logging = True

# Check API connection
python -c "from huggingface_hub import HfApi; print('Hugging Face API working')"
```

## 📝 Logs and Monitoring

### Log Levels

- **INFO**: General progress and results
- **DEBUG**: Detailed processing information
- **WARNING**: Non-critical issues
- **ERROR**: Critical failures

### Monitoring Commands

```bash
# Watch progress in real-time
tail -f outputs/huggingface_items_0_progress_*.json

# Check API status
curl https://huggingface.co/api/models
```

## 🔄 Updates and Maintenance

### Regular Maintenance

- Update dependencies monthly
- Monitor API rate limits
- Review and update filters
- Clean up old progress files

### Performance Optimization

- Adjust batch sizes based on performance
- Monitor memory usage
- Optimize search queries
- Update relevance thresholds

## 📄 License

This scraper is part of the Multi-Platform Content Scraper project and follows the same license terms.
