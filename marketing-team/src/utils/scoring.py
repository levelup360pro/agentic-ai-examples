import yaml
import csv
import os
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict

class ScoreResult(BaseModel):
    """Structured scoring result"""
    model_config = ConfigDict(frozen=True)
    
    content_id: str = Field(..., description="Unique identifier for content")
    clarity: float = Field(ge=1, le=10, description="Content clarity score")
    brand_voice: float = Field(ge=1, le=10, description="Brand voice consistency score")
    cta: float = Field(ge=1, le=10, description="Call-to-action effectiveness score")
    accuracy: float = Field(ge=1, le=10, description="Content accuracy score")
    engagement: float = Field(ge=1, le=10, description="Engagement potential score")
    average: float = Field(ge=1, le=10, description="Average score across all dimensions")
    evaluator: str = Field(default="human", description="Who performed the evaluation")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the evaluation was completed")

class ScoringHelper:
    """Production-grade helper for manual content scoring"""
    
    def __init__(self, rubric_path: str = "configs/evaluation_rubric.yaml"):
        self.rubric_path = Path(rubric_path)
        self.rubric = self._load_rubric()
        self.dimensions = ["clarity", "brand_voice", "cta", "accuracy", "engagement"]
    
    def _load_rubric(self) -> Dict:
        """Load scoring rubric from YAML file"""
        if not self.rubric_path.exists():
            raise FileNotFoundError(f"Rubric file not found: {self.rubric_path}")
        
        with open(self.rubric_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def score_content(self, content: str, content_id: str) -> ScoreResult:
        """Interactive CLI for scoring content with validation"""
        
        print("\n" + "=" * 80)
        print(f"SCORING CONTENT: {content_id}")
        print("=" * 80)
        print("\nCONTENT:")
        print("-" * 80)
        print(content)
        print("-" * 80)
        
        scores = {}
        
        for dimension in self.dimensions:
            scores[dimension] = self._score_dimension(dimension)
        
        # Calculate average
        average = sum(scores.values()) / len(scores)
        
        print(f"\n{'=' * 80}")
        print(f"AVERAGE SCORE: {average:.1f}/10")
        print(f"{'=' * 80}\n")
        
        return ScoreResult(
            content_id=content_id,
            clarity=scores["clarity"],
            brand_voice=scores["brand_voice"],
            cta=scores["cta"],
            accuracy=scores["accuracy"],
            engagement=scores["engagement"],
            average=average
        )
    
    def _score_dimension(self, dimension: str) -> float:
        """Score a single dimension with validation"""
        dimension_config = self.rubric.get('dimensions', {}).get(dimension, {})
        examples = dimension_config.get('examples', {})
        
        print(f"\n{dimension.upper()} (1-10):")
        
        # Show reference examples if available
        for score_level in ['score_3', 'score_7', 'score_10']:
            if score_level in examples:
                score_num = score_level.split('_')[1]
                description = examples[score_level].get('description', 'No description')
                print(f"  {score_num} = {description}")
        
        while True:
            try:
                score = float(input(f"Score for {dimension}: "))
                if 1 <= score <= 10:
                    return score
                else:
                    print("Score must be between 1 and 10")
            except ValueError:
                print("Please enter a valid number")
            except KeyboardInterrupt:
                print("\nScoring cancelled")
                raise
    
    def save_scores(
        self,
        score_result: ScoreResult,
        output_path: str = "data/week_02_scores.csv"
    ) -> None:
        """Save scores to CSV with proper error handling"""
        output_file = Path(output_path)
        
        # Create directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file with headers if it doesn't exist
        if not output_file.exists():
            self._create_csv_with_headers(output_file)
        
        # Append the score
        self._append_score_to_csv(output_file, score_result)
    
    def _create_csv_with_headers(self, output_file: Path) -> None:
        """Create CSV file with proper headers"""
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "content_id", "clarity", "brand_voice", "cta",
                "accuracy", "engagement", "average", "evaluator", "timestamp"
            ])
    
    def _append_score_to_csv(self, output_file: Path, score_result: ScoreResult) -> None:
        """Append score result to CSV file"""
        with open(output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                score_result.content_id,
                score_result.clarity,
                score_result.brand_voice,
                score_result.cta,
                score_result.accuracy,
                score_result.engagement,
                score_result.average,
                score_result.evaluator,
                score_result.timestamp.isoformat()
            ])
    
    def batch_score_contents(
        self,
        contents: Dict[str, str],
        output_path: str = "data/week_02_scores.csv"
    ) -> list[ScoreResult]:
        """Score multiple contents in batch"""
        results = []
        
        for content_id, content in contents.items():
            try:
                score_result = self.score_content(content, content_id)
                self.save_scores(score_result, output_path)
                results.append(score_result)
            except KeyboardInterrupt:
                print(f"\nBatch scoring stopped at content: {content_id}")
                break
            except Exception as e:
                print(f"Error scoring content {content_id}: {e}")
                continue
        
        return results
    
    def display_scoring_guide(self, content: str, content_id: str) -> None:
        """
        Display content and rubric for manual scoring in notebooks.
        Use this when input() doesn't work (Jupyter notebooks).
        
        Usage:
            scorer.display_scoring_guide(content, "post_001")
            # Then in next cell, manually create scores dict and use create_score_result()
        
        Args:
            content: The content to be scored
            content_id: Unique identifier for the content
        """
        print("\n" + "=" * 80)
        print(f"CONTENT TO SCORE: {content_id}")
        print("=" * 80)
        print(content)
        print("\n" + "=" * 80)
        print("SCORING RUBRIC:")
        print("=" * 80)
        
        # Display rubric for each dimension
        for dimension in self.dimensions:
            dimension_config = self.rubric.get('dimensions', {}).get(dimension, {})
            examples = dimension_config.get('examples', {})
            description = dimension_config.get('description', f'{dimension.title()} evaluation')
            
            print(f"\n{dimension.upper()} (1-10)")
            print(f" {description}")
            
            # Show reference examples
            for score_level in ['score_3', 'score_7', 'score_10']:
                if score_level in examples:
                    score_num = score_level.split('_')[1]
                    desc = examples[score_level].get('description', 'No description')
                    print(f"   {score_num}/10 = {desc}")
        
        print("\n" + "=" * 80)
        print("In the next cell, manually enter your scores:")
        print("=" * 80)
        print("scores = {")
        for dimension in self.dimensions:
            print(f"    '{dimension}': X,  # 1-10")
        print("}")
        print("\n# Then create and save the result:")
        print(f"score_result = scorer.create_score_result('{content_id}', scores)")
        print("scorer.save_scores(score_result)")
        print(f"print(f'Average: {{score_result.average:.1f}}/10')")
        print("=" * 80 + "\n")
    
    def create_score_result(
        self, 
        content_id: str, 
        scores: Dict[str, float],
        evaluator: str = "human"
    ) -> ScoreResult:
        """
        Create a ScoreResult from manually entered scores dict.
        Useful for notebook-based scoring where input() doesn't work.
        
        Args:
            content_id: Unique identifier for the content
            scores: Dictionary with keys: clarity, brand_voice, cta, accuracy, engagement
            evaluator: Who performed the evaluation (default: "human")
        
        Returns:
            ScoreResult object ready to be saved
        
        Example:
            scores = {
                'clarity': 8.0,
                'brand_voice': 7.5,
                'cta': 6.0,
                'accuracy': 9.0,
                'engagement': 7.0
            }
            score_result = scorer.create_score_result("post_001", scores)
            scorer.save_scores(score_result)
        """
        # Validate all required dimensions are present
        missing = set(self.dimensions) - set(scores.keys())
        if missing:
            raise ValueError(f"Missing scores for dimensions: {missing}")
        
        # Validate score ranges
        for dimension, score in scores.items():
            if not (1 <= score <= 10):
                raise ValueError(f"Score for {dimension} must be between 1 and 10, got {score}")
        
        # Calculate average
        average = sum(scores.values()) / len(scores)
        
        return ScoreResult(
            content_id=content_id,
            clarity=scores["clarity"],
            brand_voice=scores["brand_voice"],
            cta=scores["cta"],
            accuracy=scores["accuracy"],
            engagement=scores["engagement"],
            average=average,
            evaluator=evaluator
        )
