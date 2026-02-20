"""
Compliance report generator — produces accessible HTML reports.
"""

from typing import Optional
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from ..utils.constants import APP_NAME, APP_VERSION, COLORS, WCAG_CRITERIA
from ..core.wcag_validator import ValidationResult, IssueSeverity
from ..core.audit_logger import AuditLogger
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ComplianceReportGenerator:
    """Generates accessible HTML compliance reports."""

    def __init__(
        self,
        document_name: str,
        result: ValidationResult,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """
        Initialize the report generator.

        Args:
            document_name: Name of the document being reported on
            result: Validation result to report
            audit_logger: Optional audit logger for change history
        """
        self._document_name = document_name
        self._result = result
        self._audit_logger = audit_logger

    def generate_report(self, output_path: Path) -> bool:
        """
        Generate and save an HTML compliance report.

        Args:
            output_path: Path to save the HTML report

        Returns:
            True if successful
        """
        try:
            html = self._generate_html()
            output_path.write_text(html, encoding="utf-8")
            logger.info(f"Compliance report saved to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to generate compliance report: {e}")
            return False

    def _generate_html(self) -> str:
        """Build the accessible HTML report."""
        result = self._result
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "Compliant" if result.is_compliant else "Non-Compliant"
        status_color = COLORS.SUCCESS if result.is_compliant else COLORS.ERROR

        # Group issues by criterion
        issues_by_criterion = defaultdict(list)
        for issue in result.issues:
            issues_by_criterion[issue.criterion].append(issue)

        # Build issues section
        issues_html = ""
        if result.issues:
            for criterion, issues in sorted(issues_by_criterion.items()):
                info = WCAG_CRITERIA.get(criterion, {})
                name = info.get("name", criterion)
                level = info.get("level")
                level_str = level.value if level else "?"
                issues_html += f'<h3>[{criterion}] {name} (Level {level_str})</h3>\n<ul>\n'
                for issue in issues:
                    sev = issue.severity.value.upper()
                    badge_color = {
                        "ERROR": COLORS.ERROR,
                        "WARNING": COLORS.WARNING,
                        "INFO": COLORS.INFO,
                    }.get(sev, COLORS.INFO)
                    page_str = f" (Page {issue.page})" if issue.page else ""
                    issues_html += (
                        f'<li><span style="color:{badge_color};font-weight:bold;">{sev}</span> '
                        f'{issue.message}{page_str}</li>\n'
                    )
                issues_html += '</ul>\n'
        else:
            issues_html = '<p style="color:' + COLORS.SUCCESS + ';">No issues found.</p>'

        # Build actions section
        actions_html = ""
        if self._audit_logger:
            summary = self._audit_logger.get_log_summary()
            if summary["total_changes"] > 0:
                actions_html = f'<p>{summary["total_changes"]} changes recorded:</p>\n<ul>\n'
                for action in summary["actions"][:50]:
                    criterion_str = f' [{action["criterion"]}]' if action["criterion"] else ""
                    page_str = f' (Page {action["page"]})' if action["page"] else ""
                    actions_html += (
                        f'<li><strong>{action["action"]}</strong>{criterion_str}{page_str}'
                    )
                    if action["original_value"] and action["new_value"]:
                        actions_html += (
                            f' — changed from "{action["original_value"][:60]}" '
                            f'to "{action["new_value"][:60]}"'
                        )
                    actions_html += '</li>\n'
                actions_html += '</ul>\n'
            else:
                actions_html = '<p>No changes recorded in this session.</p>'
        else:
            actions_html = '<p>Audit logging was not active for this session.</p>'

        # Build remaining items
        remaining = [i for i in result.issues if i.severity == IssueSeverity.ERROR]
        if remaining:
            remaining_html = f'<p>{len(remaining)} error(s) still need resolution:</p>\n<ul>\n'
            for issue in remaining:
                remaining_html += f'<li>[{issue.criterion}] {issue.message}</li>\n'
            remaining_html += '</ul>\n'
        else:
            remaining_html = '<p style="color:' + COLORS.SUCCESS + ';">All errors resolved.</p>'

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compliance Report — {self._document_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: {COLORS.BACKGROUND};
            color: {COLORS.TEXT_PRIMARY};
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            line-height: 1.6;
        }}
        h1 {{ color: {COLORS.PRIMARY_LIGHT}; border-bottom: 2px solid {COLORS.BORDER}; padding-bottom: 8px; }}
        h2 {{ color: {COLORS.TEXT_PRIMARY}; margin-top: 32px; }}
        h3 {{ color: {COLORS.TEXT_SECONDARY}; }}
        .score-box {{
            display: inline-block;
            font-size: 48px;
            font-weight: bold;
            color: {status_color};
            border: 3px solid {status_color};
            border-radius: 12px;
            padding: 16px 32px;
            margin: 16px 0;
        }}
        .status {{ font-size: 20px; font-weight: bold; color: {status_color}; }}
        ul {{ padding-left: 24px; }}
        li {{ margin-bottom: 6px; }}
        .footer {{ margin-top: 48px; padding-top: 16px; border-top: 1px solid {COLORS.BORDER}; color: {COLORS.TEXT_DISABLED}; font-size: 14px; }}
    </style>
</head>
<body>
    <h1>WCAG Compliance Report</h1>
    <p><strong>Document:</strong> {self._document_name}</p>
    <p><strong>Date:</strong> {timestamp}</p>
    <p><strong>Target Level:</strong> WCAG {result.level.value}</p>

    <h2>Executive Summary</h2>
    <div class="score-box">{result.score:.0f}%</div>
    <p class="status">{status}</p>
    <p>Errors: {result.summary.get("errors", 0)} | Warnings: {result.summary.get("warnings", 0)} | Info: {result.summary.get("info", 0)}</p>

    <h2>Issues Found</h2>
    {issues_html}

    <h2>Actions Taken</h2>
    {actions_html}

    <h2>Remaining Items</h2>
    {remaining_html}

    <div class="footer">
        <p>Generated by {APP_NAME} v{APP_VERSION} on {timestamp}</p>
    </div>
</body>
</html>"""
