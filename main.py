import os
from dataclasses import dataclass
from typing import Dict, List, Any
from dotenv import load_dotenv
import requests
from requests.exceptions import RequestException
from datetime import datetime
import json


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


@dataclass
class PostInfo:
    """Data class for post information."""
    title: str
    created_at: datetime
    url: str
    post_number: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert PostInfo to dictionary format."""
        return {
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'url': self.url,
            'post_number': self.post_number
        }


@dataclass
class AuthorStats:
    """Data class for author statistics."""
    screen_name: str
    post_count: int
    posts: List[PostInfo]

    def to_dict(self) -> Dict[str, Any]:
        """Convert AuthorStats to dictionary format."""
        return {
            'screen_name': self.screen_name,
            'post_count': self.post_count,
            'posts': [post.to_dict() for post in sorted(
                self.posts,
                key=lambda x: x.created_at,
                reverse=True
            )]
        }


class EsaClient:
    """Enhanced ESA client with author statistics and improved pagination."""
    
    def __init__(self, config: ApiConfig):
        self.config = config
        self.base_url = f"https://api.esa.io/v1/teams/{self.config.team_name}"
        self.headers = {
            "Authorization": f"Bearer {self.config.access_token}",
            "Content-Type": "application/json"
        }

    def get_all_posts_in_category(self, category: str = None) -> List[Dict]:
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
        category: str = None,
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

    def get_author_stats(self, posts: List[Dict]) -> Dict[str, AuthorStats]:
        """Extract detailed author statistics from posts."""
        authors: Dict[str, AuthorStats] = {}
        
        for post in posts:
            author = post.get('created_by', {}).get('screen_name', 'Unknown')
            
            post_info = PostInfo(
                title=post.get('full_name', 'Untitled'),
                created_at=datetime.fromisoformat(post['created_at'].replace('Z', '+00:00')),
                url=post.get('url', ''),
                post_number=post.get('number', 0)
            )
            
            if author not in authors:
                authors[author] = AuthorStats(
                    screen_name=author,
                    post_count=1,
                    posts=[post_info]
                )
            else:
                authors[author].post_count += 1
                authors[author].posts.append(post_info)
        
        return authors


def save_author_stats(author_stats: Dict[str, AuthorStats], filename: str = 'author_stats.json') -> None:
    """Save author statistics to a JSON file."""
    output = {
        'total_authors': len(author_stats),
        'authors': {
            author: stats.to_dict()
            for author, stats in sorted(
                author_stats.items(),
                key=lambda x: x[1].post_count,
                reverse=True
            )
        }
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def main() -> None:
    """Main function to extract and save author statistics."""
    try:
        print("\nInitializing configuration...")
        config = ApiConfig.from_env()
        print(f"Team name: {config.team_name}")
        print(f"Category: {config.category}")
        
        print("\nInitializing ESA client...")
        client = EsaClient(config)
        
        print("\nStarting to fetch posts...")
        all_posts = client.get_all_posts_in_category()
        print(f"\nTotal posts fetched: {len(all_posts)}")
        
        print("\nProcessing author statistics...")
        author_stats = client.get_author_stats(all_posts)
        
        # Save to JSON file
        output_file = 'author_stats.json'
        save_author_stats(author_stats, output_file)
        print(f"\nAuthor statistics have been saved to {output_file}")
        print(f"Total unique authors: {len(author_stats)}")
        
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
