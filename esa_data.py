from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime
from datetime import datetime
import json
from typing import Dict, Any

@dataclass
class Post:
    title: str
    created_at: datetime
    url: str
    post_number: int

@dataclass
class Author:
    screen_name: str
    post_count: int
    posts: List[Post]

@dataclass
class EsaData:
    total_authors: int
    authors: Dict[str, Author]


def convert_to_post(post_data: Dict[str, Any]) -> Post:
    """Convert dictionary to Post object"""
    return Post(
        title=post_data['title'],
        created_at=datetime.fromisoformat(post_data['created_at']),
        url=post_data['url'],
        post_number=post_data['post_number']
    )

def convert_to_author(author_data: Dict[str, Any]) -> Author:
    """Convert dictionary to Author object"""
    return Author(
        screen_name=author_data['screen_name'],
        post_count=author_data['post_count'],
        posts=[convert_to_post(post) for post in author_data['posts']]
    )

def load_esa_data(json_path: str) -> EsaData:
    """
    Load JSON file and convert to EsaData object with proper nested structure.
    
    Parameters
    ----------
    json_path : str
        Path to JSON file
        
    Returns
    -------
    EsaData
        Loaded and converted data with proper typing
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            
        # Validate required keys
        if 'total_authors' not in raw_data or 'authors' not in raw_data:
            raise KeyError("JSON must contain 'total_authors' and 'authors' keys")
        
        # Convert authors dictionary
        authors = {
            name: convert_to_author(author_data)
            for name, author_data in raw_data['authors'].items()
        }
            
        return EsaData(
            total_authors=raw_data['total_authors'],
            authors=authors
        )
        
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Invalid JSON file: {e.msg}", e.doc, e.pos)
    except FileNotFoundError:
        raise FileNotFoundError(f"JSON file not found: {json_path}")
