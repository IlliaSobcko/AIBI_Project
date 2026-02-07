"""
Excel Analyzer Integration Examples
Demonstrates various ways to use the excel_analyzer module
"""

# Example 1: Simple standalone usage
def example_basic():
    """Simplest way to run analytics"""
    from features.excel_analyzer import run_analytics

    # Run with defaults (reports/ -> analytics_report.xlsx)
    run_analytics()


# Example 2: Custom output file
def example_custom_output():
    """Run analytics with custom output file"""
    from features.excel_analyzer import run_analytics
    from datetime import datetime

    output_file = f"analytics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    run_analytics(output_file=output_file)


# Example 3: Advanced with analyzer class
def example_advanced():
    """Use analyzer class directly for more control"""
    from features.excel_analyzer import ReportAnalyzer, create_excel_report

    # Initialize analyzer
    analyzer = ReportAnalyzer(reports_folder='reports')

    # Load reports
    analyzer.load_and_analyze_reports()

    # Get individual metrics
    stats = analyzer.get_summary_statistics()
    print(f"Total Deals: {stats['total_deals']}")
    print(f"Win Rate: {stats['win_rate']:.2f}%")
    print(f"Total Revenue: ${stats['total_revenue']:,.2f}")

    # Get top FAQs
    faqs = analyzer.get_top_faqs(5)
    for faq, count in faqs:
        print(f"  - {faq} ({count}x)")

    # Create Excel
    create_excel_report(analyzer, 'advanced_report.xlsx')


# Example 4: Scheduled analytics
def example_scheduled():
    """Run analytics on a schedule (requires APScheduler)"""
    from apscheduler.schedulers.background import BackgroundScheduler
    from features.excel_analyzer import run_analytics
    from datetime import datetime

    scheduler = BackgroundScheduler()

    def run_scheduled_analytics():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"analytics_{timestamp}.xlsx"
        run_analytics(output_file=output_file)
        print(f"[{timestamp}] Analytics completed: {output_file}")

    # Schedule daily at 6 AM
    scheduler.add_job(
        run_scheduled_analytics,
        'cron',
        hour=6,
        minute=0,
        id='daily_analytics'
    )

    scheduler.start()
    return scheduler


