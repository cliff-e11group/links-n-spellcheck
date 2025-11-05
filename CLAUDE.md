# Website Spell Checker - Development Log

## Project Overview
Built a comprehensive Python-based website health checker. The tool performs both spell checking and broken link detection, generating interactive reports for easy website maintenance. Originally designed for genealogy websites, the tool has been refactored to be a generic solution suitable for any type of website.

## Key Features Implemented
- **Smart Website Crawling**: Sitemap.xml discovery with recursive crawling fallback
- **Spell Checking Engine**: Uses pyspellchecker with custom dictionaries
- **Broken Link Detection**: Tracks HTTP errors (404, 500, etc.) during crawling
- **Custom Dictionaries**: Support for domain-specific terms, proper nouns, and locations
- **Interactive Reports**: Tabbed HTML interface showing both spelling errors and broken links
- **CSV Exports**: Separate data files for analysis and bulk processing
- **Performance Optimized**: Concurrent processing with configurable threading
- **Optional Features**: Toggle spell checking and link checking independently

## Development History

### Initial Planning & Architecture
1. **Research Phase**: Analyzed Python libraries for web scraping, text extraction, and spell checking
   - **Web Scraping**: Chose requests + BeautifulSoup for reliability and ease of use
   - **Spell Checking**: Selected pyspellchecker for performance and custom dictionary support
   - **Text Extraction**: Used html2text for clean content extraction

2. **Architecture Design**: Modular design with separate components for crawling, text extraction, and spell checking
   - Hybrid crawling strategy (sitemap.xml → recursive fallback)
   - Context-aware error reporting with surrounding text
   - Configurable everything via YAML

### Implementation Phases

#### Phase 1: Project Setup
- Created project structure with configuration files
- Set up dependencies: requests, beautifulsoup4, pyspellchecker, html2text, lxml, pyyaml, tqdm
- Created `config.yaml` for all settings
- Established custom dictionary system with three categories:
  - `custom_terms.txt` - domain-specific vocabulary and technical terms
  - `proper_nouns.txt` - names, brands, and organizations
  - `locations.txt` - geographic locations

#### Phase 2: Core Implementation
- Built main `WebsiteSpellChecker` class with full functionality
- Implemented sitemap parsing with recursion protection
- Added clean text extraction from HTML
- Created spell checking engine with custom dictionary loading
- Built concurrent page processing with progress tracking

#### Phase 3: Debugging & Fixes
**Major Issues Encountered & Resolved:**

1. **Infinite Sitemap Loop**
   - **Problem**: Sitemap parsing got stuck in recursive loops
   - **Solution**: Added `visited_sitemaps` tracking to prevent re-parsing same URLs

2. **URL Filtering Too Restrictive**
   - **Problem**: Include patterns `*.html`, `*.htm` excluded modern clean URLs like `/about/`
   - **Solution**: Updated patterns to include `*`, `*/`, `*/?` for comprehensive coverage

3. **Invalid URL Crawling**
   - **Problem**: Script tried to crawl `mailto:`, `javascript:` links causing errors
   - **Solution**: Added URL validation to skip non-HTTP schemes

4. **Parser Encoding Issues**
   - **Problem**: BeautifulSoup failed on some pages with encoding problems
   - **Solution**: Added fallback parsers (lxml → html.parser) and better encoding detection

5. **Critical Regex Bug**
   - **Problem**: Word extraction regex `r'\b[a-zA-Z]{' + str(min_length) + ',}\b'` was malformed
   - **Symptom**: Found 0 words despite extracting text (534 words → 0 words to check)
   - **Solution**: Fixed to `r'\b[a-zA-Z]{' + str(min_length) + r',}\b'` with proper raw string

6. **Spell Checker Candidates Error**
   - **Problem**: `spell_checker.candidates()` sometimes returned `None`
   - **Solution**: Added null check: `candidates if candidates else []`

#### Phase 4: Enhanced Features
- **Broken Link Detection**: Added HTTP error tracking during crawling
- **Tabbed HTML Reports**: Created interactive interface with separate tabs for spelling errors and broken links
- **Dual CSV Exports**: Separate files for `spelling_errors.csv` and `broken_links.csv`
- **Enhanced Logging**: Added detailed debug output for troubleshooting
- **Better Error Categorization**: Specific handling for timeouts, connection errors, HTTP errors

#### Phase 5: Smart Filtering
- **Email/Domain Fragment Detection**: Added intelligent filtering to exclude email addresses and website names
  - **Problem**: False positives from fragments like "info" in "info@site.com" or words embedded in domain names
  - **Solution**: Context-aware pattern matching that detects when words are part of:
    - Email addresses (info@domain.com)
    - Domain names (www.example.com, subdomain.site.org)
    - Compound domain-like words
  - **Result**: Significant reduction in false positives while preserving real spelling errors

