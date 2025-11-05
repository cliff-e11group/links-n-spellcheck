# Website Spell Checker

A comprehensive Python tool for crawling websites and performing spell checking on content, specifically designed for genealogy websites with custom dictionary support.

## Features

- **Smart Website Crawling**: Uses sitemap.xml discovery with recursive crawling fallback
- **Custom Dictionaries**: Support for genealogy-specific terms, family names, and place names
- **Multiple Report Formats**: Interactive HTML reports and CSV exports
- **Performance Optimized**: Concurrent processing with configurable threading
- **Flexible Configuration**: YAML-based configuration for all aspects of the tool
- **Context-Aware**: Shows surrounding text for each spelling error
- **Rate Limiting**: Respectful crawling with configurable delays

## Installation

1. **Clone or download this repository**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

1. **Edit the configuration file** (`config.yaml`):
   ```yaml
   website:
     url: "https://your-genealogy-website.com"
   ```

2. **Add your custom terms** to the dictionary files:
   - `dictionaries/family_names.txt` - Add family surnames
   - `dictionaries/place_names.txt` - Add location names
   - `dictionaries/genealogy_terms.txt` - Already populated with common terms

3. **Run the spell checker**:
   ```bash
   python website_spellcheck.py https://your-website.com
   ```

4. **View the results**:
   - HTML Report: `reports/spell_check_report.html`
   - CSV Data: `reports/spell_check_report.csv`

## Configuration

The `config.yaml` file controls all aspects of the spell checker:

### Website Settings
```yaml
website:
  url: "https://example.com"
  max_pages: 100        # Maximum pages to crawl (0 = unlimited)
  max_depth: 3          # Maximum crawl depth
  delay: 1.0           # Delay between requests (seconds)
```

### Crawling Strategy
```yaml
crawling:
  use_sitemap: true           # Try sitemap.xml first
  recursive_fallback: true    # Use recursive crawling if no sitemap
  follow_external_links: false
  
  include_patterns:           # URL patterns to include
    - "*.html"
    - "*.htm"
  exclude_patterns:           # URL patterns to exclude
    - "*/admin/*"
    - "*.pdf"
```

### Spell Checking
```yaml
spell_checking:
  language: "en"
  min_word_length: 3
  check_proper_nouns: false   # Skip capitalized words
  confidence_threshold: 0.8
  
  custom_dictionaries:       # Your custom word lists
    - "dictionaries/genealogy_terms.txt"
    - "dictionaries/family_names.txt"
    - "dictionaries/place_names.txt"
```

### Performance
```yaml
performance:
  max_workers: 5       # Concurrent processing threads
  chunk_size: 10       # Pages per processing batch
  enable_caching: true # Cache results for efficiency
```

## Custom Dictionaries

### Adding Family Names
Edit `dictionaries/family_names.txt`:
```
smith
johnson
mcpherson
o'connell
van der berg
```

### Adding Place Names
Edit `dictionaries/place_names.txt`:
```
massachusetts
yorkshire
bavaria
philadelphia
dublin
```

### Adding Genealogy Terms
The `dictionaries/genealogy_terms.txt` file is pre-populated but you can add more:
```
genealogy
ancestry
lineage
pedigree
probate
baptism
```

## Command Line Options

```bash
python website_spellcheck.py [URL] [OPTIONS]

Options:
  -c, --config CONFIG    Configuration file path (default: config.yaml)
  -v, --verbose         Enable verbose logging
  -h, --help           Show help message
```

### Examples

**Basic usage**:
```bash
python website_spellcheck.py https://mygenealogy.com
```

**Custom config file**:
```bash
python website_spellcheck.py https://mysite.com -c my_config.yaml
```

**Verbose output**:
```bash
python website_spellcheck.py https://mysite.com -v
```

## Output Reports

### HTML Report
- **Interactive table** with sortable columns
- **Direct links** to pages with errors
- **Context preview** showing surrounding text
- **Statistics dashboard** with processing summary
- **Suggestions** for each misspelled word

### CSV Report
Columns included:
- `url` - Page where error was found
- `word` - The misspelled word
- `suggestions` - Comma-separated correction suggestions
- `context` - Surrounding text context
- `confidence` - Confidence score for the error
- `timestamp` - When the error was found

## Troubleshooting

### Common Issues

**"No URLs found to process"**
- Check if the website has a sitemap.xml
- Enable `recursive_fallback: true` in config
- Verify the base URL is accessible

**"Too many false positives"**
- Add terms to your custom dictionaries
- Set `check_proper_nouns: false` 
- Increase `confidence_threshold`

**"Slow processing"**
- Reduce `max_workers` if hitting rate limits
- Increase `delay` between requests
- Limit `max_pages` for testing

**"Memory issues with large sites"**
- Reduce `max_pages` and `max_workers`
- Process site in sections using URL patterns

### Logs and Debugging

- Check `spellcheck.log` for detailed processing information
- Use `-v` flag for verbose console output
- Monitor the progress bar for processing status

## Technical Details

### Libraries Used
- **requests**: HTTP client for web crawling
- **BeautifulSoup**: HTML parsing and text extraction  
- **pyspellchecker**: Pure Python spell checking
- **html2text**: Clean text extraction from HTML
- **PyYAML**: Configuration file parsing
- **tqdm**: Progress bars for better UX

### Architecture
- **Modular Design**: Separate components for crawling, text extraction, spell checking
- **Concurrent Processing**: Thread-pool based processing for performance
- **Memory Efficient**: Streaming processing to handle large websites
- **Error Resilient**: Continues processing even if individual pages fail

## Contributing

Feel free to submit issues and enhancement requests. This tool is designed to be easily extensible for different types of websites and use cases.

## License

This project is open source. 