# Example 5: Flask integration
def example_flask():
    """Integration with Flask application"""
    from flask import Blueprint, jsonify, request
    from features.excel_analyzer import run_analytics
    import os

    analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')

    @analytics_bp.route('/run', methods=['POST'])
    def run_analysis():
        """Endpoint to trigger analysis"""
        try:
            success = run_analytics()
            return jsonify({
                'status': 'success' if success else 'failed',
                'file': 'analytics_report.xlsx'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @analytics_bp.route('/status', methods=['GET'])
    def check_status():
        """Check if report file exists"""
        exists = os.path.exists('analytics_report.xlsx')
        return jsonify({
            'report_exists': exists,
            'reports_folder_exists': os.path.exists('reports')
        })

    return analytics_bp


# Example 6: Custom report analyzer
def example_custom_analyzer():
    """Extend analyzer for custom report formats"""
    from features.excel_analyzer import ReportAnalyzer, create_excel_report
    import re

    class MyCustomAnalyzer(ReportAnalyzer):
        """Custom analyzer for company-specific report format"""

        def extract_client_name(self, text):
            """Extract from custom format: [CLIENT] Name"""
            match = re.search(r'\[CLIENT\]\s+(.+)', text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
            return super().extract_client_name(text)

        def extract_deal_status(self, text):
            """Extract from custom format: [STATUS] Win/Loss"""
            match = re.search(r'\[STATUS\]\s+(Win|Loss)', text, re.IGNORECASE)
            if match:
                return match.group(1).capitalize()
            return super().extract_deal_status(text)

    # Use custom analyzer
    analyzer = MyCustomAnalyzer(reports_folder='reports')
    analyzer.load_and_analyze_reports()
    create_excel_report(analyzer, 'custom_report.xlsx')


# Example 7: Error handling
def example_error_handling():
    """Proper error handling pattern"""
    from features.excel_analyzer import run_analytics
    import os

    try:
        # Run analytics
        success = run_analytics(
            reports_folder='reports',
            output_file='analytics_report.xlsx'
        )

        if success:
            # Verify file was created
            if os.path.exists('analytics_report.xlsx'):
                file_size = os.path.getsize('analytics_report.xlsx')
                print(f"Report created successfully ({file_size} bytes)")
            else:
                print("Report file not found after creation")
        else:
            print("Analytics failed")

    except Exception as e:
        print(f"Unexpected error: {e}")


# Example 8: Data export without Excel
def example_data_only():
    """Extract data without creating Excel file"""
    from features.excel_analyzer import ReportAnalyzer
    import json

    analyzer = ReportAnalyzer(reports_folder='reports')
    analyzer.load_and_analyze_reports()

    # Export as JSON
    data = {
        'deals': analyzer.data,
        'statistics': analyzer.get_summary_statistics(),
        'top_faqs': [
            {'faq': faq, 'count': count}
            for faq, count in analyzer.get_top_faqs(5)
        ]
    }

    with open('analytics_data.json', 'w') as f:
        json.dump(data, f, indent=2)

    print("Data exported to analytics_data.json")


# Example 9: Processing specific clients
def example_process_clients():
    """Filter and process data for specific clients"""
    from features.excel_analyzer import ReportAnalyzer

    analyzer = ReportAnalyzer(reports_folder='reports')
    analyzer.load_and_analyze_reports()

    # Get all clients
    clients = set(d['Client Name'] for d in analyzer.data)
    print(f"Total clients: {len(clients)}")

    # Get winning clients
    winning_clients = [
        d for d in analyzer.data
        if d['Deal Status'] == 'Win'
    ]
    print(f"Winning clients: {len(winning_clients)}")

    # Get top client by revenue
    top_client = max(
        (d for d in analyzer.data if d['Deal Status'] == 'Win'),
        key=lambda x: x['Revenue ($)'],
        default=None
    )

    if top_client:
        print(f"Top client: {top_client['Client Name']} (${top_client['Revenue ($)']:,.2f})")


# Example 10: Pipeline with validation
def example_validated_pipeline():
    """Run analytics with data validation"""
    from features.excel_analyzer import ReportAnalyzer, create_excel_report

    analyzer = ReportAnalyzer(reports_folder='reports')

    # Step 1: Load
    if not analyzer.load_and_analyze_reports():
        print("Failed to load reports")
        return False

    # Step 2: Validate
    stats = analyzer.get_summary_statistics()
    if stats['total_deals'] == 0:
        print("No deals found in reports")
        return False

    print(f"Validation passed: {stats['total_deals']} deals loaded")

    # Step 3: Generate report
    if not create_excel_report(analyzer, 'validated_report.xlsx'):
        print("Failed to create report")
        return False

    print("Pipeline completed successfully")
    return True


if __name__ == '__main__':
    print("Excel Analyzer Examples")
    print("=" * 50)
    print("\nAvailable examples:")
    print("  1. example_basic() - Simple usage")
    print("  2. example_custom_output() - Custom output file")
    print("  3. example_advanced() - Advanced analyzer usage")
    print("  4. example_scheduled() - Scheduled execution")
    print("  5. example_flask() - Flask integration")
    print("  6. example_custom_analyzer() - Custom report parser")
    print("  7. example_error_handling() - Error handling")
    print("  8. example_data_only() - Export data as JSON")
    print("  9. example_process_clients() - Filter and analyze clients")
    print(" 10. example_validated_pipeline() - Validated pipeline")
    print("\nRun any example: python -c 'from features.excel_analyzer_example import example_basic; example_basic()'")
