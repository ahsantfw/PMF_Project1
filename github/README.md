# GitHub Issues Scraper

A sophisticated GitHub scraper that uses semantic analysis to find relevant issues, discussions, and solutions from GitHub repositories.

## 🎯 Purpose

Extracts high-quality, relevant content from GitHub by:

- Searching GitHub issues using PyGithub API
- Analyzing issue titles, descriptions, and comments for semantic relevance
- Filtering out promotional content and spam
- Continuously learning and improving search capabilities

## 🚀 Features

- **GitHub Issues Search**: Searches across all public repositories
- **Semantic Analysis**: Uses advanced NLP to understand content relevance
- **Smart Filtering**: Removes promotional content, spam, and low-quality issues
- **Comment Analysis**: Extracts and analyzes relevant comments
- **Auto-Learning**: Updates global keywords based on found content
- **Progress Tracking**: Saves progress and avoids duplicate processing

## 📋 Requirements

### Dependencies

```bash
pip install PyGithub beautifulsoup4 selenium webdriver-manager sentence-transformers spacy nltk torch transformers huggingface-hub pandas python-dotenv langdetect
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

Create a `.env` file in the Github directory:

```env
GITHUB_TOKEN=your_github_personal_access_token
```

### 2. Get GitHub API Token

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with appropriate permissions
3. Copy the token to your `.env` file

## 📁 File Structure

```
Github/
├── main.py                 # Main scraper logic
├── semantic_analyzer.py    # Semantic analysis engine
├── platform_specific.py    # GitHub-specific data extraction
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
- Searches GitHub issues using PyGithub API
- Processes issues in batches to avoid rate limiting

### 2. Content Filtering

- **Pre-filters**: Engagement, content quality, age
- **Content Quality**: Removes promotional keywords
- **Domain Filtering**: Blocks spam domains
- **Semantic Analysis**: Relevance scoring

### 3. Data Extraction

- **Issue Data**: Title, description, author, date, reactions
- **Comments**: Relevant comments with semantic analysis
- **Metadata**: URL, engagement metrics, relevance score

### 4. Learning System

- Extracts semantic keywords from relevant content
- Updates global keywords continuously
- Improves search accuracy over time

## ⚙️ Configuration

### Filter Configuration

```python
promotional_keywords = [
    'buy now', 'sale', 'discount', 'promotion', 'offer', 
    'webinar', 'course', 'free trial'
]

blacklisted_domains = [
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'is.gd', 
    'ow.ly', 'buff.ly', 'adf.ly', 'shorte.st', 'bc.vc',
    'doubleclick.net', 'adservice.google.com', 
    'googlesyndication.com', 'analytics.google.com'
]
```

### Search Parameters

```python
max_items = 10000          # Maximum issues per search
relevance_threshold = 0.35  # Minimum relevance score
verbose_logging = True     # Detailed logging
```

## 📊 Output Format

### Issue Data Structure

```json
{
  "id": "github_issue_id",
  "title": "Issue title",
  "content": "Issue description",
  "author": "username",
  "date": "2024-01-01T00:00:00",
  "url": "https://github.com/repo/issues/123",
  "reaction_score": 15,
  "comments_count": 25,
  "relevance_score": 0.85,
  "matched_topic": "search query",
  "comments": [
    {
      "id": "comment_id",
      "author": "comment_author",
      "text": "Comment text",
      "relevance_score": 0.75,
      "replies": []
    }
  ]
}
```

## 🚀 Usage

### Basic Usage

```bash
cd Github
python main.py
```

### Custom Search

```python
# Modify search_terms.py to add custom topics
def get_custom_topics():
    return [
        "machine learning implementation",
        "python bug fixes",
        "data science projects"
    ]
```

### Adjusting Filters
**File**: `Github/main.py` (lines 38-50)
```python
self.promotional_keywords = ['buy now', 'sale', 'discount', 'promotion', 'offer', 'webinar', 'course', 'free trial']
self.blacklisted_domains = [
    # Common URL Shorteners
    'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'is.gd', 'ow.ly', 'buff.ly',
    'adf.ly', 'shorte.st', 'bc.vc',
    # Common Ad & Tracking Domains
    'doubleclick.net', 'adservice.google.com', 'googlesyndication.com',
    'analytics.google.com', 'criteo.com', 'taboola.com', 'outbrain.com'
]
```

### Modifying Search Parameters
**File**: `Github/main.py` (line 47)
```python
def process_search_query(self, search_query: str, max_items: int = 10000, all_items=None, save_callback=None, relevance_threshold: float = 0.35):
    # Modify these parameters:
    # max_items = 5000          # Fewer items to process
    # relevance_threshold = 0.4  # Higher threshold for relevance
```

### Modifying Search Topics
**File**: `Github/topics_with_descriptions.csv`
```csv
topic,description
machine learning,AI and ML related content
python programming,Python development topics
data science,Data analysis and science
```

### Modifying Search Queries
**File**: `Github/search_terms.py`
```python
def get_custom_topics():
    return [
        "machine learning implementation",
        "python bug fixes",
        "data science projects"
    ]
```

## 📈 Progress Tracking

### Files Generated

- `outputs/github_items_category_X.json` - Final results per category
- `outputs/github_items_X_progress_TIMESTAMP.json` - Progress saves
- `global_keywords.json` - Updated keywords
- `global_url.json` - Processed URLs

### Monitoring Progress

```bash
# Check current progress
tail -f outputs/github_items_0_progress_*.json

# Monitor global keywords
cat global_keywords.json
```

## 🚨 Error Handling

### Rate Limiting

- Automatic delays between requests
- Respects GitHub API rate limits
- Graceful handling of 403/429 errors

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

- Respect GitHub's API terms of service
- Use appropriate authentication
- Implement rate limiting
- Handle errors gracefully

### Data Privacy

- Only processes public repositories
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
   Solution: Check .env file and GitHub token
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
python -c "from github import Github; print('PyGithub working')"
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
tail -f outputs/github_items_0_progress_*.json

# Check API rate limits
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
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
