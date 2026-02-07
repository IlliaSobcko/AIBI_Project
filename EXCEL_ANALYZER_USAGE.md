# Excel Analyzer Module - Complete Usage Guide

## Overview

The `features/excel_analyzer.py` module is a **completely independent** analytics tool that:
- Analyzes text reports from the `reports/` folder
- Extracts key business metrics: Client Name, Deal Status (Win/Loss), Revenue
- Identifies Top 5 FAQs that led to successful deals
- Generates professional Excel reports with multiple sheets

## Key Features

✅ **Standalone Design** - No dependencies on `main.py` or other project modules
✅ **Flexible Report Parsing** - Handles various text report formats
✅ **Dual Engine Support** - Works with pandas or openpyxl (or both)
✅ **Rich Excel Output** - Multiple sheets with formatting and statistics
✅ **Easy Integration** - Simple `run_analytics()` function to trigger analysis

## Installation

Ensure dependencies are installed:

```bash
pip install -r requirements.txt
```

Required packages:
- `pandas` - Data manipulation and Excel writing
- `openpyxl` - Advanced Excel formatting

## Quick Start

### Method 1: Direct Function Call (Recommended)

```python
from features.excel_analyzer import run_analytics

# Run with default settings
run_analytics()

# Or specify custom paths
run_analytics(
    reports_folder='reports',
    output_file='my_analytics_report.xlsx'
)
```

### Method 2: Command Line

```bash
# From project root
python -m features.excel_analyzer

# Or directly
python features/excel_analyzer.py
```

### Method 3: Import Individual Classes

```python
from features.excel_analyzer import ReportAnalyzer, create_excel_report

# Create analyzer
analyzer = ReportAnalyzer(reports_folder='reports')

# Load reports
analyzer.load_and_analyze_reports()

# Get statistics
stats = analyzer.get_summary_statistics()
print(f"Win Rate: {stats['win_rate']:.2f}%")

# Get top FAQs
top_faqs = analyzer.get_top_faqs(5)
for faq, count in top_faqs:
    print(f"FAQ: {faq} ({count} occurrences)")

# Create Excel
create_excel_report(analyzer, 'output.xlsx')
```

## Report Format

The module is flexible and extracts data from various text report patterns:

### Supported Formats

Your text reports can use various formats. The analyzer looks for these patterns:

**Client Name:**
```
Client: TechCorp Solutions
Company: TechCorp Solutions Inc
Customer Name: TechCorp
```

**Deal Status:**
```
Status: Win
Deal Status: Loss
Result: Success
```

**Revenue:**
```
Revenue: $125,500
Amount: $87,300
Deal Value: $50,000
```

**FAQs:**
```
FAQ 1: What are the system requirements?
Q2: How does licensing work?
Common Questions: Can we customize?
```

### Example Report

```
TechCorp Solutions
Client: TechCorp Solutions
Status: Win
Revenue: $125,500

Summary: Enterprise software licensing deal

FAQ References:
FAQ 1: What are the system requirements?
FAQ 2: How does licensing work?
FAQ 3: What support options are included?
```

## Output

The module generates an Excel file with 3 sheets:

### Sheet 1: "Deals"
Contains all analyzed deals with columns:
- Client Name
- Deal Status (Win/Loss)
- Revenue ($)
- Report File (source filename)

### Sheet 2: "Summary"
Business metrics:
- Total Deals
- Wins
- Losses
- Win Rate (%)
- Total Revenue ($)
- Average Deal Value ($)

### Sheet 3: "Top FAQs"
Top 5 FAQs from winning deals:
- FAQ (text)
- Occurrences in Wins (count)

## API Reference

### `run_analytics(reports_folder='reports', output_file='analytics_report.xlsx')`

Main entry point for the analytics pipeline.

**Parameters:**
- `reports_folder` (str): Path to folder with text reports
- `output_file` (str): Output Excel file path

**Returns:**
- `bool`: True if successful, False otherwise

**Example:**
```python
success = run_analytics(reports_folder='reports', output_file='analysis.xlsx')
if success:
    print("Analytics completed successfully!")
```

---

### `class ReportAnalyzer`

