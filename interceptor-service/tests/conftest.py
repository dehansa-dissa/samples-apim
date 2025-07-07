
"""
Pytest configuration, utilities and hooks for interceptor service tests.
"""

import os
import json
import pytest
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Dict, Any
import requests
from datetime import datetime
import time

# Try to import dotenv, but don't fail if it's not available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Ensure environment variables are set.")

from constants import (
    AUTH_METHOD_API_KEY, 
    AUTH_METHOD_BEARER, 
    USER_AGENT,
)


class AuthConfig:
    """Configuration for authentication."""
    
    def __init__(self, method: str, token: str):
        self.method = method
        self.token = token


class TestConfig:
    """Configuration for a test endpoint version."""
    
    def __init__(self, version: int, url: str, auth: AuthConfig):
        self.version = version
        self.url = url
        self.auth = auth
    
    def get_headers(self, extra_headers: Dict[str, str] = None) -> Dict[str, str]:
        """Get headers with authentication."""
        headers = {"User-Agent": USER_AGENT}
        
        if self.auth.method == AUTH_METHOD_API_KEY:
            headers["api-key"] = self.auth.token
        elif self.auth.method == AUTH_METHOD_BEARER:
            headers["Authorization"] = f"Bearer {self.auth.token}"
        
        if extra_headers:
            headers.update(extra_headers)
        
        return headers


class BearerToken:
    """Cache for bearer tokens to avoid re-fetching."""
    
    def __init__(self):
        self._cache = {}
    
    def get_token(self, version: int, basic_auth_token: str, token_endpoint: str) -> str:
        """Get or fetch bearer token."""
        if version in self._cache:
            return self._cache[version]
        
        if not token_endpoint:
            pytest.fail(f"TOKEN_ENDPOINT_V{version} is not set for version {version}")
        
        headers = {
            "Authorization": f"Basic {basic_auth_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}
        
        try:
            response = requests.post(token_endpoint, headers=headers, data=data)
            response.raise_for_status()
            
            access_token = response.json().get("access_token")
            if not access_token:
                pytest.fail("'access_token' not found in token endpoint response")
            
            self._cache[version] = access_token
            return access_token
        
        except requests.exceptions.RequestException as e:
            pytest.fail(f"Failed to get bearer token for V{version}: {e}")


# Global bearer token cache
bearer_tokens = BearerToken()

# Cache for version configs
_version_configs_cache = None


def get_version_configs():
    """Generate test configurations for all available versions."""
    global _version_configs_cache
    if _version_configs_cache is not None:
        return _version_configs_cache

    configs = []
    version = 1
    
    while True:
        endpoint = os.getenv(f"ENDPOINT_V{version}")
        token = os.getenv(f"TOKEN_V{version}")

        if not (endpoint and token):
            break
        
        if version == 1:
            auth = AuthConfig(AUTH_METHOD_API_KEY, token)
        else:
            token_endpoint = os.getenv(f"TOKEN_ENDPOINT_V{version}")
            bearer_token = bearer_tokens.get_token(version, token, token_endpoint)
            auth = AuthConfig(AUTH_METHOD_BEARER, bearer_token)
        
        config = TestConfig(version, endpoint, auth)
        configs.append(pytest.param(config, id=f"v{version}"))
        version += 1
    
    if not configs:
        pytest.skip("No versioned endpoints configured")
    
    _version_configs_cache = configs
    return _version_configs_cache

def make_request(
    client: requests.Session,
    method: str,
    url: str,
    headers: Dict[str, str],
    data: Any = None,
    timeout: int = 30
) -> requests.Response:
    """
    Make HTTP request with standard error handling.
    
    Args:
        client: HTTP client session
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        headers: Request headers
        data: Request body data
        expected_status: Expected HTTP status code
        timeout: Request timeout in seconds
    
    Returns:
        Response object
    """
    try:
        response = client.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            timeout=timeout
        )
        
        return response
    
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Request failed: {e}")


def assert_response(response: requests.Response, expected_status: int = None, required_fields: list = None):
    """
    Assert that response is valid JSON with required fields.
    
    Args:
        response: HTTP response object
        required_fields: List of required field names in JSON response
    """
    try:
        json_data = response.json()
    except json.JSONDecodeError:
        pytest.fail(f"Response is not valid JSON: {response.text}")
    
    if expected_status is not None:
            assert response.status_code == expected_status, (
                f"Expected status {expected_status}, got {response.status_code}. "
                f"Response: {response.text}"
            )

    if required_fields:
        for field in required_fields:
            assert field in json_data, f"Required field '{field}' not found in response"
    
    return json_data


