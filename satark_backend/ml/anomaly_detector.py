"""
SATARK.AI Anomaly Detector
Statistical anomaly detection for response quality monitoring
"""

import numpy as np
import logging
from typing import List, Dict, Optional, Tuple
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import pandas as pd

from config import ML_CONFIG

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Statistical anomaly detection for survey response quality.
    Uses IsolationForest, Z-score, and IQR methods.
    """
    
    def __init__(self):
        """Initialize the anomaly detector."""
        self.isolation_forest = IsolationForest(
            contamination=ML_CONFIG['anomaly_detector']['contamination'],
            random_state=ML_CONFIG['anomaly_detector']['random_state']
        )
        self.scaler = StandardScaler()
        self.is_fitted = False
        
        # Thresholds for different anomaly types
        self.thresholds = {
            'response_time': {'min': 5, 'max': 3600},  # 5 seconds to 1 hour
            'pattern_similarity': 0.8,  # 80% similarity threshold
            'z_score': 3.0,  # Standard Z-score threshold
            'completion_rate': 0.3  # Minimum 30% completion
        }
    
    def detect_response_anomalies(self, responses: List[Dict]) -> Dict:
        """
        Detect anomalies in survey responses.
        
        Returns:
        - Overall anomaly score
        - Specific anomaly types detected
        - Flagged responses
        - Quality metrics
        """
        if not responses:
            return {
                'anomaly_score': 0.0,
                'anomalies_detected': [],
                'flagged_responses': [],
                'quality_metrics': {}
            }
        
        logger.info(f"🔍 Analyzing {len(responses)} responses for anomalies")
        
        # Convert responses to DataFrame for analysis
        df = pd.DataFrame(responses)
        
        # Detect different types of anomalies
        anomalies = {
            'speed_anomalies': self._detect_speed_anomalies(df),
            'pattern_anomalies': self._detect_pattern_anomalies(df),
            'completion_anomalies': self._detect_completion_anomalies(df),
            'statistical_anomalies': self._detect_statistical_anomalies(df)
        }
        
        # Calculate overall anomaly score
        total_responses = len(responses)
        total_anomalies = sum(len(anomaly_list) for anomaly_list in anomalies.values())
        anomaly_score = (total_anomalies / total_responses) if total_responses > 0 else 0.0
        
        # Compile results
        flagged_responses = self._compile_flagged_responses(anomalies)
        quality_metrics = self._calculate_quality_metrics(df, anomalies)
        
        logger.info(f"✅ Anomaly detection complete: {anomaly_score:.2%} anomaly rate")
        
        return {
            'anomaly_score': round(anomaly_score, 3),
            'anomalies_detected': list(anomalies.keys()),
            'flagged_responses': flagged_responses,
            'quality_metrics': quality_metrics,
            'detailed_anomalies': anomalies
        }
    
    def detect_agent_anomalies(self, agent_data: List[Dict]) -> Dict:
        """
        Detect anomalies in agent behavior patterns.
        
        Analyzes:
        - Response speed patterns
        - Survey completion rates
        - Response consistency
        - Working hour patterns
        """
        if not agent_data:
            return {'agent_anomalies': [], 'recommendations': []}
        
        logger.info(f"🔍 Analyzing {len(agent_data)} agents for behavioral anomalies")
        
        df = pd.DataFrame(agent_data)
        anomalous_agents = []
        recommendations = []
        
        # Speed analysis
        if 'avg_response_time' in df.columns:
            speed_outliers = self._detect_outliers_zscore(df['avg_response_time'])
            for idx in speed_outliers:
                agent_id = df.iloc[idx].get('agent_id', f'Agent_{idx}')
                anomalous_agents.append({
                    'agent_id': agent_id,
                    'anomaly_type': 'unusual_speed',
                    'severity': 'medium',
                    'details': f"Unusual response speed: {df.iloc[idx]['avg_response_time']:.1f}s"
                })
        
        # Completion rate analysis
        if 'completion_rate' in df.columns:
            completion_outliers = self._detect_outliers_iqr(df['completion_rate'])
            for idx in completion_outliers:
                agent_id = df.iloc[idx].get('agent_id', f'Agent_{idx}')
                rate = df.iloc[idx]['completion_rate']
                if rate < self.thresholds['completion_rate']:
                    anomalous_agents.append({
                        'agent_id': agent_id,
                        'anomaly_type': 'low_completion',
                        'severity': 'high',
                        'details': f"Low completion rate: {rate:.1%}"
                    })
        
        # Generate recommendations
        if anomalous_agents:
            recommendations.extend([
                "Review training for agents with unusual patterns",
                "Implement additional quality checks for flagged agents",
                "Consider workload redistribution for low-performing agents"
            ])
        
        return {
            'agent_anomalies': anomalous_agents,
            'recommendations': recommendations
        }
    
    def _detect_speed_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect unusually fast or slow responses."""
        anomalies = []
        
        if 'response_time' not in df.columns:
            return anomalies
        
        response_times = df['response_time'].dropna()
        
        # Z-score based detection
        outlier_indices = self._detect_outliers_zscore(response_times)
        
        for idx in outlier_indices:
            response_time = response_times.iloc[idx]
            anomaly_type = 'too_fast' if response_time < self.thresholds['response_time']['min'] else 'too_slow'
            
            anomalies.append({
                'response_id': df.iloc[idx].get('response_id', f'Response_{idx}'),
                'anomaly_type': anomaly_type,
                'value': response_time,
                'severity': 'high' if anomaly_type == 'too_fast' else 'medium'
            })
        
        return anomalies
    
    def _detect_pattern_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect repetitive or suspicious response patterns."""
        anomalies = []
        
        # Check for identical responses
        if 'answers' in df.columns:
            answer_patterns = df['answers'].astype(str)
            duplicate_patterns = answer_patterns.duplicated(keep=False)
            
            for idx, is_duplicate in enumerate(duplicate_patterns):
                if is_duplicate:
                    anomalies.append({
                        'response_id': df.iloc[idx].get('response_id', f'Response_{idx}'),
                        'anomaly_type': 'duplicate_pattern',
                        'severity': 'medium'
                    })
        
        # Check for straight-line responses (all same answers)
        if 'answer_variance' in df.columns:
            low_variance = df['answer_variance'] < 0.1
            for idx, is_low_variance in enumerate(low_variance):
                if is_low_variance:
                    anomalies.append({
                        'response_id': df.iloc[idx].get('response_id', f'Response_{idx}'),
                        'anomaly_type': 'straight_line',
                        'severity': 'high'
                    })
        
        return anomalies
    
    def _detect_completion_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect incomplete or suspicious completion patterns."""
        anomalies = []
        
        if 'completion_rate' not in df.columns:
            return anomalies
        
        completion_rates = df['completion_rate'].dropna()
        
        # Flag very low completion rates
        low_completion = completion_rates < self.thresholds['completion_rate']
        
        for idx, is_low in enumerate(low_completion):
            if is_low:
                anomalies.append({
                    'response_id': df.iloc[idx].get('response_id', f'Response_{idx}'),
                    'anomaly_type': 'incomplete_response',
                    'value': completion_rates.iloc[idx],
                    'severity': 'medium'
                })
        
        return anomalies
    
    def _detect_statistical_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        """Detect statistical anomalies using IsolationForest."""
        anomalies = []
        
        # Select numerical columns for analysis
        numerical_cols = df.select_dtypes(include=[np.number]).columns
        
        if len(numerical_cols) < 2:
            return anomalies
        
        try:
            # Prepare data
            X = df[numerical_cols].fillna(df[numerical_cols].median())
            
            if len(X) < 10:  # Need minimum samples for IsolationForest
                return anomalies
            
            # Fit and predict
            outliers = self.isolation_forest.fit_predict(X)
            
            # Flag outliers
            for idx, is_outlier in enumerate(outliers):
                if is_outlier == -1:  # -1 indicates outlier
                    anomalies.append({
                        'response_id': df.iloc[idx].get('response_id', f'Response_{idx}'),
                        'anomaly_type': 'statistical_outlier',
                        'severity': 'low'
                    })
        
        except Exception as e:
            logger.error(f"Error in statistical anomaly detection: {e}")
        
        return anomalies
    
    def _detect_outliers_zscore(self, data: pd.Series, threshold: float = None) -> List[int]:
        """Detect outliers using Z-score method."""
        if threshold is None:
            threshold = self.thresholds['z_score']
        
        z_scores = np.abs((data - data.mean()) / data.std())
        return z_scores[z_scores > threshold].index.tolist()
    
    def _detect_outliers_iqr(self, data: pd.Series) -> List[int]:
        """Detect outliers using Interquartile Range method."""
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers = data[(data < lower_bound) | (data > upper_bound)]
        return outliers.index.tolist()
    
    def _compile_flagged_responses(self, anomalies: Dict) -> List[Dict]:
        """Compile all flagged responses with severity levels."""
        flagged = []
        
        for anomaly_type, anomaly_list in anomalies.items():
            for anomaly in anomaly_list:
                flagged.append({
                    'response_id': anomaly.get('response_id'),
                    'anomaly_type': anomaly.get('anomaly_type'),
                    'severity': anomaly.get('severity', 'medium'),
                    'category': anomaly_type
                })
        
        # Sort by severity
        severity_order = {'high': 3, 'medium': 2, 'low': 1}
        flagged.sort(key=lambda x: severity_order.get(x['severity'], 0), reverse=True)
        
        return flagged
    
    def _calculate_quality_metrics(self, df: pd.DataFrame, anomalies: Dict) -> Dict:
        """Calculate overall quality metrics."""
        total_responses = len(df)
        
        if total_responses == 0:
            return {}
        
        # Count anomalies by severity
        high_severity = sum(1 for anomaly_list in anomalies.values() 
                           for anomaly in anomaly_list 
                           if anomaly.get('severity') == 'high')
        
        medium_severity = sum(1 for anomaly_list in anomalies.values() 
                             for anomaly in anomaly_list 
                             if anomaly.get('severity') == 'medium')
        
        # Calculate quality score (100 - anomaly percentage)
        total_anomalies = sum(len(anomaly_list) for anomaly_list in anomalies.values())
        quality_score = max(0, 100 - (total_anomalies / total_responses * 100))
        
        return {
            'total_responses': total_responses,
            'total_anomalies': total_anomalies,
            'high_severity_anomalies': high_severity,
            'medium_severity_anomalies': medium_severity,
            'quality_score': round(quality_score, 1),
            'anomaly_rate': round(total_anomalies / total_responses, 3)
        }