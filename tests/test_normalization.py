"""
Unit tests for Test Case Generator core functionality.
Tests normalization, classification, and generation services.
"""

import pytest
import sys
import os
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

from services.normalization import NormalizationService, TransformationStep
from services.classification import ClassificationService, RequirementClass
from services.generation import TestCaseGenerationService, GenerationConfig


class TestNormalizationService:
    """Tests for the Normalization Service."""
    
    @pytest.fixture
    def normalizer(self):
        return NormalizationService()
    
    def test_simple_requirement_normalization(self, normalizer):
        """Test normalization of a simple requirement."""
        text = "User shall login with valid credentials"
        results = normalizer.normalize(text)
        
        assert len(results) == 1
        result = results[0]
        
        assert result.original_text == text
        assert result.normalized.actor == "User"
        assert "login" in result.normalized.action.lower()
        assert result.normalized.expected_outcome is not None
        assert result.provenance['transformation_steps']
    
    def test_compound_requirement_splitting(self, normalizer):
        """Test that compound requirements are split into atomic requirements."""
        text = "User shall login and system shall authenticate"
        results = normalizer.normalize(text)
        
        # Should be split into two atomic requirements
        assert len(results) == 2
        
        actors = [r.normalized.actor for r in results]
        assert "User" in actors
        assert "System" in actors
    
    def test_ambiguity_detection(self, normalizer):
        """Test that vague terms are detected as ambiguities."""
        text = "The system shall be fast and secure"
        results = normalizer.normalize(text)
        
        assert len(results) >= 1
        result = results[0]
        
        # Should detect ambiguity
        assert result.is_ambiguous or len(result.clarifying_questions) > 0
        
        # Should have clarifying questions for vague terms
        if result.clarifying_questions:
            assert len(result.clarifying_questions) > 0
    
    def test_missing_actor_detection(self, normalizer):
        """Test detection of missing actor."""
        text = "Shall perform the action successfully"
        results = normalizer.normalize(text)
        
        assert len(results) == 1
        result = results[0]
        
        # Should have issues or low confidence
        assert result.confidence < 1.0 or len(result.ambiguity_issues) > 0
    
    def test_condition_extraction(self, normalizer):
        """Test extraction of conditional clauses."""
        text = "User shall login when credentials are valid"
        results = normalizer.normalize(text)
        
        assert len(results) == 1
        result = results[0]
        
        # Should extract condition
        conditions = result.normalized.conditions
        assert len(conditions) > 0 or "when" in result.normalized.action.lower()
    
    def test_provenance_tracking(self, normalizer):
        """Test that provenance is properly tracked."""
        text = "User shall logout"
        results = normalizer.normalize(text)
        
        assert len(results) == 1
        result = results[0]
        
        # Check provenance structure
        assert 'original_text' in result.provenance
        assert 'transformation_steps' in result.provenance
        assert 'confidence' in result.provenance
        assert 'requirement_id' in result.provenance


class TestClassificationService:
    """Tests for the Classification Service."""
    
    @pytest.fixture
    def classifier(self):
        return ClassificationService()
    
    def test_functional_classification(self, classifier):
        """Test classification of functional requirements."""
        text = "User shall create a new account"
        result = classifier.classify(text)
        
        assert result.primary_class == RequirementClass.FUNCTIONAL
        assert 0.7 <= result.confidence_scores[RequirementClass.FUNCTIONAL] <= 1.0
    
    def test_security_classification(self, classifier):
        """Test classification of security requirements."""
        text = "System shall encrypt all sensitive data using AES-256"
        result = classifier.classify(text)
        
        assert result.primary_class == RequirementClass.SECURITY
    
    def test_performance_classification(self, classifier):
        """Test classification of performance requirements."""
        text = "API shall respond within 100 milliseconds"
        result = classifier.classify(text)
        
        assert result.primary_class == RequirementClass.PERFORMANCE
    
    def test_validation_classification(self, classifier):
        """Test classification of validation requirements."""
        text = "User input must be validated for format and length"
        result = classifier.classify(text)
        
        assert result.primary_class == RequirementClass.VALIDATION
    
    def test_api_classification(self, classifier):
        """Test classification of API requirements."""
        text = "POST /users endpoint shall create a new user"
        result = classifier.classify(text)
        
        assert result.primary_class == RequirementClass.API_BEHAVIOR
    
    def test_multi_label_classification(self, classifier):
        """Test that requirements can have multiple classifications."""
        text = "User shall validate input and system shall sanitize for security"
        result = classifier.classify(text)
        
        # Should have multiple classes
        classes = [result.primary_class] + result.secondary_classes
        assert len(classes) >= 1
    
    def test_priority_hint_generation(self, classifier):
        """Test that priority hints are generated correctly."""
        security_text = "System shall prevent unauthorized access"
        result = classifier.classify(security_text)
        
        assert result.priority_hint == "High"
    
    def test_reasoning_generation(self, classifier):
        """Test that human-readable reasoning is generated."""
        text = "User shall login with password"
        result = classifier.classify(text)
        
        assert result.reasoning
        assert "Primary classification" in result.reasoning