class TestReporter:
    """Handles comprehensive test reporting and email notifications."""
    
    def __init__(self):
        self.failed_tests: List = []
        self.passed_tests: List = []
        self.skipped_tests: List = []
        self.test_stats: Dict[str, Any] = {}
        self.start_time: float = 0
        self.end_time: float = 0
        self.smtp_config = {
            'server': os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            'port': int(os.getenv("SMTP_PORT", 587)),
            'user': os.getenv("SMTP_USER"),
            'password': os.getenv("SMTP_PASSWORD"),
            'recipient': os.getenv("RECIPIENT_EMAIL")
        }
    
    def add_test_result(self, report):
        """Add a test result to the appropriate category."""
        if report.when == "call":
            if report.failed:
                self.failed_tests.append(report)
            elif report.passed:
                self.passed_tests.append(report)
            elif report.skipped:
                self.skipped_tests.append(report)
    
    def set_session_start(self):
        """Mark the start time of the test session."""
        self.start_time = time.time()
    
    def set_session_end(self):
        """Mark the end time of the test session."""
        self.end_time = time.time()
    
    def send_test_report(self):
        """Send comprehensive test report via email."""
        # Check if email reporting is enabled
        if not self._is_email_enabled():
            print("Email reporting is disabled. Set SEND_EMAIL_REPORTS=true to enable.")
            return
        
        if not self._validate_email_config():
            print("Email configuration incomplete. Skipping email notification.")
            return
        
        # Calculate test statistics
        self._calculate_test_stats()
        
        # Create report body
        report_body = self._create_comprehensive_report()
        
        # Determine subject and attachment
        if self.failed_tests:
            subject = f"[APIM AI Deployments] Test Report - {len(self.failed_tests)} Failures"
            log_file = "test_failures.log"
            self._write_failure_log(log_file)
            attachment_path = log_file
        else:
            subject = "[APIM AI Deployments] Test Report - All Tests Passed!"
            attachment_path = None
        
        self._send_email(
            subject=subject,
            body=report_body,
            attachment_path=attachment_path
        )
    
    def _is_email_enabled(self) -> bool:
        """Check if email reporting is enabled."""
        return os.getenv("SEND_EMAIL_REPORTS", "true").lower() in ("true", "1", "yes", "on")
    
    def _calculate_test_stats(self):
        """Calculate comprehensive test statistics."""
        total_tests = len(self.passed_tests) + len(self.failed_tests) + len(self.skipped_tests)
        duration = self.end_time - self.start_time
        
        # Categorize tests by module
        test_categories = {}
        for test in self.passed_tests + self.failed_tests + self.skipped_tests:
            module_name = test.nodeid.split("::")[0].replace("test_", "").replace(".py", "")
            if module_name not in test_categories:
                test_categories[module_name] = {"passed": 0, "failed": 0, "skipped": 0}
            
            if test in self.passed_tests:
                test_categories[module_name]["passed"] += 1
            elif test in self.failed_tests:
                test_categories[module_name]["failed"] += 1
            elif test in self.skipped_tests:
                test_categories[module_name]["skipped"] += 1
        
        self.test_stats = {
            "total_tests": total_tests,
            "passed_tests": len(self.passed_tests),
            "failed_tests": len(self.failed_tests),
            "skipped_tests": len(self.skipped_tests),
            "duration": duration,
            "success_rate": (len(self.passed_tests) / total_tests * 100) if total_tests > 0 else 0,
            "test_categories": test_categories,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _create_comprehensive_report(self) -> str:
        """Create a comprehensive test report."""
        stats = self.test_stats
        
        # Header
        report = f"""
APIM AI Deployments - Test Execution Report
{'=' * 60}

📊 SUMMARY
{'─' * 30}
• Total Tests: {stats['total_tests']}
• Passed: {stats['passed_tests']} ✅
• Failed: {stats['failed_tests']} ❌
• Skipped: {stats['skipped_tests']} ⏭️
• Success Rate: {stats['success_rate']:.1f}%
• Duration: {stats['duration']:.2f} seconds
• Timestamp: {stats['timestamp']}

"""
        
        # Overall Status
        if stats['failed_tests'] == 0:
            report += """
🎉 OVERALL STATUS: SUCCESS
All tests passed successfully! The system is functioning correctly.

"""
        else:
            report += f"""
⚠️ OVERALL STATUS: FAILED
{stats['failed_tests']} test(s) failed. Please review the failures below.

"""
        
        # Test Categories Breakdown
        report += f"""
📋 TEST CATEGORIES BREAKDOWN
{'─' * 40}
"""
        
        for category, results in stats['test_categories'].items():
            total_cat = results['passed'] + results['failed'] + results['skipped']
            success_rate = (results['passed'] / total_cat * 100) if total_cat > 0 else 0
            
            status_icon = "✅" if results['failed'] == 0 else "❌"
            report += f"""
{status_icon} {category.replace('_', ' ').title()}:
   • Total: {total_cat}
   • Passed: {results['passed']}
   • Failed: {results['failed']}
   • Skipped: {results['skipped']}
   • Success Rate: {success_rate:.1f}%
"""
        
        # Passed Tests Summary
        if self.passed_tests:
            report += f"""

✅ PASSED TESTS ({len(self.passed_tests)})
{'─' * 30}
"""
            for test in self.passed_tests:
                test_name = test.nodeid.split("::")[-1]
                module_name = test.nodeid.split("::")[0].replace("test_", "").replace(".py", "")
                report += f"• {module_name}: {test_name}\n"
        
        # Failed Tests Summary
        if self.failed_tests:
            report += f"""

❌ FAILED TESTS ({len(self.failed_tests)})
{'─' * 30}
"""
            for test in self.failed_tests:
                test_name = test.nodeid.split("::")[-1]
                module_name = test.nodeid.split("::")[0].replace("test_", "").replace(".py", "")
                report += f"• {module_name}: {test_name}\n"
            
            report += """
📎 Detailed failure logs are attached to this email.
"""
        
        # Skipped Tests Summary
        if self.skipped_tests:
            report += f"""

⏭️ SKIPPED TESTS ({len(self.skipped_tests)})
{'─' * 30}
"""
            for test in self.skipped_tests:
                test_name = test.nodeid.split("::")[-1]
                module_name = test.nodeid.split("::")[0].replace("test_", "").replace(".py", "")
                report += f"• {module_name}: {test_name}\n"
        
        # Footer
        report += f"""
{'─' * 60}
Report generated on: {stats['timestamp']}
Test execution duration: {stats['duration']:.2f} seconds
"""
        
        return report.strip()
    
    def _validate_email_config(self) -> bool:
        """Validate email configuration."""
        required_fields = ['user', 'password', 'recipient', 'server']
        return all(self.smtp_config.get(field) for field in required_fields)
    
    def _write_failure_log(self, log_file: str):
        """Write detailed failure information to log file."""
        with open(log_file, "w") as f:
            f.write(f"Test Failure Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            for i, report in enumerate(self.failed_tests, 1):
                f.write(f"FAILURE #{i}\n")
                f.write("-" * 40 + "\n")
                f.write(f"Test: {report.nodeid}\n")
                f.write(f"Duration: {getattr(report, 'duration', 'N/A')}\n")
                f.write(f"Error Details:\n")
                f.write(f"{report.longreprtext}\n")
                f.write("-" * 80 + "\n\n")
    
    def _send_email(self, subject: str, body: str, attachment_path: str = None):
        """Send email with optional attachment."""
        try:
            message = MIMEMultipart()
            message["From"] = self.smtp_config['user']
            message["To"] = self.smtp_config['recipient']
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))
            
            if attachment_path and os.path.exists(attachment_path):
                self._attach_file(message, attachment_path)
            
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port']) as server:
                server.starttls(context=context)
                server.login(self.smtp_config['user'], self.smtp_config['password'])
                server.sendmail(
                    self.smtp_config['user'], 
                    self.smtp_config['recipient'], 
                    message.as_string()
                )
            
            print(f"Test report sent to {self.smtp_config['recipient']}")
        
        except Exception as e:
            print(f"Failed to send email: {e}")
    
    def _attach_file(self, message: MIMEMultipart, file_path: str):
        """Attach file to email message."""
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(file_path)}"
            )
            message.attach(part)
        
        except FileNotFoundError:
            print(f"Attachment file not found: {file_path}")


# Global test reporter
test_reporter = TestReporter()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture test results and collect all test outcomes."""
    outcome = yield
    report = outcome.get_result()
    
    # Add test result to reporter
    test_reporter.add_test_result(report)


def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    test_reporter.set_session_start()


def pytest_sessionfinish(session, exitstatus):
    """Called after the whole test session finishes."""
    test_reporter.set_session_end()
    test_reporter.send_test_report()
