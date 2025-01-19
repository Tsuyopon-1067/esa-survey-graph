from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple
from matplotlib.figure import Figure
from matplotlib.axes import Axes
import matplotlib.pyplot as plt
import numpy as np
import os
from dotenv import load_dotenv
from esa_data import EsaData, filter_authors, load_esa_data

@dataclass
class Config:
    """Configuration class for the application.

    Parameters
    ----------
    json_path : str
        Path to the input JSON file
    ranking_path : str
        Path where the current year ranking chart will be saved
    ranking_all_path : str
        Path where the multi-year stacked chart will be saved
    jst : timezone, optional
        Japanese timezone information, by default timezone(timedelta(hours=+9))
    """
    json_path: str
    ranking_path: str
    ranking_all_path: str
    jst: timezone = timezone(timedelta(hours=+9))

class AcademicYearManager:
    """Manages academic year calculations and validations.

    Parameters
    ----------
    timezone_info : timezone
        Timezone information for date calculations
    """
    
    def __init__(self, timezone_info: timezone):
        self.timezone = timezone_info
    
    def get_current_year(self) -> int:
        """Get current academic year based on Japanese academic calendar.

        The academic year in Japan starts in April. For months January to March,
        the academic year is the previous calendar year.

        Returns
        -------
        int
            Current academic year
        """
        now = datetime.now(self.timezone)
        return now.year - 1 if 1 <= now.month <= 3 else now.year
    
    def get_target_years(self, lookback: int = 2) -> List[int]:
        """Get list of academic years for analysis.

        Parameters
        ----------
        lookback : int, optional
            Number of previous years to include, by default 2

        Returns
        -------
        List[int]
            List of academic years, newest first
        """
        current_year = self.get_current_year()
        return [current_year - i for i in range(lookback + 1)]
    
    def is_in_academic_year(self, date: datetime, year: int) -> bool:
        """Check if a date falls within specified academic year.

        Parameters
        ----------
        date : datetime
            Date to check
        year : int
            Academic year to check against

        Returns
        -------
        bool
            True if date falls within academic year, False otherwise
        """
        start = datetime(year, 4, 1, tzinfo=self.timezone)
        end = datetime(year + 1, 3, 31, 23, 59, 59, tzinfo=self.timezone)
        return start <= date <= end

class PostAnalyzer:
    """Analyzes post data and generates statistics.

    Parameters
    ----------
    year_manager : AcademicYearManager
        Manager for academic year calculations
    """
    
    def __init__(self, year_manager: AcademicYearManager):
        self.year_manager = year_manager
    
    def count_posts_by_year(self, data: EsaData, target_years: List[int]) -> Dict[int, Dict[str, int]]:
        """Count posts for each author grouped by academic year.

        Parameters
        ----------
        data : Dict
            Input data containing author and post information
        target_years : List[int]
            List of academic years to analyze

        Returns
        -------
        Dict[int, Dict[str, int]]
            Nested dictionary with structure {year: {author: post_count}}
        """
        counts = {year: {} for year in target_years}
        
        for author_name, author_data in data.authors.items():
            for post in author_data.posts:
                post_date = post.created_at
                
                for year in target_years:
                    if self.year_manager.is_in_academic_year(post_date, year):
                        counts[year][author_name] = counts[year].get(author_name, 0) + 1
        
        return counts

