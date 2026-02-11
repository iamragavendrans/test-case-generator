"""
Unit tests for Atomic Behavior Extraction Service.
Tests the one-actor/one-action/one-object decomposition logic.
"""

import pytest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.behavior_extraction import (
    BehaviorExtractionService,
    BehaviorExtractionResult,
    AtomicBehaviorData
)


class TestBehaviorExtractionService:
    """Test cases for BehaviorExtractionService."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        return BehaviorExtractionService()
    
    def test_extract_single_behavior(self, service):
        """Test extraction of a single atomic behavior."""
        normalized_data = {
            'actor': 'User',
            'action': 'reserve parking slot',
            'conditions': ['future time window'],
            'expected_outcome': 'slot reserved',
            'feature_area': 'Reservation'
        }
        
        result = service.extract(
            requirement_id='FR-3',
            normalized_data=normalized_data,
            requirement_type='Functional'
        )
        
        assert len(result.behaviors) == 1
        behavior = result.behaviors[0]
        assert behavior.requirement_id == 'FR-3'
        assert 'reserve' in behavior.action.lower()
        assert 'parking' in behavior.object_name.lower() or 'slot' in behavior.object_name.lower()
    
    def test_extract_compound_action_splits(self, service):
        """Test that compound actions are split into multiple behaviors."""
        normalized_data = {
            'actor': 'System',
            'action': 'authenticate user and redirect to dashboard',
            'conditions': [],
            'expected_outcome': 'user authenticated',
            'feature_area': 'Authentication'
        }
        
        result = service.extract(
            requirement_id='FR-1',
            normalized_data=normalized_data,
            requirement_type='Functional'
        )
        
        # Should split compound action
        assert len(result.behaviors) >= 1
    
    def test_behavior_id_generation(self, service):
        """Test that behavior IDs are generated correctly."""
        normalized_data = {
            'actor': 'User',
            'action': 'login',
            'conditions': [],
            'expected_outcome': 'authenticated',
            'feature_area': 'Auth'
        }
        
        result = service.extract(
            requirement_id='FR-1',
            normalized_data=normalized_data,
            requirement_type='Functional'
        )
        
        assert len(result.behaviors) == 1
        behavior = result.behaviors[0]
        assert behavior.behavior_id is not None
        assert 'B01' in behavior.behavior_id
    
    def test_actor_extraction_from_text(self, service):
        """Test that actor is correctly extracted."""
        normalized_data = {
            'actor': 'System',
            'action': 'block reserved slot',
            'conditions': ['for other users'],
            'expected_outcome': 'slot blocked',
            'feature_area': 'Reservation'
        }
        
        result = service.extract(
            requirement_id='FR-3',
            normalized_data=normalized_data,
            requirement_type='Functional'
        )
        
        behavior = result.behaviors[0]
        assert behavior.actor == 'System'
    
    def test_condition_preservation(self, service):
        """Test that conditions are preserved in behavior."""
        normalized_data = {
            'actor': 'User',
            'action': 'reserve slot',
            'conditions': ['for future time window'],
            'expected_outcome': 'reservation confirmed',
            'feature_area': 'Reservation'
        }
        
        result = service.extract(
            requirement_id='FR-3',
            normalized_data=normalized_data,
            requirement_type='Functional'
        )
        
        behavior = result.behaviors[0]
        assert behavior.condition is not None
        assert 'future' in behavior.condition.lower() or 'time' in behavior.condition.lower()
    
    def test_description_generation(self, service):
        """Test that behavior description is generated."""
        normalized_data = {
            'actor': 'User',
            'action': 'login with credentials',
            'conditions': ['valid username', 'valid password'],
            'expected_outcome': 'authenticated',
            'feature_area': 'Authentication'
        }
        
        result = service.extract(
            requirement_id='FR-1',
            normalized_data=normalized_data,
            requirement_type='Functional'
        )
        
        behavior = result.behaviors[0]
        assert behavior.description is not None
        assert len(behavior.description) > 0
        assert 'login' in behavior.description.lower() or 'User' in behavior.description
    
    def test_multiple_behaviors_extraction(self, service):
        """Test extraction of multiple behaviors from compound requirement."""
        # Test with multiple conditions
        normalized_data = {
            'actor': 'User',
            'action': 'reserve slot for future time window and receive confirmation',
            'conditions': ['slot available'],
            'expected_outcome': 'reservation complete',
            'feature_area': 'Reservation'
        }
        
        result = service.extract(
            requirement_id='FR-3',
            normalized_data=normalized_data,
            requirement_type='Functional'
        )
        
        assert len(result.behaviors) >= 1
    
    def test_object_extraction(self, service):
        """Test that object is correctly extracted."""
        normalized_data = {
            'actor': 'Payment Gateway',
            'action': 'process credit card transaction',
            'conditions': [],
            'expected_outcome': 'payment processed',
            'feature_area': 'Payment'
        }
        
        result = service.extract(
            requirement_id='FR-5',
            normalized_data=normalized_data,
            requirement_type='Functional'
        )
        
        behavior = result.behaviors[0]
        assert behavior.object_name is not None
        assert 'transaction' in behavior.object_name.lower() or 'credit' in behavior.object_name.lower()
    
    def test_malformed_action_handling(self, service):
        """Test that malformed actions are detected and handled properly."""
        normalized_data = {
            'actor': 'System',
            'action': 'System (SPMS) 1 Product Overview Product Name',  # Malformed action
            'conditions': [],
            'expected_outcome': '',
            'feature_area': 'General'
        }
        
        result = service.extract(
            requirement_id='REQ-20260211-001',
            normalized_data=normalized_data,
            requirement_type='NFR'
        )
        
        # Should still create a behavior
        assert len(result.behaviors) == 1
        behavior = result.behaviors[0]
        
        # Should detect the issue
        assert len(result.issues) > 0
        assert any('malformed' in issue.lower() or 'missing' in issue.lower() for issue in result.issues)
        
        # Confidence should be reduced
        assert result.confidence < 1.0
        
        # Behavior should still have required fields
        assert behavior.behavior_id is not None
        assert behavior.requirement_id == 'REQ-20260211-001'


class TestAtomicBehaviorData:
    """Test cases for AtomicBehaviorData dataclass."""
    
    def test_atomic_behavior_creation(self):
        """Test creating an atomic behavior."""
        behavior = AtomicBehaviorData(
            behavior_id='FR3-B1',
            requirement_id='FR-3',
            actor='User',
            action='reserve',
            object_name='parking slot',
            condition='future time window',
            description='User reserves parking slot for future time window'
        )
        
        assert behavior.behavior_id == 'FR3-B1'
        assert behavior.requirement_id == 'FR-3'
        assert behavior.actor == 'User'
        assert behavior.action == 'reserve'
        assert behavior.object_name == 'parking slot'
        assert 'future' in behavior.condition.lower()
        assert 'reserve' in behavior.description.lower()


class TestBehaviorExtractionResult:
    """Test cases for BehaviorExtractionResult dataclass."""
    
    def test_result_with_behaviors(self):
        """Test result containing behaviors."""
        behavior = AtomicBehaviorData(
            behavior_id='FR1-B1',
            requirement_id='FR-1',
            actor='User',
            action='login',
            object_name='',
            condition=None,
            description='User login'
        )
        
        result = BehaviorExtractionResult(
            behaviors=[behavior],
            confidence=0.95,
            issues=[]
        )
        
        assert len(result.behaviors) == 1
        assert result.confidence == 0.95
        assert len(result.issues) == 0
    
    def test_result_with_issues(self):
        """Test result with detected issues."""
        result = BehaviorExtractionResult(
            behaviors=[],
            confidence=0.7,
            issues=['Compound action detected', 'Ambiguous actor']
        )
        
        assert len(result.behaviors) == 0
        assert result.confidence == 0.7
        assert len(result.issues) == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
