"""
Unit tests for Coverage Calculation Service.
Tests the coverage_score = test_types_generated / required_dimensions formula.
"""

import pytest
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.coverage import (
    CoverageService,
    CoverageResult,
    DimensionApplicabilityChecker,
    Dimension
)


class TestDimensionApplicabilityChecker:
    """Test cases for DimensionApplicabilityChecker."""
    
    @pytest.fixture
    def checker(self):
        """Create a fresh checker instance."""
        return DimensionApplicabilityChecker()
    
    def test_functional_dimension_always_required(self, checker):
        """Test that Functional dimension is always required."""
        required = checker.get_required_dimensions(
            requirement_text="User shall login",
            requirement_types=['Functional'],
            behavior_data={}
        )
        
        assert Dimension.FUNCTIONAL in required
    
    def test_negative_dimension_always_required(self, checker):
        """Test that Negative dimension is always required."""
        required = checker.get_required_dimensions(
            requirement_text="User shall login",
            requirement_types=['Functional'],
            behavior_data={}
        )
        
        assert Dimension.NEGATIVE in required
    
    def test_performance_dimension_triggered(self, checker):
        """Test that Performance dimension is triggered by performance keywords."""
        required = checker.get_required_dimensions(
            requirement_text="API shall respond within 100 milliseconds",
            requirement_types=['Performance'],
            behavior_data={}
        )
        
        assert Dimension.PERFORMANCE in required
    
    def test_security_dimension_triggered(self, checker):
        """Test that Security dimension is triggered by security keywords."""
        required = checker.get_required_dimensions(
            requirement_text="System shall encrypt sensitive data",
            requirement_types=['Security'],
            behavior_data={}
        )
        
        assert Dimension.SECURITY in required
    
    def test_concurrency_dimension_triggered(self, checker):
        """Test that Concurrency dimension is triggered by concurrency keywords."""
        required = checker.get_required_dimensions(
            requirement_text="System shall handle concurrent requests",
            requirement_types=['Functional'],
            behavior_data={}
        )
        
        assert Dimension.CONCURRENCY in required
    
    def test_payment_flow_requires_security(self, checker):
        """Test that payment flows require Security dimension."""
        required = checker.get_required_dimensions(
            requirement_text="Payment gateway shall process credit card transactions",
            requirement_types=['Functional'],
            behavior_data={}
        )
        
        assert Dimension.SECURITY in required
        assert Dimension.FAILURE in required
    
    def test_shared_resource_requires_concurrency(self, checker):
        """Test that shared resources require Concurrency dimension."""
        required = checker.get_required_dimensions(
            requirement_text="Users shall reserve parking slots",
            requirement_types=['Functional'],
            behavior_data={}
        )
        
        assert Dimension.CONCURRENCY in required
    
    def test_boundary_dimension_with_measurable_inputs(self, checker):
        """Test that Boundary dimension is triggered for measurable inputs."""
        required = checker.get_required_dimensions(
            requirement_text="System shall validate input value between 1 and 100",
            requirement_types=['Validation'],
            behavior_data={}
        )
        
        assert Dimension.BOUNDARY in required
    
    def test_edge_dimension_with_conditions(self, checker):
        """Test that Edge dimension is triggered when conditions exist."""
        required = checker.get_required_dimensions(
            requirement_text="User shall login if credentials are valid",
            requirement_types=['Functional'],
            behavior_data={'conditions': ['credentials valid']}
        )
        
        assert Dimension.EDGE in required
    
    def test_nfr_requires_performance_and_failure(self, checker):
        """Test that NFR requirements require Performance and Failure dimensions."""
        required = checker.get_required_dimensions(
            requirement_text="System shall maintain 99.9% uptime",
            requirement_types=['NFR'],
            behavior_data={}
        )
        
        assert Dimension.PERFORMANCE in required
        assert Dimension.FAILURE in required


