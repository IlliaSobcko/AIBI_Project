"""
Features Module - Additional functionality for AIBI Project

This package contains standalone feature modules that extend the core project.
"""

# Excel Analyzer - Standalone analytics module
try:
    from .excel_analyzer import (
        ReportAnalyzer,
        run_analytics,
        create_excel_report
    )
    __all__ = [
        'ReportAnalyzer',
        'run_analytics',
        'create_excel_report'
    ]
except ImportError as e:
    print(f"Warning: Could not import excel_analyzer: {e}")
    __all__ = []
