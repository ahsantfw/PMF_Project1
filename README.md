# Multi-Platform Content Scraper

A comprehensive suite of intelligent content scrapers that use semantic analysis to find relevant content across multiple platforms. Each scraper automatically learns and improves its search capabilities by updating global keywords based on semantic relevance.

## 🚀 Overview

This project contains four specialized scrapers that extract and analyze content from different platforms:

- **Reddit Scraper** - Scrapes relevant posts and comments from Reddit
- **GitHub Scraper** - Extracts relevant issues and discussions from GitHub
- **Stack Overflow Scraper** - Finds relevant questions and answers from Stack Overflow
- **Hugging Face Scraper** - Discovers relevant models and datasets from Hugging Face

## 🎯 Key Features

- **Semantic Analysis**: Uses advanced NLP to understand content relevance
- **Auto-Learning**: Continuously updates global keywords based on found content
- **Multi-Platform**: Unified architecture across different platforms
- **Intelligent Filtering**: Removes spam, promotional content, and irrelevant items
- **Progress Tracking**: Saves progress and avoids duplicate processing
- **Configurable**: Easy to adjust thresholds and filters

## 📋 Prerequisites

- Python 3.8+
- Git
- API tokens for respective platforms (see Environment Setup)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd PMF_Project1
```

### 2. Install Dependencies

#### Core Dependencies (Required for all scrapers)

```bash
pip install selenium webdriver-manager sentence-transformers spacy nltk torch transformers huggingface-hub pandas python-dotenv langdetect
```

#### Platform-Specific Dependencies

**Reddit Scraper:**

```bash
pip install praw
```

**GitHub Scraper:**

```bash
pip install PyGithub beautifulsoup4
```

**Stack Overflow Scraper:**

```bash
pip install bs4
```

**Hugging Face Scraper:**

```bash
# No additional dependencies beyond core
```

### 3. Install spaCy Model

```bash
# Uncomment and run this command in requirements.txt files
python -m spacy download en_core_web_sm
```

### 4. Download NLTK Data

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

## 🔧 Environment Setup

Create a `.env` file in each scraper directory with the following variables:

### Reddit Scraper

```env
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_user_agent
```

### GitHub Scraper

```env
GITHUB_TOKEN=your_github_personal_access_token
```

### Stack Overflow Scraper

```env
STACKOVERFLOW_API_TOKEN=your_stackoverflow_api_token
```

### Hugging Face Scraper

```env
# No API token required for public access
```

## 📁 Project Structure

```
PMF_Project1/
├── Reddit/                 # Reddit content scraper
├── Github/                 # GitHub issues scraper
├── Stackoverflow/          # Stack Overflow Q&A scraper
├── HuggingFace/            # Hugging Face models/datasets scraper
├── LinkedIn/               # LinkedIn scrapers (separate structure)
│   ├── Linkedin_jobs/
│   └── Linkedin_posts/
└── .gitignore
```

## 🔍 How Each Scraper Works

### Reddit Scraper (`Reddit/`)

**Purpose**: Extracts relevant posts and comments from Reddit subreddits.

**Key Features:**

- Searches across all subreddits using PRAW API
- Filters posts by score, comment count, and age
- Analyzes post content and comments for relevance
- Removes promotional content and spam

**Main Components:**

- `main.py` - Main scraper logic
- `semantic_analyzer.py` - Semantic analysis engine
- `platform_specific.py` - Reddit-specific data extraction
- `utils.py` - Utility functions for data management

**Usage:**

```bash
cd Reddit
python main.py
```

### GitHub Scraper (`Github/`)

**Purpose**: Finds relevant issues and discussions from GitHub repositories.

**Key Features:**

- Searches GitHub issues using PyGithub API
- Analyzes issue titles, descriptions, and comments
- Filters by engagement metrics and content quality
- Extracts relevant discussions and solutions

**Main Components:**

- `main.py` - Main scraper logic
- `semantic_analyzer.py` - Semantic analysis engine
- `platform_specific.py` - GitHub-specific data extraction
- `utils.py` - Utility functions for data management

**Usage:**

```bash
cd Github
python main.py
```

### Stack Overflow Scraper (`Stackoverflow/`)

**Purpose**: Extracts relevant questions and answers from Stack Overflow.

**Key Features:**

- Uses Stack Exchange API for data extraction
- Analyzes questions and top answers for relevance
- Filters by reputation, votes, and content quality
- Extracts code snippets and technical discussions

**Main Components:**

- `main.py` - Main scraper logic
- `semantic_analyzer.py` - Semantic analysis engine
- `platform_specific.py` - Stack Overflow-specific data extraction
- `utils.py` - Utility functions for data management

**Usage:**

```bash
cd Stackoverflow
python main.py
```

### Hugging Face Scraper (`HuggingFace/`)

**Purpose**: Discovers relevant models and datasets from Hugging Face Hub.

**Key Features:**

- Searches Hugging Face Hub for models and datasets
- Analyzes model descriptions and metadata
- Filters by downloads, likes, and relevance
- Extracts model information and usage examples

**Main Components:**

- `main.py` - Main scraper logic
- `semantic_analyzer.py` - Semantic analysis engine
- `platform_specific.py` - Hugging Face-specific data extraction
- `utils.py` - Utility functions for data management

**Usage:**

```bash
cd HuggingFace
python main.py
```

## 🧠 Semantic Analysis Engine

All scrapers use a unified semantic analysis engine that:

1. **Extracts Keywords**: Identifies relevant terms from content
2. **Semantic Matching**: Uses sentence transformers for similarity analysis
3. **Global Learning**: Updates global keywords based on found content
4. **Relevance Scoring**: Assigns relevance scores to content items

### Key Components:

- **Sentence Transformers**: Uses `all-MiniLM-L6-v2` model for embeddings
- **spaCy**: For text preprocessing and NLP tasks
- **NLTK**: For tokenization and stopword removal
- **Custom Filters**: Removes promotional content and spam

## 📊 Output Format

Each scraper generates JSON files with the following structure:

```json
{
  "id": "unique_identifier",
  "title": "Content title",
  "content": "Main content text",
  "author": "Content author",
  "date": "2024-01-01T00:00:00",
  "url": "Original URL",
  "relevance_score": 0.85,
  "matched_topic": "Search query",
  "comments": [
    {
      "id": "comment_id",
      "author": "Comment author",
      "text": "Comment text",
      "relevance_score": 0.75
    }
  ]
}
```

## ⚙️ Configuration

Each scraper has configurable parameters that can be modified in their respective `main.py` files:

### Reddit Scraper Configuration
**File**: `Reddit/main.py` (lines 33-40)
```python
self.filter_config = {
    'relevance_threshold': 0.35,    # Minimum relevance score
    'min_post_length': 100,         # Minimum post length
    'min_word_count': 10,           # Minimum word count
    'max_age_days': 730,            # Maximum post age (days)
    'reddit_min_score': 50,         # Minimum Reddit score
    'reddit_min_comments': 10,      # Minimum comment count
    'max_link_ratio': 0.3,          # Maximum link ratio
    'promo_keywords': ["buy now", "subscribe", "free trial", "discount", "offer", "promo", "sale"],
    'blacklisted_domains': ['bit.ly', 'tinyurl.com', 't.co']
}
```

### GitHub Scraper Configuration
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

### Stack Overflow Scraper Configuration
**File**: `Stackoverflow/main.py` (lines 35-45)
```python
self.filter_config = {
    'relevance_threshold': 0.35,    # Minimum relevance score
    'min_post_length': 100,         # Minimum post length
    'min_word_count': 10,           # Minimum word count
    'max_age_days': 730,            # Maximum post age (days)
    'min_score': 5,                 # Minimum question score
    'min_answers': 1,               # Minimum number of answers
    'promo_keywords': ["buy now", "subscribe", "free trial", "discount"],
    'blacklisted_domains': ['bit.ly', 'tinyurl.com', 't.co']
}
```

### Hugging Face Scraper Configuration
**File**: `HuggingFace/main.py` (lines 25-35)
```python
self.filter_config = {
    'relevance_threshold': 0.35,    # Minimum relevance score
    'min_post_length': 100,         # Minimum description length
    'min_word_count': 10,           # Minimum word count
    'max_age_days': 730,            # Maximum age (days)
    'min_engagement': 10,           # Minimum downloads/likes
    'max_link_ratio': 0.3,          # Maximum link ratio
    'promo_keywords': ["buy now", "subscribe", "free trial", "discount", "offer", "promo", "sale"],
    'blacklisted_domains': ['bit.ly', 'tinyurl.com', 't.co']
}
```

### Common Configuration Parameters

- **Relevance Threshold**: Minimum similarity score (default: 0.35)
- **Max Items**: Maximum items to process per query
- **Delay**: Time between requests to avoid rate limiting
- **Filters**: Content quality and spam filters

## 📈 Progress Tracking

- **Global URLs**: Tracks processed URLs to avoid duplicates
- **Global Keywords**: Continuously updated based on semantic analysis
- **Progress Files**: Saves intermediate results every 10 items
- **Category Tracking**: Organizes results by search categories

## 🚨 Error Handling

- **Rate Limiting**: Handles API rate limits gracefully
- **Network Errors**: Retries failed requests
- **Data Validation**: Validates extracted data before saving
- **Graceful Shutdown**: Saves progress on interruption

## 🔒 Security & Best Practices

- **API Tokens**: Stored securely in `.env` files
- **Rate Limiting**: Respects platform API limits
- **Data Privacy**: Only processes public content
- **Error Logging**: Comprehensive error tracking

## 📝 Usage Examples

### Basic Usage

```bash
# Navigate to any scraper directory
cd Reddit

# Run the scraper
python main.py
```

### Custom Configuration

#### Modifying Filters
```python
# Modify filter_config in main.py
filter_config = {
    'relevance_threshold': 0.4,  # Higher threshold
    'min_post_length': 200,      # Longer posts
    'max_age_days': 365,         # Recent content only
}
```

#### Modifying Search Topics
**File**: `topics_with_descriptions.csv` in each scraper directory
```csv
topic,description
machine learning,AI and ML related content
python programming,Python development topics
data science,Data analysis and science
```

#### Modifying Search Queries
**File**: `search_terms.py` in each scraper directory
```python
def get_custom_topics():
    return [
        "machine learning tutorials",
        "python programming tips", 
        "data science projects"
    ]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:

1. Check the individual scraper README files
2. Review the error logs
3. Ensure all dependencies are installed
4. Verify API tokens are correctly configured

## 🔄 Updates

- **Global Keywords**: Automatically updated during scraping
- **Progress Files**: Saved every 10 items processed
- **Configuration**: Can be modified without restarting
- **Data Export**: Results saved in JSON format for analysis
