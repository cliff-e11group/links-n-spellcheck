# Website Spell Checker

A comprehensive Python tool for website health checking that performs spell checking and broken link detection with custom dictionary support.

## Features

- **Smart Website Crawling** - Sitemap.xml discovery with recursive crawling fallback
- **Spell Checking** - Comprehensive content analysis with custom dictionaries
- **Broken Link Detection** - Internal and external link validation
- **Custom Dictionaries** - Support for domain-specific terms, proper nouns, and locations
- **Interactive Reports** - HTML reports with tabbed interface and CSV exports
- **Optional Features** - Run spell checking, link checking, or both
- **Concurrent Processing** - Multi-threaded for performance

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Basic Usage

```bash
# Check both spelling and links
python3 website_spellcheck.py https://example.com

# Link checking only
python3 website_spellcheck.py https://example.com --no-spell-check

# Spell checking only
python3 website_spellcheck.py https://example.com --no-link-check

# With verbose logging
python3 website_spellcheck.py https://example.com -v
```

### View Results

- **HTML Report**: `reports/spell_check_report.html`
- **Spelling CSV**: `reports/spelling_errors.csv`
- **Broken Links CSV**: `reports/broken_links.csv`

## Configuration

Edit `config.yaml` to customize:

```yaml
# Enable/disable features
features:
  enable_spell_checking: true
  enable_link_checking: true

# Crawling settings
website:
  url: "https://example.com"
  max_pages: 0  # 0 = unlimited
  max_depth: 3
  delay: 1.0

# Spell checking
spell_checking:
  language: "en"
  min_word_length: 3
  check_proper_nouns: false
  custom_dictionaries:
    - "dictionaries/custom_terms.txt"
    - "dictionaries/proper_nouns.txt"
    - "dictionaries/locations.txt"

# Performance
performance:
  max_workers: 5
```

## Custom Dictionaries

Add domain-specific vocabulary to avoid false positives:

**`dictionaries/custom_terms.txt`** - Technical terms, jargon, abbreviations
```
website
webinar
api
```

**`dictionaries/proper_nouns.txt`** - Names, brands, organizations
```
acme
techcorp
```

**`dictionaries/locations.txt`** - Cities, states, countries
```
california
toronto
```

## Command Line Options

```bash
python3 website_spellcheck.py [URL] [OPTIONS]

Arguments:
  URL                      Website URL to check

Options:
  -c, --config FILE        Configuration file (default: config.yaml)
  -v, --verbose           Enable verbose logging
  --spell-check           Enable spell checking
  --no-spell-check        Disable spell checking
  --link-check            Enable link checking
  --no-link-check         Disable link checking
  -h, --help              Show help message
```

## Report Features

### HTML Report
- Interactive tabbed interface (Spelling Errors / Broken Links)
- Sortable columns
- Direct links to problem pages
- Context preview for spelling errors
- Visual indicators for link types (internal/external)
- Statistics dashboard

### CSV Reports
- Importable data for analysis
- Timestamp tracking
- Full context and suggestions

## Troubleshooting

**No URLs found**
- Verify website has sitemap.xml or enable `recursive_fallback`
- Check URL is accessible

**Too many false positives**
- Add terms to custom dictionaries
- Set `check_proper_nouns: false`
- Increase `min_word_length`

**Slow processing**
- Reduce `max_workers`
- Increase `delay` between requests
- Limit `max_pages` for testing

## Dependencies

- requests - HTTP client
- beautifulsoup4 - HTML parsing
- pyspellchecker - Spell checking
- html2text - Text extraction
- lxml - XML parsing
- pyyaml - Configuration
- tqdm - Progress bars

## License

Open source. Use freely for website maintenance and quality assurance.
