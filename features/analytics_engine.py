"""
Unified Analytics Engine
Analyzes BOTH Format A (Ukrainian AI reports) and Format B (English business reports).
Extends features.excel_analyzer.py for unified analytics.
MODULAR: No imports from main.py or core modules.
"""

import asyncio
import re
from pathlib import Path
from typing import Optional, Dict, List
from collections import Counter
from datetime import datetime

try:
    from features.excel_analyzer import ReportAnalyzer, create_excel_report
    EXCEL_ANALYZER_AVAILABLE = True
except ImportError:
    EXCEL_ANALYZER_AVAILABLE = False
    print("[WARNING] excel_analyzer not available")


class UnifiedReportAnalyzer(ReportAnalyzer):
    """
    Extended analyzer supporting BOTH:
    - Format A: Ukrainian AI chat analysis (ЗВІТ ПО ЧАТУ)
    - Format B: English business reports (Client/Status/Revenue)
    """

    def __init__(self, reports_folder: str = "reports"):
        """Initialize analyzer with unified support."""
        super().__init__(reports_folder=reports_folder)
        self.format_stats = {
            "format_a": 0,
            "format_b": 0,
            "unknown": 0
        }

    def detect_report_format(self, text: str) -> str:
        """
        Detect report format from content.

        Returns: 'format_a', 'format_b', or 'unknown'
        """
        if "ЗВІТ ПО ЧАТУ:" in text or "ВПЕВНЕНІСТЬ ШІ:" in text:
            return "format_a"
        elif "Deal Status:" in text or "Client:" in text or "Revenue:" in text:
            return "format_b"
        return "unknown"

    def extract_client_name(self, text: str) -> Optional[str]:
        """
        Enhanced extraction supporting both formats.

        Format A: Extract from "ЗВІТ ПО ЧАТУ: [Name]"
        Format B: Use existing parent logic (Client:/Company:/etc)
        """
        format_type = self.detect_report_format(text)

        if format_type == "format_a":
            # Ukrainian format: "ЗВІТ ПО ЧАТУ: Chat Name"
            match = re.search(r'ЗВІТ ПО ЧАТУ:\s*(.+?)(?:\n|$)', text)
            if match:
                name = match.group(1).strip()
                return name if name else "Unknown"
            return "Unknown"
        else:
            # Use parent class logic for Format B
            return super().extract_client_name(text)

    def extract_deal_status(self, text: str) -> str:
        """
        Enhanced extraction supporting both formats.

        Format A: Infer from AUTO-REPLY SENT, DRAFT FOR REVIEW, confidence
        Format B: Use existing parent logic (Status: Win/Loss)
        """
        format_type = self.detect_report_format(text)

        if format_type == "format_a":
            # Format A: Ukrainian AI report
            # Rules:
            # - If "AUTO-REPLY SENT" + high confidence (>=80%) = Win
            # - If "DRAFT FOR REVIEW" = Unknown (needs manual review)
            # - If mentions rejection/failure = Loss

            if "AUTO-REPLY SENT" in text:
                confidence = self._extract_confidence_from_format_a(text)
                if confidence >= 80:
                    return "Win"
                else:
                    return "Unknown"

            if "DRAFT FOR REVIEW" in text:
                return "Unknown"

            # Check for failure/rejection indicators
            failure_patterns = [
                r'(?:відхилено|відхилена|відхилили)',
                r'(?:не відповідає|не підходит)',
                r'(?:скасовано|скасована)',
                r'(?:втрачено|втратили|втрачена)'
            ]
            text_lower = text.lower()
            for pattern in failure_patterns:
                if re.search(pattern, text_lower):
                    return "Loss"

            return "Unknown"
        else:
            # Use parent class logic for Format B
            return super().extract_deal_status(text)

    def extract_revenue(self, text: str) -> float:
        """
        Enhanced extraction with Ukrainian currency support.

        Format A: Extract from "💰 **ГРОШІ ТА УГОДИ:**" section
        Format B: Use existing parent logic
        """
        format_type = self.detect_report_format(text)

        if format_type == "format_a":
            # Look for currency patterns in Ukrainian reports
            # Patterns: $100, 100$, 100 грн, 100₴, 100 USD, 100 UAH
            patterns = [
                r'[\$][\s]*([0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{2})?)',
                r'([0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{2})?)\s*(?:грн|₴|USD|UAH)',
                r'💰.*?([0-9]{1,3}(?:[,\s][0-9]{3})*(?:\.[0-9]{2})?)'
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    amount_str = match.group(1).replace(' ', '').replace(',', '')
                    try:
                        return float(amount_str)
                    except ValueError:
                        pass

            return 0.0
        else:
            # Use parent class logic for Format B
            return super().extract_revenue(text)

    def extract_faqs(self, text: str) -> List[str]:
        """
        Enhanced extraction with Ukrainian patterns.

        Format A: Extract from analysis sections (питання, запитання)
        Format B: Use existing parent logic (FAQ 1: , Q2: , etc)
        """
        format_type = self.detect_report_format(text)
        faqs = []

        if format_type == "format_a":
            # Ukrainian patterns
            patterns = [
                r'(?:питання|запитання|вопрос)[\s:]*([^\n]+)',
                r'клієнт.*?(?:питає|запитує|спитав)[\s:]*([^\n]+)',
                r'(?:закрита|закрыта)[\s:]*([^\n]+)',
                r'(?:обговорювалась|обсуждалась)[\s:]*([^\n]+)'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                faqs.extend([m.strip() for m in matches if m.strip() and len(m.strip()) > 10])

            # Remove duplicates while preserving order
            seen = set()
            unique_faqs = []
            for faq in faqs:
                if faq not in seen:
                    seen.add(faq)
                    unique_faqs.append(faq)
            return unique_faqs
        else:
            # Use parent class logic for Format B
            return super().extract_faqs(text)

    def _extract_confidence_from_format_a(self, text: str) -> int:
        """Extract AI confidence percentage from Format A reports."""
        match = re.search(r'ВПЕВНЕНІСТЬ ШІ:\s*(\d+)\s*%?', text)
        try:
            return int(match.group(1)) if match else 0
        except ValueError:
            return 0

    def load_and_analyze_reports(self) -> bool:
        """
        Override parent method to track format statistics.
        Calls parent implementation and tracks formats.
        """
        if not self.reports_folder.exists():
            print(f"[WARNING] Reports folder not found: {self.reports_folder}")
            return False

        report_files = (
            list(self.reports_folder.glob('*.txt')) +
            list(self.reports_folder.glob('*.md')) +
            list(self.reports_folder.glob('*.text'))
        )

        if not report_files:
            print("[INFO] No report files found")
            return True

        print(f"[ANALYTICS] Analyzing {len(report_files)} reports...")

        for report_file in report_files:
            try:
                text = report_file.read_text(encoding='utf-8', errors='ignore')
                format_type = self.detect_report_format(text)
                self.format_stats[format_type] += 1

                # Extract data (same as parent)
                client_name = self.extract_client_name(text)
                deal_status = self.extract_deal_status(text)
                revenue = self.extract_revenue(text)
                faqs = self.extract_faqs(text)

                # Store data
                self.data.append({
                    'Client Name': client_name,
                    'Deal Status': deal_status,
                    'Revenue ($)': revenue,
                    'Report File': report_file.name,
                    'Format': format_type
                })

                # Track FAQs from winning deals only
                if deal_status == "Win" and faqs:
                    for faq in faqs:
                        self.faqs_data.append({
                            'FAQ': faq,
                            'Client': client_name,
                            'Revenue': revenue,
                            'Format': format_type
                        })

                print(f"[OK] {report_file.name} ({format_type}): {client_name} - {deal_status}")

            except Exception as e:
                print(f"[ERROR] {report_file.name}: {e}")

        print(f"[ANALYTICS] Format breakdown: A={self.format_stats['format_a']}, "
              f"B={self.format_stats['format_b']}, Unknown={self.format_stats['unknown']}")
        return True

    def analyze_winning_patterns(self) -> Dict:
        """
        Identify patterns in winning deals vs lost deals.

        Returns:
            {
                "total_wins": int,
                "total_losses": int,
                "total_unknown": int,
                "win_rate": float (%),
                "avg_win_revenue": float,
                "top_winning_faqs": [(faq, count), ...],
                "format_breakdown": {a_wins, a_losses, b_wins, b_losses},
                "customer_count": int
            }
        """
        wins = [d for d in self.data if d['Deal Status'] == 'Win']
        losses = [d for d in self.data if d['Deal Status'] == 'Loss']
        unknowns = [d for d in self.data if d['Deal Status'] == 'Unknown']

        # Count by format
        format_breakdown = {
            'format_a_wins': len([d for d in wins if d.get('Format') == 'format_a']),
            'format_a_losses': len([d for d in losses if d.get('Format') == 'format_a']),
            'format_b_wins': len([d for d in wins if d.get('Format') == 'format_b']),
            'format_b_losses': len([d for d in losses if d.get('Format') == 'format_b']),
        }

        # FAQ frequency from winning deals
        winning_faqs = [faq['FAQ'] for faq in self.faqs_data if faq['FAQ']]
        faq_counter = Counter(winning_faqs)
        top_faqs = faq_counter.most_common(10)

        # Revenue calculations
        total_revenue = sum(d['Revenue ($)'] for d in wins)
        avg_win_revenue = total_revenue / len(wins) if wins else 0.0

        # Unique customers
        unique_customers = len(set(d['Client Name'] for d in self.data))

        return {
            "total_wins": len(wins),
            "total_losses": len(losses),
            "total_unknown": len(unknowns),
            "total_deals": len(self.data),
            "win_rate": (len(wins) / len(self.data) * 100) if self.data else 0.0,
            "avg_win_revenue": avg_win_revenue,
            "total_revenue": total_revenue,
            "top_winning_faqs": top_faqs,
            "format_breakdown": format_breakdown,
            "customer_count": unique_customers
        }


async def run_unified_analytics(
    reports_folder: str = "reports",
    output_file: str = "unified_analytics.xlsx"
) -> Dict:
    """
    Main entry point for unified analytics engine.

    Analyzes ALL reports (Format A + B) and generates Excel report.

    Args:
        reports_folder: Path to reports directory
        output_file: Output Excel filename

    Returns:
        {
            "success": bool,
            "file_path": str or None,
            "summary": dict with statistics,
            "message": str
        }
    """
    if not EXCEL_ANALYZER_AVAILABLE:
        return {
            "success": False,
            "file_path": None,
            "message": "excel_analyzer module not available",
            "summary": {}
        }

    try:
        print(f"[ANALYTICS] Starting unified analysis: {reports_folder}")

        # Initialize analyzer
        analyzer = UnifiedReportAnalyzer(reports_folder=reports_folder)

        # Load and analyze all reports (async)
        await asyncio.to_thread(analyzer.load_and_analyze_reports)

        # Get statistics
        stats = analyzer.get_summary_statistics()
        patterns = analyzer.analyze_winning_patterns()

        # Merge statistics
        summary = {**stats, **patterns}

        # Generate Excel (async)
        success = await asyncio.to_thread(
            create_excel_report,
            analyzer,
            output_file
        )

        if success:
            return {
                "success": True,
                "file_path": output_file,
                "summary": summary,
                "message": f"Analytics complete: {output_file}"
            }
        else:
            return {
                "success": False,
                "file_path": None,
                "summary": summary,
                "message": "Failed to create Excel file"
            }

    except Exception as e:
        print(f"[ERROR] Analytics failed: {e}")
        return {
            "success": False,
            "file_path": None,
            "summary": {},
            "message": f"Analytics error: {type(e).__name__}: {str(e)}"
        }


def get_analytics_summary() -> Dict:
    """
    Quick analytics without full Excel generation.
    Useful for Telegram reports and quick checks.

    Returns:
        Summary dict with key metrics
    """
    try:
        analyzer = UnifiedReportAnalyzer()
        analyzer.load_and_analyze_reports()

        stats = analyzer.get_summary_statistics()
        patterns = analyzer.analyze_winning_patterns()

        return {**stats, **patterns}
    except Exception as e:
        print(f"[ERROR] Summary generation failed: {e}")
        return {}
