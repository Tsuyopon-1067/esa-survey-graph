from dataclasses import dataclass
from typing import List, Dict
from datetime import datetime
from datetime import datetime
import json
import yaml
from pathlib import Path
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

def filter_authors(json_data: EsaData, yaml_path: str) -> EsaData:
    """
    Filter authors based on a list of valid users from a YAML file.
    Authors will be ordered according to the order in YAML file.
    """
    if not Path(yaml_path).exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")
    
    # Load valid users from YAML
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML file: {e}")
    
    if 'valid_users' not in config:
        raise KeyError("'valid_users' key not found in YAML file")
        
    valid_users = config['valid_users']  # リストとして保持して順序を維持
    valid_users_set = set(valid_users)   # 検索用にセットも作成
    
    # Create new EsaData object with only valid authors, maintaining YAML order
    filtered_authors = {}
    for name in valid_users:  # YAMLの順序でループ
        if name in json_data.authors:
            filtered_authors[name] = json_data.authors[name]
    
    filtered_data = EsaData(
        total_authors=len(filtered_authors),
        authors=filtered_authors
    )
    
    # Check if any valid users were not found in the JSON data
    found_users = set(filtered_authors.keys())
    missing_users = valid_users_set - found_users
    if missing_users:
        print(f"Warning: Some users from YAML were not found in JSON: {missing_users}")
    
    return filtered_data