class TestCoverageService:
    """Test cases for CoverageService."""
    
    @pytest.fixture
    def service(self):
        """Create a fresh service instance."""
        return CoverageService()
    
    def test_coverage_calculation_full_coverage(self, service):
        """Test coverage calculation with full coverage."""
        test_cases = [
            {'behavior_id': 'FR1-B1', 'test_type': 'Functional', 'mapped_requirement_id': 'FR-1'},
            {'behavior_id': 'FR1-B1', 'test_type': 'Negative', 'mapped_requirement_id': 'FR-1'},
            {'behavior_id': 'FR1-B1', 'test_type': 'Edge', 'mapped_requirement_id': 'FR-1'},
            {'behavior_id': 'FR1-B1', 'test_type': 'Boundary', 'mapped_requirement_id': 'FR-1'},
        ]
        
        requirements = [
            {'requirement_id': 'FR-1', 'source_text': 'User shall login', 
             'classification': ['Functional'], 'normalized': {}}
        ]
        
        behaviors = [
            {'behavior_id': 'FR1-B1', 'requirement_id': 'FR-1'}
        ]
        
        result = service.calculate(test_cases, requirements, behaviors)
        
        assert result.overall_coverage >= 0
        assert 'FR-1' in result.requirement_coverage
    
    def test_coverage_calculation_partial_coverage(self, service):
        """Test coverage calculation with partial coverage."""
        test_cases = [
            {'behavior_id': 'FR1-B1', 'test_type': 'Functional', 'mapped_requirement_id': 'FR-1'},
        ]
        
        requirements = [
            {'requirement_id': 'FR-1', 'source_text': 'User shall login', 
             'classification': ['Functional'], 'normalized': {}}
        ]
        
        behaviors = [
            {'behavior_id': 'FR1-B1', 'requirement_id': 'FR-1'}
        ]
        
        result = service.calculate(test_cases, requirements, behaviors)
        
        assert result.overall_coverage >= 0
        assert 'FR-1' in result.requirement_coverage
    
    def test_coverage_with_no_test_cases(self, service):
        """Test coverage calculation with no test cases."""
        result = service.calculate(
            test_cases=[],
            requirements=[
                {'requirement_id': 'FR-1', 'source_text': 'User shall login', 
                 'classification': ['Functional'], 'normalized': {}}
            ],
            behaviors=[]
        )
        
        assert result.overall_coverage == 0
        assert 'FR-1' in result.requirement_coverage
        assert result.requirement_coverage['FR-1'] == 0
    
    def test_coverage_with_gaps_detected(self, service):
        """Test that gaps are detected correctly."""
        test_cases = [
            {'behavior_id': 'FR1-B1', 'test_type': 'Functional', 'mapped_requirement_id': 'FR-1'},
            # Missing: Negative, Edge, Boundary, Performance, Security, etc.
        ]
        
        requirements = [
            {'requirement_id': 'FR-1', 
             'source_text': 'Payment gateway shall process transactions securely with high performance',
             'classification': ['Functional', 'Security', 'Performance'], 
             'normalized': {}}
        ]
        
        behaviors = [
            {'behavior_id': 'FR1-B1', 'requirement_id': 'FR-1'}
        ]
        
        result = service.calculate(test_cases, requirements, behaviors)
        
        # Should detect missing dimensions
        assert len(result.gaps_detected) > 0
        # Should mention missing test types
        assert any('Negative' in gap or 'Security' in gap or 'Performance' in gap 
                   for gap in result.gaps_detected)
    
    def test_dimension_coverage_tracking(self, service):
        """Test that dimension coverage is tracked correctly."""
        test_cases = [
            {'behavior_id': 'FR1-B1', 'test_type': 'Functional', 'mapped_requirement_id': 'FR-1'},
            {'behavior_id': 'FR1-B1', 'test_type': 'Negative', 'mapped_requirement_id': 'FR-1'},
            {'behavior_id': 'FR1-B1', 'test_type': 'Security', 'mapped_requirement_id': 'FR-1'},
        ]
        
        requirements = [
            {'requirement_id': 'FR-1', 'source_text': 'System shall authenticate users', 
             'classification': ['Functional', 'Security'], 'normalized': {}}
        ]
        
        behaviors = [
            {'behavior_id': 'FR1-B1', 'requirement_id': 'FR-1'}
        ]
        
        result = service.calculate(test_cases, requirements, behaviors)
        
        assert 'Functional' in result.dimension_coverage
        assert 'Negative' in result.dimension_coverage
        assert 'Security' in result.dimension_coverage
    
    def test_coverage_percentage_capped_at_100(self, service):
        """Test that coverage percentage is capped at 100."""
        # Create test cases with more types than required
        test_cases = [
            {'behavior_id': 'FR1-B1', 'test_type': tc_type, 'mapped_requirement_id': 'FR-1'}
            for tc_type in ['Functional', 'Negative', 'Edge', 'Boundary', 
                           'Performance', 'Security', 'Concurrency', 'Failure', 'Integration']
        ]
        
        requirements = [
            {'requirement_id': 'FR-1', 'source_text': 'User shall login', 
             'classification': ['Functional'], 'normalized': {}}
        ]
        
        behaviors = [
            {'behavior_id': 'FR1-B1', 'requirement_id': 'FR-1'}
        ]
        
        result = service.calculate(test_cases, requirements, behaviors)
        
        # Coverage should not exceed 100
        assert result.requirement_coverage['FR-1'] <= 100


class TestCoverageResult:
    """Test cases for CoverageResult dataclass."""
    
    def test_coverage_result_creation(self):
        """Test creating a coverage result."""
        result = CoverageResult(
            requirement_coverage={'FR-1': 85, 'FR-2': 90},
            overall_coverage=88,
            gaps_detected=['FR-1: Missing Security tests'],
            dimension_coverage={'Functional': 2, 'Negative': 1}
        )
        
        assert result.requirement_coverage['FR-1'] == 85
        assert result.overall_coverage == 88
        assert len(result.gaps_detected) == 1
        assert result.dimension_coverage['Functional'] == 2
    
    def test_coverage_result_defaults(self):
        """Test coverage result with defaults."""
        result = CoverageResult()
        
        assert result.requirement_coverage == {}
        assert result.overall_coverage == 0
        assert result.gaps_detected == []
        assert result.dimension_coverage == {}


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
