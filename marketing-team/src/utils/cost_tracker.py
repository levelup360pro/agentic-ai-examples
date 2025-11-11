"""Cost tracking utilities for API usage in the example project.

Reads the CSV produced by the central LLM client and surfaces
summaries for notebooks and quick diagnostics. This module does not
perform any network calls.
"""

import pandas as pd
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from pathlib import Path
import logging

class ModelCostBreakdown(BaseModel):
    """Cost breakdown per model.

    Attributes:
        model: Model name.
        total_cost: Total cost attributed to the model (EUR).
        call_count: Number of invocations.
        avg_cost_per_call: Average EUR spent per invocation.
    """
    model_config = ConfigDict(frozen=True)
    
    model: str = Field(..., description="Model name")
    total_cost: float = Field(ge=0.0, description="Total cost in EUR")
    call_count: int = Field(ge=0, description="Number of API calls")
    avg_cost_per_call: float = Field(ge=0.0, description="Average cost per call")

class CostSummary(BaseModel):
    """Comprehensive cost analysis report.

    Attributes reflect aggregate totals and a per-model breakdown.
    """
    model_config = ConfigDict(frozen=True)
    
    total_cost: float = Field(ge=0.0, description="Total cost across all models")
    total_calls: int = Field(ge=0, description="Total number of API calls")
    avg_cost_per_call: float = Field(ge=0.0, description="Average cost per call")
    total_input_tokens: int = Field(ge=0, description="Total input tokens processed")
    total_output_tokens: int = Field(ge=0, description="Total output tokens generated")
    date_range: str = Field(..., description="Date range of the analysis")
    by_model: list[ModelCostBreakdown] = Field(default_factory=list, description="Cost breakdown by model")

class CostTracker:
    """API cost tracking and analysis helper.

    Args:
        log_file: Path to the CSV exported by the LLM client.
    """
    
    def __init__(self, log_file: str = "data/api_calls.csv"):
        self.log_file = Path(log_file)
        self.logger = logging.getLogger(__name__)
    
    def _load_data(self) -> pd.DataFrame:
        """Load and validate cost data from CSV.

        Returns:
            Dataframe with timestamp, model, token counts, cost, latency.
        """
        if not self.log_file.exists():
            self.logger.warning(f"Cost log file not found: {self.log_file}")
            return pd.DataFrame(columns=['timestamp', 'model', 'input_tokens', 'output_tokens', 'cost_eur', 'latency_seconds'])
        
        try:
            df = pd.read_csv(self.log_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except Exception as e:
            self.logger.error(f"Failed to load cost data: {e}")
            raise
    
    def get_total_cost(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> float:
        """Compute total cost for an optional date range.

        Args:
            start_date: Inclusive start date (YYYY-MM-DD) or None.
            end_date: Inclusive end date (YYYY-MM-DD) or None.

        Returns:
            Sum of cost_eur for the selected period.
        """
        df = self._load_data()
        
        if df.empty:
            return 0.0
        
        # Apply date filters
        if start_date:
            df = df[df['timestamp'] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df['timestamp'] <= pd.to_datetime(end_date)]
        
        return float(df['cost_eur'].sum())
    
    def get_cost_by_model(self) -> list[ModelCostBreakdown]:
        """Get cost breakdown by model.

        Returns:
            A list of ModelCostBreakdown sorted by total_cost descending.
        """
        df = self._load_data()
        
        if df.empty:
            return []
        
        model_stats = df.groupby('model').agg({
            'cost_eur': ['sum', 'count', 'mean']
        }).round(6)
        
        model_stats.columns = ['total_cost', 'call_count', 'avg_cost_per_call']
        
        breakdowns = []
        for model, stats in model_stats.iterrows():
            breakdowns.append(ModelCostBreakdown(
                model=model,
                total_cost=stats['total_cost'],
                call_count=int(stats['call_count']),
                avg_cost_per_call=stats['avg_cost_per_call']
            ))
        
        # Sort by total cost (descending)
        return sorted(breakdowns, key=lambda x: x.total_cost, reverse=True)
    
    def get_cost_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> CostSummary:
        """Generate a comprehensive cost summary report.

        Args:
            start_date: Inclusive start date (YYYY-MM-DD) or None.
            end_date: Inclusive end date (YYYY-MM-DD) or None.

        Returns:
            A CostSummary object with totals and per-model breakdown.
        """
        df = self._load_data()
        
        if df.empty:
            return CostSummary(
                total_cost=0.0,
                total_calls=0,
                avg_cost_per_call=0.0,
                total_input_tokens=0,
                total_output_tokens=0,
                date_range="No data available",
                by_model=[]
            )
        
        # Apply date filters
        filtered_df = df.copy()
        if start_date:
            filtered_df = filtered_df[filtered_df['timestamp'] >= pd.to_datetime(start_date)]
        if end_date:
            filtered_df = filtered_df[filtered_df['timestamp'] <= pd.to_datetime(end_date)]
        
        # Calculate date range
        if not filtered_df.empty:
            min_date = filtered_df['timestamp'].min().strftime('%Y-%m-%d')
            max_date = filtered_df['timestamp'].max().strftime('%Y-%m-%d')
            date_range = f"{min_date} to {max_date}" if min_date != max_date else min_date
        else:
            date_range = "No data in range"
        
        # Calculate summary stats
        total_cost = float(filtered_df['cost_eur'].sum())
        total_calls = len(filtered_df)
        avg_cost = float(filtered_df['cost_eur'].mean()) if total_calls > 0 else 0.0
        
        # Get model breakdown for filtered data
        by_model = []
        if not filtered_df.empty:
            model_stats = filtered_df.groupby('model').agg({
                'cost_eur': ['sum', 'count', 'mean']
            }).round(6)
            
            model_stats.columns = ['total_cost', 'call_count', 'avg_cost_per_call']
            
            for model, stats in model_stats.iterrows():
                by_model.append(ModelCostBreakdown(
                    model=model,
                    total_cost=stats['total_cost'],
                    call_count=int(stats['call_count']),
                    avg_cost_per_call=stats['avg_cost_per_call']
                ))
            
            by_model.sort(key=lambda x: x.total_cost, reverse=True)
        
        return CostSummary(
            total_cost=total_cost,
            total_calls=total_calls,
            avg_cost_per_call=avg_cost,
            total_input_tokens=int(filtered_df['input_tokens'].sum()) if not filtered_df.empty else 0,
            total_output_tokens=int(filtered_df['output_tokens'].sum()) if not filtered_df.empty else 0,
            date_range=date_range,
            by_model=by_model
        )
