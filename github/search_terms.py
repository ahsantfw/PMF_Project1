import json
from typing import List, Dict
import pandas as pd

def get_topics_from_csv(csv_path: str = 'topics_with_descriptions.csv') -> List[Dict]:
    """
    Reads the CSV file and returns a list of dictionaries,
    each containing a 'topic' and its 'initial_keywords'.
    """
    try:
        df = pd.read_csv(csv_path)
        # We only need the 'topic' column
        topics_list = [{'topic': row['topic']} for index, row in df.iterrows()]
        return topics_list
    except FileNotFoundError:
        print(f"Error: The file '{csv_path}' was not found.")
        return []
    except Exception as e:
        print(f"An error occurred while reading the CSV: {e}")
        return []

if __name__ == "__main__":
    topics = get_topics_from_csv()
    if topics:
        print(f"Successfully loaded {len(topics)} topics from CSV.")
        print("First 3 topics:")
       #loop through the lopics
        for topic in topics:
            print(f"Topic: {topic['topic']}")
            

