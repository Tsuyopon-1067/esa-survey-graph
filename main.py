import os
from dataclasses import dataclass
from typing import Dict, List
from dotenv import load_dotenv
import requests
from requests.exceptions import RequestException
from datetime import datetime
import json
from esa_data import Post, Author, EsaData
from bar_plot import create_graph

@dataclass
class ApiConfig:
    """Configuration class for API settings."""
    access_token: str
    team_name: str
    category: str = 'Survey'

    @classmethod
    def from_env(cls) -> 'ApiConfig':
        """Create ApiConfig instance from environment variables."""
        load_dotenv()
        
        access_token = os.getenv('ESA_ACCESS_TOKEN')
        team_name = os.getenv('ESA_TEAM_NAME')
        category = os.getenv('ESA_CATEGORY', 'Survey')
        
        if not access_token or not team_name:
            raise ValueError(
                "Required environment variables are not set. "
                "Please set ESA_ACCESS_TOKEN and ESA_TEAM_NAME in .env file."
            )
            
        return cls(
            access_token=access_token,
            team_name=team_name.replace('.esa.io', ''),
            category=category
        )


class EsaClient:
    """Enhanced ESA client with author statistics and improved pagination."""
    
    def __init__(self, config: ApiConfig):
        self.config = config
        self.base_url = f"https://api.esa.io/v1/teams/{self.config.team_name}"
        self.headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "Content-Type": "application/json"
        }

    def get_all_posts_in_category(self, category: str = '') -> List[Dict]:
        """Fetch all posts from a category across all pages."""
        category = category or self.config.category
        all_posts = []
        page = 1
        total_count = None
        
        while True:
            try:
                response = self.get_posts_in_category(category, page=page)
                posts = response.get('posts', [])
                
                # Get total count on first page
                if total_count is None:
                    total_count = response.get('total_count', 0)
                    print(f"\nTotal posts to fetch: {total_count}")
                
                if not posts:
                    print("No more posts found in this response")
                    break
                    
                all_posts.extend(posts)
                print(f"Progress: {len(all_posts)}/{total_count} posts collected")
                
                # Check for next page instead of total_pages
                if not response.get('next_page'):
                    print("No next page available")
                    break
                    
                page += 1
                
            except RequestException as e:
                print(f"Error fetching page {page}: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Response status code: {e.response.status_code}")
                    try:
                        print(f"Response content: {e.response.json()}")
                    except:
                        print(f"Response text: {e.response.text}")
                break
                
        return all_posts

    def get_posts_in_category(
        self,
        category: str = '',
        page: int = 1,
        per_page: int = 100
    ) -> Dict:
        """Fetch posts from a specified category with pagination."""
        category = category or self.config.category
        url = f"{self.base_url}/posts"
        
        params = {
            "q": f"in:{category}",
            "page": page,
            "per_page": per_page,
            "sort": "created",
            "order": "desc"
        }
        
        print(f"Fetching page {page}...")
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_esa_data_in_category(self, category: str = '') -> EsaData:
        """Fetch all posts from a category and organize them by author into EsaData structure."""
        category = category or self.config.category
        authors_dict: Dict[str, List[Post]] = {}
        page = 1
        total_count = None
        
        while True:
            try:
                response = self.get_posts_in_category(category, page=page)
                posts = response.get('posts', [])
                
                if total_count is None:
                    total_count = response.get('total_count', 0)
                    print(f"\nTotal posts to fetch: {total_count}")
                
                if not posts:
                    print("No more posts found in this response")
                    break
                    
                # Group posts by author
                for post in posts:
                    post_obj = Post(
                        title=post['name'],
                        created_at=datetime.fromisoformat(post['created_at']),
                        url=post['url'],
                        post_number=post['number']
                    )
                    
                    author_name = post.get('created_by', {}).get('screen_name', 'unknown')
                    if author_name not in authors_dict:
                        authors_dict[author_name] = []
                    authors_dict[author_name].append(post_obj)
                
                print(f"Progress: {sum(len(posts) for posts in authors_dict.values())}/{total_count} posts collected")
                
                if not response.get('next_page'):
                    print("No next page available")
                    break
                    
                page += 1
                
            except RequestException as e:
                print(f"Error fetching page {page}: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    print(f"Response status code: {e.response.status_code}")
                    try:
                        print(f"Response content: {e.response.json()}")
                    except:
                        print(f"Response text: {e.response.text}")
                break
        
        # Convert the grouped posts into Author objects
        authors = {
            name: Author(
                screen_name=name,
                post_count=len(posts),
                posts=posts
            )
            for name, posts in authors_dict.items()
        }
        
        return EsaData(
            total_authors=len(authors),
            authors=authors
        )


def save_author_stats(author_stats: EsaData, filename: str = 'author_stats.json') -> None:
    """Save author statistics to a JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(author_stats.to_dict(), f, ensure_ascii=False, indent=2)

def main() -> None:
    """Main function to extract and save author statistics."""
    try:
        print("\nInitializing configuration...")
        config = ApiConfig.from_env()
        print(f"Team name: {config.team_name}")
        print(f"Category: {config.category}")
        
        print("\nInitializing esa client...")
        client = EsaClient(config)
        
        print("\nStarting to fetch posts...")
        esa_data = client.get_esa_data_in_category()
        
        # Save to JSON file
        #output_file = 'author_stats.json'
        #save_author_stats(esa_data, output_file)
        #print(f"\nAuthor statistics have been saved to {output_file}")

        create_graph(esa_data)
        
    except RequestException as e:
        print(f"API request error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            try:
                print(f"Response content: {e.response.json()}")
            except:
                print(f"Response text: {e.response.text}")
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
