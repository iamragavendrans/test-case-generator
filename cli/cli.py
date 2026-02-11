#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Tool for Test Case Generator.
Provides command-line interface for generating test cases from requirements.
"""

import sys
import os
import io
import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))

from services.ingestion import IngestionService
from services.normalization import NormalizationService
from services.classification import ClassificationService
from services.generation import TestCaseGenerationService, GenerationConfig


class TestCaseGeneratorCLI:
    """
    Command-line interface for Test Case Generator.
    
    Usage:
        python -m cli.cli generate "User shall login with valid credentials"
        python -m cli.cli generate --file requirements.txt --output ./output
        python -m cli.cli batch requirements.txt --format json
    """
    
    def __init__(self):
        self.ingestion_service = IngestionService()
        self.normalization_service = NormalizationService()
        self.classification_service = ClassificationService()
        self.generation_service = TestCaseGenerationService()
    
    def generate(
        self, 
        text: str, 
        output_dir: Optional[str] = None,
        verbose: bool = False
    ) -> dict:
        """
        Generate test cases from a single requirement.
        
        Args:
            text: Raw requirement text
            output_dir: Directory to save output files
            verbose: Enable verbose output
            
        Returns:
            Dictionary containing normalized requirements and test cases
        """
        print(f"\n{'='*60}")
        print("AI TEST CASE GENERATOR - CLI")
        print(f"{'='*60}")
        print(f"\n[INPUT] Requirement:")
        print(f"   {text}")
        print()
        
        # Step 1: Ingestion
        print("[STEP 1] Ingesting and sanitizing...")
        ingestion_result = self.ingestion_service.ingest(text)
        print(f"   [OK] Created {len(ingestion_result.chunks)} chunks")
        if ingestion_result.sanitization_warnings:
            for warning in ingestion_result.sanitization_warnings:
                print(f"   [WARN] {warning}")
        
        # Step 2: Normalization
        print("\n[STEP 2] Normalizing (Actor-Action-Conditions-Outcome)...")
        norm_results = self.normalization_service.normalize(text)
        print(f"   [OK] Generated {len(norm_results)} normalized requirement(s)")
        
        # Step 3: Classification
        print("\n[STEP 3] Classifying requirement type...")
        for norm in norm_results:
            classification = self.classification_service.classify(
                norm.original_text,
                norm.normalized.__dict__ if hasattr(norm.normalized, '__dict__') else norm.normalized
            )
            print(f"   [OK] Primary: {classification.primary_class.value}")
            if classification.secondary_classes:
                print(f"      Secondary: {', '.join(c.value for c in classification.secondary_classes)}")
        
        # Step 4: Generate Test Cases
        print("\n[STEP 4] Generating test cases...")
        all_test_cases = []
        all_normalized = []
        
        for norm in norm_results:
            classification = self.classification_service.classify(
                norm.original_text,
                norm.normalized.__dict__ if hasattr(norm.normalized, '__dict__') else norm.normalized
            )
            
            generated = self.generation_service.generate(
                normalized_req=norm.normalized.__dict__ if hasattr(norm.normalized, '__dict__') else norm.normalized,
                classification={
                    'types': [c.value for c in [classification.primary_class] + classification.secondary_classes],
                    'priority_hint': classification.priority_hint
                },
                ambiguity={
                    'is_ambiguous': norm.is_ambiguous,
                    'issues': [i.description for i in norm.ambiguity_issues] if norm.ambiguity_issues else [],
                    'clarifying_questions': norm.clarifying_questions
                } if norm.is_ambiguous else None
            )
            
            all_test_cases.extend(generated)
            all_normalized.append({
                'requirement_id': norm.provenance.get('requirement_id', 'REQ-UNKNOWN'),
                'source_text': norm.original_text,
                'normalized': norm.normalized.__dict__ if hasattr(norm.normalized, '__dict__') else norm.normalized,
                'classification': [classification.primary_class.value] + [c.value for c in classification.secondary_classes],
                'priority_hint': classification.priority_hint,
                'ambiguity': {
                    'is_ambiguous': norm.is_ambiguous,
                    'issues': [i.description for i in norm.ambiguity_issues] if norm.ambiguity_issues else [],
                    'clarifying_questions': norm.clarifying_questions
                },
                'provenance': norm.provenance
            })
        
        print(f"   ✅ Generated {len(all_test_cases)} test case(s)")
        
        # Step 5: Build Output
        output = {
            'normalized_requirements': all_normalized,
            'test_cases': [
                {
                    'test_case_id': self.generation_service.generate_test_case_id(tc.requirement_id, tc.test_type[:3].upper()),
                    'title': tc.title,
                    'mapped_requirement_id': tc.requirement_id,
                    'test_type': tc.test_type,
                    'preconditions': tc.preconditions,
                    'steps': tc.steps,
                    'test_data': tc.test_data,
                    'expected_result': tc.expected_result,
                    'priority': self.generation_service._map_priority(
                        classification.priority_hint,
                        tc.test_type[:3].upper()
                    ),
                    'automation_feasibility': {
                        'feasible': True,
                        'notes': 'Standard test case',
                        'estimated_effort': 'Medium'
                    },
                    'determinism_seed': self.generation_service.config.determinism_seed,
                    'explainability': {
                        'generation_template_id': tc.template_id,
                        'rules_applied': tc.rules_applied,
                        'confidence': norm.confidence * 0.9
                    }
                }
                for tc in all_test_cases
            ],
            'audit_log': {
                'generation_timestamp': datetime.utcnow().isoformat(),
                'generator_version': '1.0.0',
                'model_reference': 'rule-based-v1',
                'validation_status': 'passed',
                'errors': [],
                'change_history': [
                    {
                        'timestamp': datetime.utcnow().isoformat(),
                        'actor': 'system',
                        'change': 'Generated via CLI',
                        'diff': None
                    }
                ]
            }
        }
        
        # Print Summary
        self._print_summary(output, verbose)
        
        # Save to file
        if output_dir:
            self._save_output(output, output_dir)
        
        return output
    
    def _print_summary(self, output: dict, verbose: bool = False):
        """Print summary of generated test cases."""
        print(f"\n{'='*60}")
        print("GENERATION SUMMARY")
        print(f"{'='*60}")
        
        print(f"\n📊 Statistics:")
        print(f"   Requirements Processed: {len(output['normalized_requirements'])}")
        print(f"   Test Cases Generated: {len(output['test_cases'])}")
        
        # Print test cases
        print(f"\n📋 Generated Test Cases:")
        for tc in output['test_cases']:
            print(f"\n   [{tc['test_type']}] {tc['title']}")
            print(f"   ID: {tc['test_case_id']}")
            print(f"   Priority: {tc['priority']}")
            if verbose:
                print(f"   Preconditions: {', '.join(tc['preconditions'][:2])}")
                print(f"   Steps: {len(tc['steps'])} steps")
                print(f"   Expected: {tc['expected_result'][:80]}...")
        
        # Print ambiguities
        ambiguous = [r for r in output['normalized_requirements'] if r.get('ambiguity', {}).get('is_ambiguous')]
        if ambiguous:
            print(f"\n⚠️  Ambiguous Requirements ({len(ambiguous)}):")
            for req in ambiguous:
                print(f"\n   ID: {req['requirement_id']}")
                print(f"   Issues:")
                for issue in req['ambiguity'].get('issues', []):
                    print(f"      - {issue}")
                print(f"   Clarifying Questions:")
                for q in req['ambiguity'].get('clarifying_questions', []):
                    print(f"      ? {q}")
    
    def _save_output(self, output: dict, output_dir: str):
        """Save output to JSON file."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = os.path.join(output_dir, f'tc-output-{timestamp}.json')
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Output saved to: {filename}")
        
        # Also save markdown report
        md_filename = os.path.join(output_dir, f'tc-report-{timestamp}.md')
        self._save_markdown_report(output, md_filename)
        print(f"📄 Markdown report saved to: {md_filename}")
    
    def _save_markdown_report(self, output: dict, filename: str):
        """Generate human-readable markdown report."""
        lines = [
            "# Test Case Generation Report",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Summary",
            f"- Requirements Processed: {len(output['normalized_requirements'])}",
            f"- Test Cases Generated: {len(output['test_cases'])}",
            "",
            "## Normalized Requirements",
            "",
        ]
        
        for req in output['normalized_requirements']:
            lines.extend([
                f"### {req['requirement_id']}",
                f"**Source:** {req['source_text']}",
                "",
                f"**Normalized:**",
                f"- Actor: {req['normalized'].get('actor', 'N/A')}",
                f"- Action: {req['normalized'].get('action', 'N/A')}",
                f"- Conditions: {', '.join(req['normalized'].get('conditions', []))}",
                f"- Expected Outcome: {req['normalized'].get('expected_outcome', 'N/A')}",
                "",
                f"**Classification:** {', '.join(req['classification'])}",
                f"**Priority:** {req['priority_hint']}",
                "",
            ])
        
        lines.extend([
            "## Generated Test Cases",
            "",
        ])
        
        for tc in output['test_cases']:
            lines.extend([
                f"### {tc['test_case_id']}",
                f"**Title:** {tc['title']}",
                f"**Type:** {tc['test_type']}",
                f"**Priority:** {tc['priority']}",
                f"**Mapped Requirement:** {tc['mapped_requirement_id']}",
                "",
                f"**Preconditions:**",
            ])
            for p in tc['preconditions']:
                lines.append(f"- {p}")
            lines.extend([
                "",
                "**Steps:",
            ])
            for step in tc['steps']:
                lines.append(f"{step['step_number']}. {step['action']}")
                if step.get('expected_intermediate'):
                    lines.append(f"   Expected: {step['expected_intermediate']}")
            lines.extend([
                "",
                f"**Expected Result:** {tc['expected_result']}",
                "",
            ])
        
        with open(filename, 'w') as f:
            f.write('\n'.join(lines))
    
    def batch_process(
        self, 
        input_file: str,
        output_dir: Optional[str] = None,
        verbose: bool = False
    ) -> List[dict]:
        """
        Process multiple requirements from a file.
        
        Args:
            input_file: Path to file containing requirements (one per line)
            output_dir: Directory to save output files
            verbose: Enable verbose output
            
        Returns:
            List of output dictionaries for each requirement
        """
        print(f"\n{'='*60}")
        print("BATCH PROCESSING MODE")
        print(f"{'='*60}")
        
        if not os.path.exists(input_file):
            print(f"❌ Error: Input file not found: {input_file}")
            return []
        
        with open(input_file, 'r') as f:
            requirements = [line.strip() for line in f if line.strip()]
        
        print(f"\n📄 Loaded {len(requirements)} requirements from {input_file}")
        
        results = []
        for i, req in enumerate(requirements, 1):
            print(f"\n{'─'*40}")
            print(f"Processing requirement {i}/{len(requirements)}")
            result = self.generate(req, output_dir=None, verbose=verbose)
            results.append(result)
        
        # Combine results
        combined = {
            'normalized_requirements': [],
            'test_cases': [],
            'audit_log': {
                'generation_timestamp': datetime.utcnow().isoformat(),
                'generator_version': '1.0.0',
                'model_reference': 'rule-based-v1',
                'validation_status': 'passed',
                'errors': [],
                'change_history': []
            }
        }
        
        for r in results:
            combined['normalized_requirements'].extend(r['normalized_requirements'])
            combined['test_cases'].extend(r['test_cases'])
            combined['audit_log']['change_history'].extend(r['audit_log']['change_history'])
        
        if output_dir:
            self._save_output(combined, output_dir)
            print(f"\n💾 Combined output saved")
        
        self._print_summary(combined, verbose)
        
        return results


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="AI Test Case Generator - Generate high-quality test cases from requirements",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from single requirement
  python cli/cli.py generate "User shall login with valid credentials"
  
  # Generate with verbose output
  python cli/cli.py generate "System shall validate input" --verbose
  
  # Process requirements from file
  python cli/cli.py batch requirements.txt --output ./output
  
  # Use Docker
  docker-compose run --rm backend python -m cli.cli generate "User shall..."
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Generate command
    gen_parser = subparsers.add_parser('generate', help='Generate test cases from a requirement')
    gen_parser.add_argument('requirement', help='Requirement text')
    gen_parser.add_argument('-o', '--output', help='Output directory', default='./output')
    gen_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Process multiple requirements from file')
    batch_parser.add_argument('input_file', help='File containing requirements (one per line)')
    batch_parser.add_argument('-o', '--output', help='Output directory', default='./output')
    batch_parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    # Serve command
    serve_parser = subparsers.add_parser('serve', help='Start API server')
    serve_parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    serve_parser.add_argument('--port', type=int, default=8000, help='Port to bind')
    
    args = parser.parse_args()
    
    if args.command == 'generate':
        cli = TestCaseGeneratorCLI()
        cli.generate(args.requirement, args.output, args.verbose)
    
    elif args.command == 'batch':
        cli = TestCaseGeneratorCLI()
        cli.batch_process(args.input_file, args.output, args.verbose)
    
    elif args.command == 'serve':
        import uvicorn
        uvicorn.run(
            'backend.main:app',
            host=args.host,
            port=args.port,
            reload=True
        )
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