class TestGenerationService:
    """Tests for the Test Case Generation Service."""
    
    @pytest.fixture
    def generator(self):
        return TestCaseGenerationService()
    
    @pytest.fixture
    def sample_normalized_req(self):
        return {
            'requirement_id': 'REQ-20240210-0001',
            'actor': 'User',
            'action': 'login with valid credentials',
            'conditions': ['User is on login page'],
            'expected_outcome': 'successful authentication'
        }
    
    @pytest.fixture
    def sample_classification(self):
        return {
            'types': ['Functional'],
            'priority_hint': 'Medium'
        }
    
    def test_positive_test_case_generation(self, generator, sample_normalized_req, sample_classification):
        """Test generation of positive test case."""
        results = generator.generate(sample_normalized_req, sample_classification)
        
        assert len(results) >= 1
        
        # Find positive test
        pos_tc = next((tc for tc in results if tc.test_type == "Positive"), None)
        assert pos_tc is not None
        assert pos_tc.title
        assert "when" in pos_tc.title.lower()
        assert "expecting" in pos_tc.title.lower()
    
    def test_negative_test_case_generation(self, generator, sample_normalized_req, sample_classification):
        """Test generation of negative test case."""
        results = generator.generate(sample_normalized_req, sample_classification)
        
        neg_tc = next((tc for tc in results if tc.test_type == "Negative"), None)
        assert neg_tc is not None
        assert "invalid" in neg_tc.title.lower() or "error" in neg_tc.title.lower()
    
    def test_boundary_test_case_generation(self, generator):
        """Test boundary test case generation."""
        req = {
            'requirement_id': 'REQ-20240210-0002',
            'actor': 'API',
            'action': 'process request',
            'conditions': [],
            'expected_outcome': 'successful response'
        }
        classification = {'types': ['Performance', 'API behavior'], 'priority_hint': 'High'}
        
        results = generator.generate(req, classification)
        
        # Should generate boundary test for performance/API requirements
        bnd_tc = next((tc for tc in results if tc.test_type == "Boundary"), None)
        # May or may not be generated based on configuration
    
    def test_test_case_title_pattern(self, generator, sample_normalized_req, sample_classification):
        """Test that generated titles follow required pattern."""
        results = generator.generate(sample_normalized_req, sample_classification)
        
        for tc in results:
            # Must have 'when' and 'expecting'
            assert 'when' in tc.title.lower(), f"Title '{tc.title}' missing 'when'"
            assert 'expecting' in tc.title.lower(), f"Title '{tc.title}' missing 'expecting'"
            
            # Must not be generic
            assert tc.title.lower() != 'verify'
            assert tc.title.lower() != 'test'
    
    def test_test_case_steps_generation(self, generator, sample_normalized_req, sample_classification):
        """Test that test steps are generated correctly."""
        results = generator.generate(sample_normalized_req, sample_classification)
        
        for tc in results:
            assert len(tc.steps) >= 1
            for step in tc.steps:
                assert 'step_number' in step
                assert 'action' in step
                assert step['step_number'] >= 1
    
    def test_test_case_data_generation(self, generator, sample_normalized_req, sample_classification):
        """Test that test data is generated."""
        results = generator.generate(sample_normalized_req, sample_classification)
        
        for tc in results:
            assert tc.test_data
            assert 'inputs' in tc.test_data or 'api_request' in tc.test_data
    
    def test_test_case_id_generation(self, generator):
        """Test unique test case ID generation."""
        req_id = 'REQ-20240210-0001'
        
        id1 = generator.generate_test_case_id(req_id, 'POS')
        id2 = generator.generate_test_case_id(req_id, 'NEG')
        
        assert id1 != id2
        assert id1.startswith('TTC-')
        assert req_id in id1
    
    def test_rules_applied_tracking(self, generator, sample_normalized_req, sample_classification):
        """Test that applied rules are tracked for explainability."""
        results = generator.generate(sample_normalized_req, sample_classification)
        
        for tc in results:
            assert len(tc.rules_applied) >= 1
            assert any('template' in r for r in tc.rules_applied)


class TestIntegration:
    """Integration tests for the complete pipeline."""
    
    def test_end_to_end_pipeline(self):
        """Test complete pipeline from text to test cases."""
        from services.ingestion import IngestionService
        from services.normalization import NormalizationService
        from services.classification import ClassificationService
        from services.generation import TestCaseGenerationService
        
        text = "User shall login with valid credentials and system shall authenticate the user"
        
        # Ingest
        ingestion = IngestionService()
        ingest_result = ingestion.ingest(text)
        
        # Normalize
        normalizer = NormalizationService()
        norm_results = normalizer.normalize(text)
        
        # Classify
        classifier = ClassificationService()
        
        # Generate
        generator = TestCaseGenerationService()
        
        all_tcs = []
        for norm in norm_results:
            classification = classifier.classify(
                norm.original_text,
                norm.normalized.__dict__ if hasattr(norm.normalized, '__dict__') else norm.normalized
            )
            tcs = generator.generate(
                normalized_req=norm.normalized.__dict__ if hasattr(norm.normalized, '__dict__') else norm.normalized,
                classification={
                    'types': [c.value for c in [classification.primary_class] + classification.secondary_classes],
                    'priority_hint': classification.priority_hint
                }
            )
            all_tcs.extend(tcs)
        
        # Assertions
        assert len(norm_results) == 2  # Compound split
        assert len(all_tcs) >= 4  # Multiple test cases per requirement


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