class ChartGenerator:
    """Generates visualization charts.

    Parameters
    ----------
    timezone_info : timezone
        Timezone information for date display
    """
    BAR_TOP_FONT_SIZE = 16
    LEGEND_FONT_SIZE = 18
    TITLE_FONT_SIZE = 18
    AXIS_FONT_SIZE = 18
    
    def __init__(self, timezone_info: timezone):
        self.timezone = timezone_info
        self.colors = ['#4c72b0', '#dd8453', '#55a868']
    
    def _create_fig_template(self, sorted_author_names: List[str]) -> Tuple[Figure, Axes, np.ndarray]:
        """Create a template for matplotlib figure with common styling.

        Parameters
        ----------
        sorted_author_names : List[str]
            List of author names to be used for x-axis labels

        Returns
        -------
        Tuple[plt.Figure, plt.Axes, np.ndarray]
            Tuple containing figure, axis, and bottom array for stacking
        """
        dpi = 96
        width_inches = 1258 / dpi
        height_inches = 977 / dpi
        fig, ax = plt.subplots(figsize=(width_inches, height_inches), dpi=dpi)
        ax.set_facecolor('#eaeaf2')
        fig.patch.set_facecolor('white')

        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(length=0)

        bottom = np.zeros(len(sorted_author_names))
        
        ax.grid(True, color='white', linewidth=1.5, zorder=0)
        ax.set_xlabel('Username')
        ax.set_ylabel('# of surveyed papers')
        ax.set_xlabel('Username', fontsize=self.AXIS_FONT_SIZE)
        ax.set_ylabel('# of surveyed papers', fontsize=self.AXIS_FONT_SIZE)
        
        ax.set_xticks(range(len(sorted_author_names)))
        ax.set_xticklabels(sorted_author_names, rotation=90, ha='center', va='top', fontsize=self.AXIS_FONT_SIZE)
        ax.tick_params(axis='y', labelsize=self.AXIS_FONT_SIZE)
        
        plt.tight_layout()
        return fig, ax, bottom
    
    def create_current_year_chart(self, post_counts: Dict[int, Dict[str, int]], 
                                current_year: int, output_path: str):
        """Create bar chart for current academic year's survey rankings.

        Parameters
        ----------
        post_counts : Dict[int, Dict[str, int]]
            Dictionary containing post counts by year and author
        current_year : int
            Current academic year
        output_path : str
            Path where the chart should be saved
        """
        current_year_data = dict(sorted(
            post_counts[current_year].items(), 
            key=lambda x: x[1], 
            reverse=True
        ))
        
        authors = list(current_year_data.keys())
        counts = list(current_year_data.values())

        fig, ax, _ = self._create_fig_template(authors)
        bars = ax.bar(authors, counts,
                     width=0.5,
                     label=str(current_year),
                     edgecolor='white',
                     linewidth=1.5,
                     zorder=3)
        
        now = datetime.now(self.timezone)
        ax.set_title(f'Survey ranking {current_year} / updated: {now.strftime("%Y/%m/%d")}', fontsize=self.TITLE_FONT_SIZE)
        ax.grid(True, axis='y', alpha=0.3)
        
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom',fontsize=self.BAR_TOP_FONT_SIZE,)
        
        self._finalize_chart(fig, ax, output_path)
    
    def create_stacked_chart(self, post_counts: Dict[int, Dict[str, int]], 
                           target_years: List[int], output_path: str):
        """Create stacked bar chart showing survey rankings across multiple years.

        Parameters
        ----------
        post_counts : Dict[int, Dict[str, int]]
            Dictionary containing post counts by year and author
        target_years : List[int]
            List of academic years to include in the chart
        output_path : str
            Path where the chart should be saved
        """
        author_stats = self._calculate_author_statistics(post_counts, target_years)
        sorted_author_names = [author for author, _ in author_stats]
        
        fig, ax, bottom = self._create_fig_template(sorted_author_names)
        
        now = datetime.now(self.timezone)
        ax.set_title(f'Survey ranking {min(target_years)}-{max(target_years)} / '
                    f'updated: {now.strftime("%Y/%m/%d")}', fontsize=self.TITLE_FONT_SIZE)
        
        self._create_stacked_bars(ax, post_counts, target_years, sorted_author_names, bottom)
        self._add_total_labels(ax, author_stats)
        
        self._finalize_chart(fig, ax, output_path)
    
    def _calculate_author_statistics(self, post_counts: Dict, 
                                  target_years: List[int]) -> List[Tuple[str, int]]:
        """Calculate total posts for each author and sort.

        Parameters
        ----------
        post_counts : Dict
            Dictionary containing post counts by year and author
        target_years : List[int]
            List of academic years to analyze

        Returns
        -------
        List[Tuple[str, int]]
            List of tuples containing (author_name, total_posts), sorted by total_posts
        """
        all_authors = set().union(*[year_data.keys() for year_data in post_counts.values()])
        author_total_posts = {
            author: sum(post_counts[year].get(author, 0) for year in target_years)
            for author in all_authors
        }
        return sorted(author_total_posts.items(), key=lambda x: x[1], reverse=True)
    
    def _create_stacked_bars(self, ax: Axes, post_counts: Dict, 
                           target_years: List[int], sorted_authors: List[str], 
                           bottom: np.ndarray):
        """Create stacked bars for each year.

        Parameters
        ----------
        ax : plt.Axes
            Matplotlib axes object
        post_counts : Dict
            Dictionary containing post counts by year and author
        target_years : List[int]
            List of academic years to include
        sorted_authors : List[str]
            List of author names, sorted by total posts
        bottom : np.ndarray
            Array containing bottom positions for stacking
        """
        for i, year in enumerate(reversed(target_years)):
            values = [post_counts[year].get(author, 0) for author in sorted_authors]
            ax.bar(range(len(sorted_authors)), values,
                  width=0.5,
                  bottom=bottom,
                  label=str(year),
                  color=self.colors[i],
                  edgecolor='white',
                  linewidth=1.5,
                  zorder=3)
            bottom += values
    
    def _add_total_labels(self, ax: Axes, author_stats: List[Tuple[str, int]]):
        """Add total count labels on top of bars.

        Parameters
        ----------
        ax : plt.Axes
            Matplotlib axes object
        author_stats : List[Tuple[str, int]]
            List of tuples containing (author_name, total_posts)
        """
        y_margin = max(total for _, total in author_stats) * 0.003
        for i, (_, total) in enumerate(author_stats):
            if total > 0:
                ax.text(i, total + y_margin, str(int(total)),
                       ha='center', va='bottom',
                       fontsize=self.BAR_TOP_FONT_SIZE,
                       fontweight='medium',
                       zorder=4)
    
    def _finalize_chart(self, fig: Figure, ax: Axes, output_path: str):
        """Apply final touches to the chart and save.

        Parameters
        ----------
        fig : plt.Figure
            Matplotlib figure object
        ax : plt.Axes
            Matplotlib axes object
        output_path : str
            Path where the chart should be saved
        """
        ax.margins(x=0.02)
        legend = ax.legend(bbox_to_anchor=(1, 1), loc='upper right')
        plt.setp(legend.get_texts(), fontsize=self.LEGEND_FONT_SIZE)
        
        plt.tight_layout()
        fig.savefig(output_path, dpi=96, bbox_inches='tight')
        plt.show()
        plt.close()