Core analyzer class for processing reports.

#### Methods

**`__init__(reports_folder='reports')`**
Initialize analyzer with reports folder path.

**`load_and_analyze_reports()`**
Load all .txt, .md, .text files from reports folder.
Returns: bool

**`extract_client_name(text)`**
Extract client name from text.
Returns: str or None

**`extract_deal_status(text)`**
Extract deal status (Win/Loss/Unknown).
Returns: str

**`extract_revenue(text)`**
Extract revenue amount from text.
Returns: float

**`extract_faqs(text)`**
Extract FAQ references from text.
Returns: List[str]

**`get_summary_statistics()`**
Calculate summary metrics.
Returns: Dict with keys: total_deals, wins, losses, win_rate, total_revenue, average_deal_value

**`get_top_faqs(top_n=5)`**
Get most frequent FAQs from winning deals.
Returns: List[Tuple[str, int]]

---

### `create_excel_report(analyzer, output_path)`

Create Excel file from analyzed data.

**Parameters:**
- `analyzer` (ReportAnalyzer): Analyzer with loaded data
- `output_path` (str): Output file path

**Returns:**
- `bool`: True if successful, False otherwise

## Advanced Usage

### Custom Report Parsing

If your reports have a custom format, extend the `ReportAnalyzer` class:

```python
from features.excel_analyzer import ReportAnalyzer

class CustomReportAnalyzer(ReportAnalyzer):
    def extract_client_name(self, text):
        # Your custom logic
        import re
        match = re.search(r'MY_PATTERN: (.+)', text)
        return match.group(1) if match else "Unknown"

analyzer = CustomReportAnalyzer(reports_folder='reports')
analyzer.load_and_analyze_reports()
```

### Integration with Scheduling

Schedule analytics to run periodically:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from features.excel_analyzer import run_analytics

scheduler = BackgroundScheduler()

def scheduled_analytics():
    run_analytics(
        reports_folder='reports',
        output_file=f'analytics_{datetime.now().date()}.xlsx'
    )

scheduler.add_job(scheduled_analytics, 'cron', hour=0, minute=0)  # Daily at midnight
scheduler.start()
```

### Integration with Flask

Trigger analytics from a Flask endpoint:

```python
from flask import Flask, jsonify
from features.excel_analyzer import run_analytics

app = Flask(__name__)

@app.route('/api/analytics/run', methods=['POST'])
def trigger_analytics():
    try:
        success = run_analytics()
        return jsonify({'status': 'success' if success else 'failed'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
```

## Testing

Run the module with sample data:

```bash
# Sample reports are in reports/ folder
python -m features.excel_analyzer

# This generates analytics_report.xlsx
```

## Troubleshooting

### Issue: "No report files found"
- Ensure report files are in the `reports/` folder
- Check file extensions: `.txt`, `.md`, `.text` are supported
- Verify the path is correct

### Issue: "Neither pandas nor openpyxl is installed"
```bash
pip install pandas openpyxl
```

### Issue: Empty Summary/Top FAQs sheets
- Ensure your reports contain deal status information (Win/Loss)
- For FAQs sheet, winning deals must contain FAQ references
- Check report format matches expected patterns

### Issue: Revenue extracted as 0.0
- Reports must contain currency amounts with $ symbol or explicit "Revenue:" prefix
- Examples: `$125,500` or `Revenue: 125500`

## Report Format Best Practices

For best results, use this structure in your reports:

```
[Client Name]
Client: CompanyName

[Deal Status]
Status: Win

[Revenue]
Revenue: $100,000

[FAQ References]
FAQ 1: Question about feature X
FAQ 2: Question about feature Y
```

## Performance Notes

- Processes text files sequentially
- Memory efficient for large reports
- Excel generation optimized with openpyxl
- Typical run time: < 1 second for 100 reports

## Independence Notes

This module is completely independent:
- ✅ No imports from `main.py`
- ✅ No imports from other project modules
- ✅ Can run in separate process/thread
- ✅ No shared state dependencies
- ✅ Safe for concurrent execution

## License & Attribution

Part of AIBI Project - Standalone Analytics Module
