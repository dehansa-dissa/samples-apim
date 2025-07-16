#!/usr/bin/env python3
"""
Test runner script for the interceptor service tests.
Provides convenient commands to run tests.
"""

import os
import sys
import subprocess
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TestRunner:
    """Handles test execution and configuration."""
    
    TEST_MODULES = {
        'all': [],  # Empty means run all tests
        'apichat': ['test_api_chat.py'],
        'marketplaceassistant': ['test_marketplace_assistant.py'],
        'specpopulator': ['test_spec_populator.py'],
        'apidesignassistant': ['test_api_design_assistant.py'],
    }
    
    def __init__(self):
        self.base_cmd = ['python', '-m', 'pytest']
    
    def run_tests(self, verbose: bool = False) -> int:
        """
        Run tests with specified configuration.
        
        Args:
            verbose: Enable verbose output
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        # Get test type from environment variable
        test_type = os.getenv("TEST_TYPE", "all").lower()
        if test_type not in self.TEST_MODULES:
            print(f"Warning: Invalid TEST_TYPE '{test_type}' in environment, using 'all'")
            test_type = 'all'
        
        cmd = self._build_command(test_type, verbose)
        description = f"Running {test_type} tests"
        return self._execute_command(cmd, description)
    
    def _build_command(self, test_type: str, verbose: bool) -> list[str]:
        """Build pytest command with specified options."""
        cmd = self.base_cmd.copy()
        
        # Add test modules if specific type is selected
        if test_type in self.TEST_MODULES:
            test_modules = self.TEST_MODULES[test_type]
            if test_modules:  # If specific modules are defined
                cmd.extend(test_modules)
        
        if verbose:
            cmd.append('-v')
        
        return cmd
    
    def _execute_command(self, cmd: list[str], description: str) -> int:
        """Execute command and handle the result."""
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"Command: {' '.join(cmd)}")
        print('='*60)
        
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print(f"Passed: {description}")
        else:
            print(f"Failed: {description}")
        
        return result.returncode


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description='Run interceptor service tests',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --verbose
  TEST_TYPE=apichat %(prog)s
  TEST_TYPE=specpopulator %(prog)s --verbose
        """
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    return parser


def main():
    """Main entry point."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    test_runner = TestRunner()
    exit_code = test_runner.run_tests(verbose=args.verbose)
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