def load_config() -> Config:
    load_dotenv()
    json_path = os.getenv('JSON_PATH')
    if json_path is None:
        raise ValueError("JSON_PATH environment variable is not set")
        
    ranking_path = os.getenv('ESA_RANKING')
    if ranking_path is None:
        raise ValueError("ESA_RANKING environment variable is not set")
        
    ranking_all_path = os.getenv('ESA_RANKING_ALL')
    if ranking_all_path is None:
        raise ValueError("ESA_RANKING_ALL environment variable is not set")
        
    return Config(
        json_path=json_path,
        ranking_path=ranking_path,
        ranking_all_path=ranking_all_path
    )

def create_graph(data):
    config = load_config()
    year_manager = AcademicYearManager(config.jst)
    current_year = year_manager.get_current_year()
    target_years = year_manager.get_target_years()
    yaml_path = os.getenv('YAML_PATH')
    if yaml_path is not None:
        data = filter_authors(data, yaml_path)
    
    print(f"Current academic year: {current_year}")
    print(f"Analyzing academic years: {target_years}")

    analyzer = PostAnalyzer(year_manager)
    post_counts = analyzer.count_posts_by_year(data, target_years)
    
    chart_generator = ChartGenerator(config.jst)
    chart_generator.create_current_year_chart(post_counts, current_year, config.ranking_path)
    chart_generator.create_stacked_chart(post_counts, target_years, config.ranking_all_path)

def main():
    """Main function to generate survey ranking visualizations."""
    
    config = load_config()
    data: EsaData = load_esa_data(config.json_path)
    create_graph(data)
    
if __name__ == "__main__":
    main()
