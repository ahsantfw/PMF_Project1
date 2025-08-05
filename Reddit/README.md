# Reddit Content Scraper

A sophisticated Reddit scraper that uses semantic analysis to find relevant posts and comments across all subreddits.

## 🎯 Purpose

Extracts high-quality, relevant content from Reddit by:
- Searching across all subreddits using PRAW API
- Analyzing post content and comments for semantic relevance
- Filtering out spam and promotional content
- Continuously learning and improving search capabilities

## 🚀 Features

- **Cross-Subreddit Search**: Searches all of Reddit, not just specific subreddits
- **Semantic Analysis**: Uses advanced NLP to understand content relevance
- **Smart Filtering**: Removes promotional content, spam, and low-quality posts
- **Comment Analysis**: Extracts and analyzes relevant comments
- **Auto-Learning**: Updates global keywords based on found content
- **Progress Tracking**: Saves progress and avoids duplicate processing

## 📋 Requirements

### Dependencies
```bash
pip install praw selenium webdriver-manager sentence-transformers spacy nltk torch transformers huggingface-hub pandas python-dotenv langdetect
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
Create a `.env` file in the Reddit directory:

```env
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_user_agent
```

### 2. Get Reddit API Credentials
1. Go to https://www.reddit.com/prefs/apps
2. Create a new app (script type)
3. Copy the client ID and client secret
4. Set a user agent (e.g., "MyBot/1.0")

## 📁 File Structure

```
Reddit/
├── main.py                 # Main scraper logic
├── semantic_analyzer.py    # Semantic analysis engine
├── platform_specific.py    # Reddit-specific data extraction
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
- Searches Reddit using PRAW API with relevance sorting
- Processes posts in batches to avoid rate limiting

### 2. Content Filtering
- **Pre-filters**: Score, comments, age, length
- **Content Quality**: Removes promotional keywords
- **Domain Filtering**: Blocks spam domains
- **Semantic Analysis**: Relevance scoring

### 3. Data Extraction
- **Post Data**: Title, content, author, date, score
- **Comments**: Relevant comments with semantic analysis
- **Metadata**: URL, engagement metrics, relevance score

### 4. Learning System
- Extracts semantic keywords from relevant content
- Updates global keywords continuously
- Improves search accuracy over time

## ⚙️ Configuration

### Filter Configuration
```python
filter_config = {
    'relevance_threshold': 0.35,    # Minimum relevance score
    'min_post_length': 100,         # Minimum post length
    'min_word_count': 10,           # Minimum word count
    'max_age_days': 730,            # Maximum post age (days)
    'reddit_min_score': 50,         # Minimum Reddit score
    'reddit_min_comments': 10,      # Minimum comment count
    'max_link_ratio': 0.3,          # Maximum link ratio
    'promo_keywords': ["buy now", "subscribe", "free trial", "discount"],
    'blacklisted_domains': ['bit.ly', 'tinyurl.com', 't.co']
}
```

### Search Parameters
```python
max_posts = 1000          # Maximum posts per search
delay_seconds = 0.5       # Delay between requests
verbose_logging = True    # Detailed logging
```

## 📊 Output Format

### Post Data Structure
```json
{
  "id": "reddit_post_id",
  "title": "Post title",
  "content": "Post content",
  "author": "username",
  "date": "2024-01-01T00:00:00",
  "url": "https://reddit.com/r/subreddit/comments/...",
  "score": 150,
  "comments_count": 25,
  "relevance_score": 0.85,
  "matched_topic": "search query",
  "comments": [
    {
      "id": "comment_id",
      "author": "comment_author",
      "text": "Comment text",
      "relevance_score": 0.75,
      "score": 10
    }
  ]
}
```

## 🚀 Usage

### Basic Usage
```bash
cd Reddit
python main.py
```

### Custom Search
```python
# Modify search_terms.py to add custom topics
def get_custom_topics():
    return [
        "machine learning tutorials",
        "python programming tips",
        "data science projects"
    ]
```

### Adjusting Filters
**File**: `Reddit/main.py` (lines 33-40)
```python
self.filter_config = {
    'relevance_threshold': 0.4,    # Higher threshold for relevance
    'min_post_length': 100,        # Minimum post length
    'min_word_count': 10,          # Minimum word count
    'max_age_days': 365,           # Recent content only (days)
    'reddit_min_score': 100,       # Higher Reddit score requirement
    'reddit_min_comments': 10,     # Minimum comment count
    'max_link_ratio': 0.3,         # Maximum link ratio
    'promo_keywords': ["buy now", "subscribe", "free trial", "discount", "offer", "promo", "sale"],
    'blacklisted_domains': ['bit.ly', 'tinyurl.com', 't.co']
}
```

### Modifying Search Topics
**File**: `Reddit/topics_with_descriptions.csv`
```csv
topic,description
machine learning,AI and ML related content
python programming,Python development topics
data science,Data analysis and science
```

### Modifying Search Queries
**File**: `Reddit/search_terms.py`
```python
def get_custom_topics():
    return [
        "machine learning tutorials",
        "python programming tips",
        "data science projects"
    ]
```

## 📈 Progress Tracking

### Files Generated
- `outputs/reddit_items_category_X.json` - Final results per category
- `outputs/reddit_items_X_progress_TIMESTAMP.json` - Progress saves
- `global_keywords.json` - Updated keywords
- `global_url.json` - Processed URLs

### Monitoring Progress
```bash
# Check current progress
tail -f outputs/reddit_items_0_progress_*.json

# Monitor global keywords
cat global_keywords.json
```

## 🚨 Error Handling

### Rate Limiting
- Automatic delays between requests
- Respects Reddit API limits
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
- Respect Reddit's API terms of service
- Use appropriate user agent
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
   Solution: Check .env file and API credentials
   ```

2. **Rate Limiting**
   ```
   Solution: Increase delay_seconds in configuration
   ```

3. **No Results Found**
   ```
   Solution: Lower relevance_threshold or adjust filters
   ```

4. **Memory Issues**
   ```
   Solution: Reduce max_posts or enable progress saving more frequently
   ```

### Debug Mode
```python
# Enable verbose logging
verbose_logging = True

# Check API connection
python -c "import praw; print('PRAW working')"
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
tail -f outputs/reddit_items_0_progress_*.json

# Check API status
curl -H "User-Agent: MyBot/1.0" https://www.reddit.com/api/v1/overview.json
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