#### Phase 6: External Link Checking
- **Comprehensive Link Validation**: Extended broken link detection to include external links
  - **Feature**: Extract and test all external links found on each page
  - **Implementation**:
    - Separate session with browser-like headers for external requests
    - Configurable timeout (10 seconds default)
    - Deduplication to avoid checking same link multiple times
    - Track which page each broken link was found on
  - **Error Handling**: Detect HTTP errors, timeouts, connection failures
  - **Reporting**: Visual distinction between internal (🏠) and external (🔗) links
  - **Bug Fix**: Fixed status code sorting to handle mixed integer/string types (404 vs 'TIMEOUT')

#### Phase 7: Optional Features
- **Feature Toggle System**: Made spell checking and link validation optional
  - **Problem**: Users wanted ability to run just one feature (e.g., only link checking)
  - **Solution**: Added configuration and command-line flags to enable/disable features independently
  - **Configuration**:
    - Added `features` section in config.yaml with `enable_spell_checking` and `enable_link_checking` flags
    - Command-line arguments override config file settings
  - **Command-line Arguments**:
    - `--spell-check` / `--no-spell-check` - Enable/disable spell checking
    - `--link-check` / `--no-link-check` - Enable/disable link checking
  - **Implementation**:
    - Conditional initialization of spell checker components
    - Conditional execution in `process_url()` method
    - Dynamic HTML report generation (only shows enabled features)
    - Selective CSV report generation (only creates files for enabled features)
    - Updated summary output to show active features
  - **Benefits**:
    - Faster execution when only one feature is needed
    - Reduced resource usage (no spell checker loading if not needed)
    - Flexibility for different use cases (e.g., daily link checks, weekly spell checks)

#### Phase 8: Report Layout Improvements
- **Fixed-Width Table Layout**: Improved HTML report readability
  - **Problem**: Extremely long URLs were pushing table columns off the page, making reports hard to read
  - **Solution**: Implemented fixed-width table layout with proper text wrapping
  - **Implementation**:
    - Added `table-layout: fixed` to force consistent column widths
    - Set specific percentage widths for each column in both tables
    - Added `word-wrap: break-word` and `overflow-wrap: break-word` for proper text wrapping
    - Used `word-break: break-all` for URLs to break at any character if needed
  - **Column Width Distribution**:
    - Spelling Errors: URL (25%), Word (12%), Suggestions (20%), Context (35%), Confidence (8%)
    - Broken Links: URL (30%), Type (12%), Status (10%), Error (18%), Found On (30%)
  - **Result**: Reports now maintain consistent layout regardless of URL length

- **Report Regeneration Tool**: Created standalone script to rebuild HTML from CSV data
  - **Problem**: Needed to update report layout without re-running entire scan
  - **Solution**: Created `regenerate_report.py` script
  - **Features**:
    - Reads existing CSV files (spelling_errors.csv, broken_links.csv)
    - Generates fresh HTML report with current styling/layout
    - Works with partial data (spelling only, links only, or both)
    - Preserves original scan timestamps in CSV data
  - **Usage**: `python3 regenerate_report.py`
  - **Benefits**:
    - Quick layout updates without rescanning
    - Test report design changes instantly
    - Share updated report formats with existing data

#### Phase 9: Generic Refactoring
- **Made Tool Generic**: Removed genealogy-specific references for broader applicability
  - **Motivation**: Tool proved useful beyond genealogy websites
  - **Changes Made**:
    - Renamed dictionary files to generic names (`custom_terms.txt`, `proper_nouns.txt`, `locations.txt`)
    - Updated all code comments and documentation to remove genealogy mentions
    - Replaced genealogy-specific website filtering with generic domain fragment detection
    - Cleaned dictionary files to have generic examples
    - Rewrote README.md to be concise and applicable to any website type
    - Updated configuration examples to use generic placeholder URLs
    - **Cleaned up test files**:
      - Deleted `test_genealogy_page.py` (hardcoded to specific genealogy site)
      - Deleted `test_image_links.py` (hardcoded to specific genealogy site)
      - Deleted `test_output.log` (old log file)
      - Updated `test_spellcheck.py` with generic test words (website, webinar, etc.)
      - Updated `test_email_domain_filter.py` with generic domain examples
  - **Result**: Tool now suitable for any website maintenance use case while retaining all functionality

## File Structure
```
website_spellcheck/
├── CLAUDE.md                       # This development log
├── README.md                       # User documentation
├── requirements.txt                # Python dependencies
├── config.yaml                     # Configuration settings
├── setup.sh                        # Installation script
├── website_spellcheck.py           # Main application
├── regenerate_report.py            # Standalone HTML report regenerator
├── test_spellcheck.py              # Spell checker test script
├── test_email_domain_filter.py     # Email/domain filtering test script
├── dictionaries/                   # Custom word lists
│   ├── custom_terms.txt           # Domain-specific vocabulary
│   ├── proper_nouns.txt           # Names, brands, organizations
│   └── locations.txt              # Geographic locations
└── reports/                        # Generated output
    ├── spell_check_report.html    # Interactive tabbed report
    ├── spelling_errors.csv        # Spelling data
    └── broken_links.csv           # Broken link data
```

