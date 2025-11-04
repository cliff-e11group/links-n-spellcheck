#!/usr/bin/env python3
"""
Regenerate HTML report from existing CSV files without re-running the scan.
"""

import csv
import os
from datetime import datetime
from collections import defaultdict


def read_spelling_errors(csv_path):
    """Read spelling errors from CSV file."""
    errors = []
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                errors.append(row)
    return errors


def read_broken_links(csv_path):
    """Read broken links from CSV file."""
    links = []
    if os.path.exists(csv_path):
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                links.append(row)
    return links


def generate_html_report(spelling_errors, broken_links, output_path):
    """Generate HTML report from data."""

    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Website Health Check Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .header { background: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
            .stats { display: flex; gap: 20px; margin-bottom: 20px; }
            .stat-box { background: #e9ecef; padding: 15px; border-radius: 5px; flex: 1; text-align: center; }

            /* Tab styles */
            .tabs { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 20px; }
            .tab { padding: 15px 25px; cursor: pointer; border: none; background: #f8f9fa; margin-right: 5px; border-radius: 5px 5px 0 0; }
            .tab.active { background: #007bff; color: white; }
            .tab:hover { background: #e9ecef; }
            .tab.active:hover { background: #0056b3; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }

            table { width: 100%; border-collapse: collapse; margin-top: 20px; table-layout: fixed; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; word-wrap: break-word; overflow-wrap: break-word; }
            th { background-color: #f2f2f2; }

            /* Column widths for spelling errors table */
            #errorsTable th:nth-child(1), #errorsTable td:nth-child(1) { width: 25%; }  /* URL */
            #errorsTable th:nth-child(2), #errorsTable td:nth-child(2) { width: 12%; }  /* Word */
            #errorsTable th:nth-child(3), #errorsTable td:nth-child(3) { width: 20%; }  /* Suggestions */
            #errorsTable th:nth-child(4), #errorsTable td:nth-child(4) { width: 35%; }  /* Context */
            #errorsTable th:nth-child(5), #errorsTable td:nth-child(5) { width: 8%; }   /* Confidence */

            /* Column widths for broken links table */
            #brokenLinksTable th:nth-child(1), #brokenLinksTable td:nth-child(1) { width: 30%; }  /* URL */
            #brokenLinksTable th:nth-child(2), #brokenLinksTable td:nth-child(2) { width: 12%; }  /* Type */
            #brokenLinksTable th:nth-child(3), #brokenLinksTable td:nth-child(3) { width: 10%; }  /* Status */
            #brokenLinksTable th:nth-child(4), #brokenLinksTable td:nth-child(4) { width: 18%; }  /* Error */
            #brokenLinksTable th:nth-child(5), #brokenLinksTable td:nth-child(5) { width: 30%; }  /* Found On */

            .error-word { color: #d32f2f; font-weight: bold; }
            .suggestions { color: #388e3c; }
            .context { font-style: italic; color: #666; }
            .url-link { color: #1976d2; text-decoration: none; word-break: break-all; }
            .url-link:hover { text-decoration: underline; }
            .status-404 { color: #dc3545; font-weight: bold; }
            .status-500 { color: #fd7e14; font-weight: bold; }
            .broken-link-count { background: #dc3545; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
            .spell-error-count { background: #d32f2f; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Website Health Check Report</h1>
            <p>Generated on: {timestamp}</p>
            <p>Regenerated from CSV data</p>
        </div>

        {stats_section}

        {tabs_section}

        {spelling_content}

        {broken_links_content}

        <script>
            function showTab(tabName) {
                // Hide all tab contents
                const contents = document.querySelectorAll('.tab-content');
                contents.forEach(content => content.classList.remove('active'));

                // Remove active class from all tabs
                const tabs = document.querySelectorAll('.tab');
                tabs.forEach(tab => tab.classList.remove('active'));

                // Show selected tab content
                document.getElementById(tabName).classList.add('active');

                // Add active class to clicked tab
                event.target.classList.add('active');
            }
        </script>
    </body>
    </html>
    """

    # Count unique pages
    pages_with_spelling = len(set([e['url'] for e in spelling_errors])) if spelling_errors else 0
    pages_with_links = len(set([l['found_on'] for l in broken_links])) if broken_links else 0
    total_pages = max(pages_with_spelling, pages_with_links)

    # Build stats section
    stats_html = '<div class="stats">'
    stats_html += f'''
            <div class="stat-box">
                <h3>{total_pages}</h3>
                <p>Pages in Report</p>
            </div>'''

    if spelling_errors is not None:
        stats_html += f'''
            <div class="stat-box">
                <h3>{len(spelling_errors)}</h3>
                <p>Spelling Errors</p>
            </div>'''

    if broken_links is not None:
        stats_html += f'''
            <div class="stat-box">
                <h3>{len(broken_links)}</h3>
                <p>Broken Links</p>
            </div>'''

    stats_html += '</div>'

    # Build tabs section
    has_spelling = spelling_errors is not None and len(spelling_errors) > 0
    has_links = broken_links is not None and len(broken_links) > 0

    tabs_html = '<div class="tabs">'
    if spelling_errors is not None:
        tabs_html += f'''
            <button class="tab active" onclick="showTab('spelling')">
                📝 Spelling Errors <span class="spell-error-count">{len(spelling_errors)}</span>
            </button>'''
    if broken_links is not None:
        active_class = "" if spelling_errors is not None else "active"
        tabs_html += f'''
            <button class="tab {active_class}" onclick="showTab('broken-links')">
                🔗 Broken Links <span class="broken-link-count">{len(broken_links)}</span>
            </button>'''
    tabs_html += '</div>'

    # Build spelling errors rows
    error_rows = ""
    if spelling_errors:
        import html
        for error in spelling_errors:
            url_escaped = html.escape(error['url'])
            word_escaped = html.escape(error['word'])
            suggestions_escaped = html.escape(error['suggestions'])
            context_escaped = html.escape(error['context'][:100])

            error_rows += f"""
                <tr>
                    <td><a href="{url_escaped}" class="url-link" target="_blank">{url_escaped}</a></td>
                    <td class="error-word">{word_escaped}</td>
                    <td class="suggestions">{suggestions_escaped}</td>
                    <td class="context">{context_escaped}...</td>
                    <td>{error['confidence']}</td>
                </tr>
            """

    # Build spelling content section
    spelling_content = ""
    if spelling_errors is not None:
        no_spelling_errors = "<p style='color: #28a745; font-style: italic;'>🎉 No spelling errors found! Your content looks great.</p>" if not spelling_errors else ""
        spelling_content = f'''
        <div id="spelling" class="tab-content active">
            <h2>Spelling Errors</h2>
            <p>Words that may be misspelled or need to be added to your custom dictionary.</p>
            <table id="errorsTable">
                <thead>
                    <tr>
                        <th>URL</th>
                        <th>Word</th>
                        <th>Suggestions</th>
                        <th>Context</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
                    {error_rows}
                </tbody>
            </table>
            {no_spelling_errors}
        </div>'''

    # Build broken links rows
    broken_link_rows = ""
    if broken_links:
        import html
        for broken_link in broken_links:
            url_escaped = html.escape(broken_link['url'])
            reason_escaped = html.escape(broken_link['reason'])
            found_on_escaped = html.escape(broken_link.get('found_on', 'Unknown'))
            link_type = broken_link.get('link_type', 'unknown')
            resource_type = broken_link.get('resource_type', 'hyperlink')
            status_code = broken_link['status_code']
            status_class = f"status-{status_code}" if status_code in ['404', '500'] else ""

            # Add visual indicators
            link_type_icon = "🔗" if link_type == "external" else "🏠"
            resource_icons = {
                'image': '🖼️',
                'document': '📄',
                'css': '🎨',
                'javascript': '⚡',
                'media': '🎵',
                'hyperlink': '🔗'
            }
            resource_icon = resource_icons.get(resource_type, '🔗')

            broken_link_rows += f"""
                <tr>
                    <td><a href="{url_escaped}" class="url-link" target="_blank">{link_type_icon} {url_escaped}</a></td>
                    <td>{resource_icon} {resource_type.title()}</td>
                    <td class="{status_class}">{status_code}</td>
                    <td>{reason_escaped}</td>
                    <td><a href="{html.escape(found_on_escaped)}" class="url-link" target="_blank">{found_on_escaped}</a></td>
                </tr>
            """

    # Build broken links content section
    broken_links_content = ""
    if broken_links is not None:
        no_broken_links = "<p style='color: #28a745; font-style: italic;'>🎉 No broken links found! All pages are accessible.</p>" if not broken_links else ""
        active_class = "" if spelling_errors is not None else "active"
        broken_links_content = f'''
        <div id="broken-links" class="tab-content {active_class}">
            <h2>Broken Links</h2>
            <p>Pages that returned HTTP error codes and need attention.</p>
            <table id="brokenLinksTable">
                <thead>
                    <tr>
                        <th>URL</th>
                        <th>Type</th>
                        <th>Status Code</th>
                        <th>Error</th>
                        <th>Found On</th>
                    </tr>
                </thead>
                <tbody>
                    {broken_link_rows}
                </tbody>
            </table>
            {no_broken_links}
        </div>'''

    # Replace placeholders
    html_content = template.replace('{timestamp}', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    html_content = html_content.replace('{stats_section}', stats_html)
    html_content = html_content.replace('{tabs_section}', tabs_html)
    html_content = html_content.replace('{spelling_content}', spelling_content)
    html_content = html_content.replace('{broken_links_content}', broken_links_content)

    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ HTML report regenerated: {output_path}")


def main():
    """Main function."""
    reports_dir = "reports"

    spelling_csv = os.path.join(reports_dir, "spelling_errors.csv")
    broken_links_csv = os.path.join(reports_dir, "broken_links.csv")
    output_html = os.path.join(reports_dir, "spell_check_report.html")

    # Check if at least one CSV exists
    if not os.path.exists(spelling_csv) and not os.path.exists(broken_links_csv):
        print("❌ Error: No CSV files found in reports/ directory")
        print("   Run the spell checker first to generate data files")
        return

    # Read data
    print("Reading CSV files...")
    spelling_errors = read_spelling_errors(spelling_csv) if os.path.exists(spelling_csv) else None
    broken_links = read_broken_links(broken_links_csv) if os.path.exists(broken_links_csv) else None

    if spelling_errors is not None:
        print(f"  Found {len(spelling_errors)} spelling errors")
    if broken_links is not None:
        print(f"  Found {len(broken_links)} broken links")

    # Generate report
    print("Generating HTML report...")
    generate_html_report(spelling_errors, broken_links, output_html)

    print("\n" + "="*50)
    print(f"Report regenerated successfully!")
    print(f"Open: {output_html}")
    print("="*50)


if __name__ == "__main__":
    main()
