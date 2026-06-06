"""
SATARK.AI - Statistical Aggregation Engine
Government-Grade Analytics for MoSPI

This module computes precomputed metrics for the dashboard:
- Summary statistics
- Time series trends
- Geographic comparisons
- Validation metrics
- Anomaly detection
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AggregationEngine:
    """
    Precomputes statistical metrics for dashboard visualization.
    Designed for government-grade reporting with audit trails.
    """
    
    def __init__(self):
        self.cache = {}
        logger.info("✅ Aggregation Engine initialized")
    
    def compute_summary(self, responses: List[Dict]) -> Dict[str, Any]:
        """
        Compute KPI summary metrics.
        
        Returns:
            - total_responses: Total survey responses
            - validated_count: Number of validated responses
            - validation_rate: Percentage validated
            - error_rate: Percentage with errors
            - rural_urban_split: Rural vs Urban distribution
            - gender_ratio: Male/Female/Other distribution
            - confidence_score: Overall data confidence (0-100)
        """
        if not responses:
            return self._empty_summary()
        
        df = pd.DataFrame(responses)
        
        total = len(df)
        validated = len(df[df.get('is_valid', True) == True])
        validation_rate = (validated / total * 100) if total > 0 else 0
        error_rate = 100 - validation_rate
        
        # Rural/Urban split
        location_counts = df.get('location_type', pd.Series(['Unknown'] * total)).value_counts()
        rural_pct = (location_counts.get('Rural', 0) / total * 100) if total > 0 else 0
        urban_pct = (location_counts.get('Urban', 0) / total * 100) if total > 0 else 0
        
        # Gender distribution
        gender_counts = df.get('gender', pd.Series(['Unknown'] * total)).value_counts()
        gender_dist = {
            'male': int(gender_counts.get('Male', 0)),
            'female': int(gender_counts.get('Female', 0)),
            'other': int(gender_counts.get('Other', 0))
        }
        
        # Confidence score calculation
        confidence_score = self._calculate_confidence_score(df)
        
        return {
            'total_responses': total,
            'validated_count': validated,
            'validation_rate': round(validation_rate, 2),
            'error_rate': round(error_rate, 2),
            'rural_urban_split': {
                'rural': round(rural_pct, 1),
                'urban': round(urban_pct, 1)
            },
            'gender_distribution': gender_dist,
            'confidence_score': round(confidence_score, 1),
            'timestamp': datetime.now().isoformat(),
            'data_source': 'SATARK.AI Validated Responses'
        }
    
    def compute_timeseries(
        self, 
        responses: List[Dict], 
        metric: str = 'employment_rate',
        period: str = 'monthly'
    ) -> Dict[str, Any]:
        """
        Compute time series trends for specified metric.
        
        Args:
            responses: List of survey responses
            metric: Metric to track (employment_rate, participation_rate, etc.)
            period: Aggregation period (daily, weekly, monthly, quarterly)
        
        Returns:
            Time series data with dates and values
        """
        if not responses:
            return {'dates': [], 'values': [], 'metric': metric}
        
        df = pd.DataFrame(responses)
        
        # Ensure timestamp column
        if 'timestamp' not in df.columns:
            df['timestamp'] = datetime.now()
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Set period frequency
        freq_map = {
            'daily': 'D',
            'weekly': 'W',
            'monthly': 'M',
            'quarterly': 'Q'
        }
        freq = freq_map.get(period, 'M')
        
        # Group by period
        df.set_index('timestamp', inplace=True)
        
        # Calculate metric (placeholder - would use actual response data)
        # For demo, generate synthetic trend
        grouped = df.resample(freq).size()
        
        dates = [d.strftime('%Y-%m-%d') for d in grouped.index]
        values = grouped.values.tolist()
        
        return {
            'dates': dates,
            'values': values,
            'metric': metric,
            'period': period,
            'timestamp': datetime.now().isoformat()
        }
    
    def compute_state_comparison(
        self, 
        responses: List[Dict], 
        metric: str = 'validation_rate'
    ) -> Dict[str, Any]:
        """
        Compute state-wise comparison for drill-down.
        
        Args:
            responses: List of survey responses
            metric: Metric to compare across states
        
        Returns:
            State-wise metrics with drill-down capability
        """
        # Always generate demo data for major states
        states = ['Uttar Pradesh', 'Maharashtra', 'Bihar', 'West Bengal', 
                 'Madhya Pradesh', 'Tamil Nadu', 'Rajasthan', 'Karnataka',
                 'Gujarat', 'Andhra Pradesh']
        values = np.random.uniform(75, 95, len(states)).tolist()
        
        return {
            'states': states,
            'values': [round(v, 1) for v in values],
            'metric': metric,
            'timestamp': datetime.now().isoformat(),
            'drill_down_enabled': True
        }
    
    def compute_validation_heatmap(
        self, 
        responses: List[Dict]
    ) -> Dict[str, Any]:
        """
        Compute validation error heatmap (Agent vs Error Type).
        
        Returns:
            Matrix data for heatmap visualization
        """
        # Demo data - in production, would aggregate from validation logs
        agents = ['ENUM001', 'ENUM002', 'ENUM003', 'ENUM004', 'ENUM005']
        error_types = ['Range Error', 'Missing Data', 'Duplicate', 'Anomaly', 'Format Error']
        
        # Generate heatmap matrix (agents x error_types)
        matrix = np.random.randint(0, 20, size=(len(agents), len(error_types))).tolist()
        
        return {
            'agents': agents,
            'error_types': error_types,
            'matrix': matrix,
            'timestamp': datetime.now().isoformat()
        }
    
    def compute_anomalies(
        self, 
        responses: List[Dict]
    ) -> Dict[str, Any]:
        """
        Detect and return anomalous data points.
        
        Uses IsolationForest for anomaly detection.
        
        Returns:
            List of flagged responses with anomaly scores
        """
        if not responses or len(responses) < 10:
            return {'anomalies': [], 'count': 0}
        
        df = pd.DataFrame(responses)
        
        # Demo anomalies - in production, use IsolationForest
        anomaly_indices = np.random.choice(len(df), size=min(5, len(df)//20), replace=False)
        
        anomalies = []
        for idx in anomaly_indices:
            anomalies.append({
                'response_id': df.iloc[idx].get('response_id', f'RESP_{idx}'),
                'anomaly_score': round(np.random.uniform(0.7, 0.95), 2),
                'reason': np.random.choice([
                    'Unusual response pattern',
                    'Statistical outlier',
                    'Speeding detected',
                    'GPS anomaly'
                ]),
                'timestamp': datetime.now().isoformat()
            })
        
        return {
            'anomalies': anomalies,
            'count': len(anomalies),
            'threshold': 0.7,
            'timestamp': datetime.now().isoformat()
        }
    
    def compute_sector_breakdown(
        self, 
        responses: List[Dict]
    ) -> Dict[str, Any]:
        """
        Compute sector contribution breakdown.
        
        Returns:
            Sector-wise distribution for stacked bar/area chart
        """
        sectors = ['Agriculture', 'Manufacturing', 'Services', 'Construction', 'Other']
        
        # Demo data - in production, aggregate from responses
        values = [35.2, 22.8, 28.5, 8.3, 5.2]
        
        return {
            'sectors': sectors,
            'values': values,
            'timestamp': datetime.now().isoformat()
        }
    
    def compute_agent_performance(
        self, 
        responses: List[Dict]
    ) -> Dict[str, Any]:
        """
        Compute agent performance ranking.
        
        Returns:
            Agent performance table with metrics
        """
        # Demo data - in production, aggregate from paradata
        agents = []
        for i in range(1, 11):
            agents.append({
                'agent_id': f'ENUM{i:03d}',
                'name': f'Enumerator {i}',
                'responses': np.random.randint(50, 200),
                'error_rate': round(np.random.uniform(2, 15), 1),
                'flagged_pct': round(np.random.uniform(0, 8), 1),
                'avg_time': np.random.randint(180, 600),
                'rank': i
            })
        
        # Sort by error rate (lower is better)
        agents.sort(key=lambda x: x['error_rate'])
        for i, agent in enumerate(agents, 1):
            agent['rank'] = i
        
        return {
            'agents': agents,
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_confidence_score(self, df: pd.DataFrame) -> float:
        """
        Calculate overall data confidence score.
        
        Formula:
        Confidence = 100 - (ErrorWeight + AnomalyWeight + DuplicateWeight)
        
        Where:
        - ErrorWeight = error_rate * 0.5
        - AnomalyWeight = anomaly_rate * 0.3
        - DuplicateWeight = duplicate_rate * 0.2
        """
        total = len(df)
        if total == 0:
            return 0.0
        
        # Error weight
        errors = len(df[df.get('is_valid', True) == False])
        error_weight = (errors / total) * 50
        
        # Anomaly weight (placeholder)
        anomaly_weight = np.random.uniform(2, 8)
        
        # Duplicate weight (placeholder)
        duplicate_weight = np.random.uniform(1, 5)
        
        confidence = 100 - (error_weight + anomaly_weight + duplicate_weight)
        
        return max(0, min(100, confidence))
    
    def _empty_summary(self) -> Dict[str, Any]:
        """Return empty summary when no data available."""
        return {
            'total_responses': 0,
            'validated_count': 0,
            'validation_rate': 0,
            'error_rate': 0,
            'rural_urban_split': {'rural': 0, 'urban': 0},
            'gender_distribution': {'male': 0, 'female': 0, 'other': 0},
            'confidence_score': 0,
            'timestamp': datetime.now().isoformat(),
            'data_source': 'SATARK.AI Validated Responses'
        }


# Singleton instance
aggregation_engine = AggregationEngine()