## Configuration
The system is highly configurable via `config.yaml`:

### Website Settings
- `max_pages`: Limit crawling scope (100 default)
- `max_depth`: Recursive crawling depth (3 levels)
- `delay`: Rate limiting between requests (1.0 seconds)

### Crawling Strategy
- `use_sitemap`: Try sitemap.xml first (true)
- `recursive_fallback`: Use recursive crawling if no sitemap (true)
- `check_external_links`: Enable external link validation (true)
- `external_link_timeout`: Timeout for external requests (10 seconds)
- URL include/exclude patterns for filtering

### Spell Checking
- `language`: Dictionary language ("en")
- `min_word_length`: Minimum word length to check (3)
- `check_proper_nouns`: Whether to check capitalized words (false)
- Custom dictionary file paths

### Performance
- `max_workers`: Concurrent processing threads (5)
- Timeout and caching settings

## Key Technical Decisions

### Library Choices
- **requests + BeautifulSoup** over Scrapy: Simpler for this use case, easier to debug
- **pyspellchecker** over enchant: Pure Python, better performance, easier custom dictionaries
- **html2text** for text extraction: Clean output, handles complex layouts well

### Architecture Patterns
- **Strategy Pattern**: Hybrid crawling (sitemap → recursive fallback)
- **Template Method**: Consistent processing pipeline for all pages
- **Observer Pattern**: Progress tracking and logging throughout

### Error Handling
- **Graceful Degradation**: Continue processing if individual pages fail
- **Comprehensive Logging**: Detailed error messages for troubleshooting
- **Fallback Strategies**: Multiple parsers, encoding detection, timeout handling

## Testing & Validation
- Tested on multiple live websites with varying structures
- Processed 300+ URLs from sitemap discovery
- Successfully found and categorized both spelling errors and broken links
- Validated spell checker with intentional misspellings (wrold → world, teh → the)
- External link checking finds broken outbound links (404s, timeouts, connection errors)
- Smart email/domain filtering reduces false positives significantly
- Status code handling supports both HTTP codes (404) and system errors ('TIMEOUT')
- Feature toggle testing: Verified both features work independently and together
- Fixed-width layout tested with extremely long URLs (200+ characters)
- Report regeneration tested with large datasets (60+ spelling errors, 2400+ broken links)
- **Test Scripts Available**:
  - `test_spellcheck.py` - Validates spell checker functionality with test words
  - `test_email_domain_filter.py` - Verifies email/domain filtering accuracy

## Current Status
✅ **Fully Functional Website Health Checker**
- **Optional Features** - Run spell checking, link checking, or both
- Spell checking with custom dictionary support
- **Smart Email/Domain Filtering** - Automatically excludes email addresses and website names
- **Internal & External Link Checking** - Validates both site pages and outbound links
- **Fixed-Width Report Layout** - Professional reports that handle long URLs gracefully
- Interactive HTML reports with tabbed interface showing link sources
- CSV exports for data analysis with link categorization
- **Report Regeneration Tool** - Update report layout without re-scanning
- Comprehensive logging and error handling
- Concurrent processing for performance
- Flexible command-line interface with feature toggles
- **Generic and Reusable** - Suitable for any type of website

## Usage Examples
```bash
# Basic usage (both spell checking and link checking)
python3 website_spellcheck.py https://your-website.com

# With verbose logging
python3 website_spellcheck.py https://your-website.com -v

# Custom config file
python3 website_spellcheck.py https://your-website.com -c custom_config.yaml

# Link checking only (no spell checking)
python3 website_spellcheck.py https://your-website.com --no-spell-check

# Spell checking only (no link checking)
python3 website_spellcheck.py https://your-website.com --no-link-check

# Enable only one feature explicitly
python3 website_spellcheck.py https://your-website.com --link-check --no-spell-check

# Regenerate HTML report from existing CSV files (no re-scanning)
python3 regenerate_report.py
```

## Future Enhancement Ideas
- Email notifications for broken links
- Scheduled runs with cron integration
- GitHub Actions integration for continuous monitoring
- Link depth analysis (which pages link to broken URLs)
- Historical tracking of issues over time
- WordPress plugin integration
- Support for authentication (login-protected areas)
- Image alt-text spell checking
- SEO analysis integration

## Dependencies
```
requests>=2.31.0          # HTTP client
beautifulsoup4>=4.12.0    # HTML parsing
pyspellchecker>=0.8.3     # Spell checking engine
html2text>=2020.1.16     # Clean text extraction
lxml>=4.9.0               # Fast XML parsing
pyyaml>=6.0.0             # Configuration files
tqdm>=4.66.0              # Progress bars
```

---
*This log is maintained to track development progress and assist with future enhancements.*