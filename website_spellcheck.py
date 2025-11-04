#!/usr/bin/env python3
"""
Website Spell Checker
A comprehensive tool for crawling websites and performing spell checking on content.
Designed specifically for genealogy websites with custom dictionary support.
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
import time
import urllib.parse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

import html2text
import requests
import yaml
from bs4 import BeautifulSoup
from spellchecker import SpellChecker
from tqdm import tqdm


class WebsiteSpellChecker:
    """Main class for website spell checking functionality."""
    
    def __init__(self, config_path: str = "config.yaml", enable_spell_checking: bool = None, enable_link_checking: bool = None):
        """Initialize the spell checker with configuration."""
        self.config = self._load_config(config_path)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WebsiteSpellChecker/1.0 (Genealogy Site Checker)'
        })

        # Determine which features are enabled
        # Command-line arguments override config file
        self.enable_spell_checking = enable_spell_checking if enable_spell_checking is not None else self.config.get('features', {}).get('enable_spell_checking', True)
        self.enable_link_checking = enable_link_checking if enable_link_checking is not None else self.config.get('features', {}).get('enable_link_checking', True)

        logging.info(f"Features enabled - Spell checking: {self.enable_spell_checking}, Link checking: {self.enable_link_checking}")

        # Initialize spell checker only if needed
        if self.enable_spell_checking:
            self.spell_checker = SpellChecker(language=self.config['spell_checking']['language'])
            self._load_custom_dictionaries()

            # Test spell checker functionality
            logging.info("Testing spell checker...")
            test_words = ["hello", "wrold", "teh", "spellling"]  # Mix of correct and incorrect words
            for word in test_words:
                is_correct = word in self.spell_checker
                suggestions = list(self.spell_checker.candidates(word))[:3] if not is_correct else []
                logging.info(f"Test word '{word}': {'✓ correct' if is_correct else '✗ misspelled'} {suggestions}")
            logging.info(f"Spell checker dictionary size: {len(self.spell_checker.word_frequency.dictionary)}")

            # Initialize HTML to text converter
            self.html_converter = html2text.HTML2Text()
            self.html_converter.ignore_links = True
            self.html_converter.ignore_images = True
        else:
            logging.info("Spell checking disabled")
            self.spell_checker = None
            self.html_converter = None

        # Results storage
        self.crawled_urls: Set[str] = set()
        self.errors: List[Dict] = []
        self.broken_links: List[Dict] = []
        self.external_links_checked: Set[str] = set()  # Track checked external links
        self.stats = defaultdict(int)

        # Setup logging
        self._setup_logging()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logging.error(f"Configuration file {config_path} not found")
            sys.exit(1)
        except yaml.YAMLError as e:
            logging.error(f"Error parsing configuration file: {e}")
            sys.exit(1)
    
    def _setup_logging(self):
        """Setup logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('spellcheck.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _load_custom_dictionaries(self):
        """Load custom dictionary files."""
        custom_words = set()
        
        for dict_file in self.config['spell_checking']['custom_dictionaries']:
            dict_path = Path(dict_file)
            if dict_path.exists():
                try:
                    with open(dict_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#'):
                                custom_words.add(line.lower())
                    logging.info(f"Loaded {len(custom_words)} words from {dict_file}")
                except Exception as e:
                    logging.warning(f"Error loading dictionary {dict_file}: {e}")
            else:
                logging.warning(f"Dictionary file not found: {dict_file}")
        
        # Add custom words to spell checker
        self.spell_checker.word_frequency.load_words(custom_words)
    
    def discover_urls(self, base_url: str) -> Set[str]:
        """Discover URLs using sitemap and/or recursive crawling."""
        urls = set()
        
        if self.config['crawling']['use_sitemap']:
            logging.info("Starting sitemap discovery...")
            sitemap_urls = self._parse_sitemap(base_url, set())
            urls.update(sitemap_urls)
            logging.info(f"Found {len(sitemap_urls)} URLs from sitemap")
            if len(sitemap_urls) > 0:
                logging.info(f"Sample URLs: {list(sitemap_urls)[:3]}")
        
        if self.config['crawling']['recursive_fallback'] and len(urls) == 0:
            logging.info("No URLs from sitemap, starting recursive crawling...")
            recursive_urls = self._recursive_crawl(base_url)
            urls.update(recursive_urls)
            logging.info(f"Found {len(recursive_urls)} URLs from recursive crawling")
        
        # Apply URL filtering
        logging.info(f"Applying URL filtering to {len(urls)} URLs...")
        filtered_urls = self._filter_urls(urls)
        logging.info(f"After filtering: {len(filtered_urls)} URLs to process")
        
        if len(filtered_urls) == 0:
            logging.error("No URLs found after filtering. Check your include/exclude patterns.")
        
        return filtered_urls
    
    def _parse_sitemap(self, sitemap_url: str, visited_sitemaps: Set[str] = None) -> Set[str]:
        """Parse sitemap.xml to extract URLs with recursion protection."""
        if visited_sitemaps is None:
            visited_sitemaps = set()
            
        urls = set()
        
        # If sitemap_url looks like a base URL, try to find the sitemap
        if not sitemap_url.endswith('.xml') and not sitemap_url.endswith('/sitemap'):
            base_url = sitemap_url
            sitemap_url = self.config['crawling']['sitemap_url']
            
            if not sitemap_url:
                # Try common sitemap locations
                common_paths = ['/sitemap.xml', '/sitemap_index.xml', '/sitemap']
                for path in common_paths:
                    test_url = urllib.parse.urljoin(base_url, path)
                    try:
                        response = self.session.get(test_url, timeout=10)
                        if response.status_code == 200:
                            sitemap_url = test_url
                            break
                    except requests.RequestException:
                        continue
        
        if sitemap_url and sitemap_url not in visited_sitemaps:
            visited_sitemaps.add(sitemap_url)
            try:
                logging.info(f"Parsing sitemap: {sitemap_url}")
                response = self.session.get(sitemap_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'xml')
                    
                    # Handle sitemap index files
                    sitemap_tags = soup.find_all('sitemap')
                    if sitemap_tags:
                        logging.info(f"Found {len(sitemap_tags)} sub-sitemaps")
                        for sitemap_tag in sitemap_tags:
                            loc_tag = sitemap_tag.find('loc')
                            if loc_tag and loc_tag.text not in visited_sitemaps:
                                sub_urls = self._parse_sitemap(loc_tag.text, visited_sitemaps)
                                urls.update(sub_urls)
                    
                    # Handle regular sitemap files
                    url_tags = soup.find_all('url')
                    if url_tags:
                        logging.info(f"Found {len(url_tags)} URLs in sitemap")
                        for url_tag in url_tags:
                            loc_tag = url_tag.find('loc')
                            if loc_tag:
                                urls.add(loc_tag.text)
                else:
                    logging.warning(f"HTTP {response.status_code} for sitemap {sitemap_url}")
                            
            except Exception as e:
                logging.warning(f"Error parsing sitemap {sitemap_url}: {e}")
        elif sitemap_url in visited_sitemaps:
            logging.warning(f"Skipping already visited sitemap: {sitemap_url}")
        
        return urls
    
    def _recursive_crawl(self, base_url: str, max_depth: int = None) -> Set[str]:
        """Recursively crawl website starting from base URL."""
        if max_depth is None:
            max_depth = self.config['website']['max_depth']
        
        urls = set()
        to_visit = [(base_url, 0)]
        visited = set()
        
        while to_visit and len(urls) < self.config['website']['max_pages']:
            url, depth = to_visit.pop(0)
            
            if url in visited or depth > max_depth:
                continue
            
            visited.add(url)
            
            try:
                response = self.session.get(url, timeout=10)
                if response.status_code == 200:
                    urls.add(url)
                    
                    if depth < max_depth:
                        try:
                            soup = BeautifulSoup(response.content, 'lxml')
                        except:
                            # Fallback to html.parser if lxml fails
                            soup = BeautifulSoup(response.content, 'html.parser')
                        
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            
                            # Skip invalid URL schemes
                            if href.startswith(('mailto:', 'javascript:', 'tel:', '#')):
                                continue
                                
                            absolute_url = urllib.parse.urljoin(url, href)
                            
                            # Only follow internal links unless configured otherwise
                            if self._is_internal_url(absolute_url, base_url) and self._is_valid_url(absolute_url):
                                to_visit.append((absolute_url, depth + 1))
                
                # Respect rate limiting
                time.sleep(self.config['website']['delay'])
                
            except requests.RequestException as e:
                logging.warning(f"Error crawling {url}: {e}")
        
        return urls
    
    def _is_internal_url(self, url: str, base_url: str) -> bool:
        """Check if URL is internal to the base domain."""
        try:
            base_domain = urllib.parse.urlparse(base_url).netloc
            url_domain = urllib.parse.urlparse(url).netloc
            return url_domain == base_domain or url_domain == ""
        except Exception:
            return False
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and processable."""
        try:
            parsed = urllib.parse.urlparse(url)
            # Must have valid scheme and netloc
            if parsed.scheme not in ['http', 'https']:
                return False
            if not parsed.netloc:
                return False
            return True
        except Exception:
            return False
    
    def _filter_urls(self, urls: Set[str]) -> Set[str]:
        """Filter URLs based on include/exclude patterns."""
        filtered_urls = set()
        
        include_patterns = self.config['crawling']['include_patterns']
        exclude_patterns = self.config['crawling']['exclude_patterns']
        
        for url in urls:
            # Check exclude patterns first
            if any(self._match_pattern(url, pattern) for pattern in exclude_patterns):
                continue
            
            # Check include patterns
            if not include_patterns or any(self._match_pattern(url, pattern) for pattern in include_patterns):
                filtered_urls.add(url)
        
        return filtered_urls
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """Match text against a pattern (supports simple wildcards)."""
        import fnmatch
        return fnmatch.fnmatch(text.lower(), pattern.lower())
    
    def extract_text(self, html_content: str, url: str) -> str:
        """Extract clean text from HTML content."""
        try:
            # Try different parsers if needed
            try:
                soup = BeautifulSoup(html_content, 'lxml')
            except:
                try:
                    soup = BeautifulSoup(html_content, 'html.parser')
                except:
                    # Fallback - just return empty string if parsing fails
                    logging.warning(f"Could not parse HTML for {url}")
                    return ""
            
            # Remove unwanted elements
            for element in soup(self.config['text_extraction']['ignore_elements']):
                element.decompose()
            
            # Extract text using html2text
            text = self.html_converter.handle(str(soup))
            
            # Clean up the text
            text = re.sub(r'\n\s*\n', '\n\n', text)  # Normalize line breaks
            text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
            
            return text.strip()
        except Exception as e:
            logging.warning(f"Error extracting text from {url}: {e}")
            return ""
    
    def spell_check_text(self, text: str, url: str) -> List[Dict]:
        """Perform spell checking on text and return errors."""
        errors = []
        min_length = self.config['spell_checking']['min_word_length']
        
        # Split text into words and track positions
        pattern = r'\b[a-zA-Z]{' + str(min_length) + r',}\b'
        words = list(re.finditer(pattern, text))
        logging.debug(f"Using regex pattern: {pattern}")
        
        logging.debug(f"Found {len(words)} words to check in {url} (min_length={min_length})")
        
        # Show a sample of words being checked for debugging
        if len(words) > 0:
            sample_words = [match.group() for match in words[:10]]
            logging.debug(f"Sample words from {url}: {sample_words}")
        
        words_checked = 0
        words_skipped = 0
        
        for match in words:
            word = match.group().lower()
            original_word = match.group()
            start_pos = match.start()
            end_pos = match.end()
            
            # Skip proper nouns if configured
            if not self.config['spell_checking']['check_proper_nouns']:
                if original_word[0].isupper() and len(original_word) > 1:
                    words_skipped += 1
                    continue
            
            # Skip words that are part of email addresses or domain names
            if self._is_email_or_domain_fragment(word, text, start_pos, end_pos):
                words_skipped += 1
                logging.debug(f"Skipped email/domain fragment: '{word}'")
                continue
            
            words_checked += 1
            
            # Check if word is misspelled
            if word not in self.spell_checker:
                # Get suggestions
                candidates = self.spell_checker.candidates(word)
                suggestions = list(candidates)[:self.config['reporting']['max_suggestions']] if candidates else []
                
                # Get context
                context_length = self.config['reporting']['context_length']
                context_start = max(0, start_pos - context_length)
                context_end = min(len(text), end_pos + context_length)
                context = text[context_start:context_end].strip()
                
                # Calculate confidence (simple heuristic)
                confidence = 1.0 - (len(word) / 20.0)  # Longer words get lower confidence
                
                error = {
                    'url': url,
                    'word': match.group(),  # Original case
                    'word_lower': word,
                    'suggestions': suggestions,
                    'context': context,
                    'position': start_pos,
                    'confidence': confidence,
                    'timestamp': datetime.now().isoformat()
                }
                
                errors.append(error)
                logging.debug(f"Misspelled word found: '{word}' in {url}")
        
        logging.debug(f"Spell check results for {url}: {words_checked} words checked, {words_skipped} skipped, {len(errors)} errors found")
        
        return errors
    
    def _is_email_or_domain_fragment(self, word: str, text: str, start_pos: int, end_pos: int) -> bool:
        """Check if a word is part of an email address or domain name."""
        
        # Get a larger context around the word to check for email/domain patterns
        context_start = max(0, start_pos - 30)
        context_end = min(len(text), end_pos + 30)
        context = text[context_start:context_end]
        
        # Find the word's position within this context
        word_start_in_context = start_pos - context_start
        word_end_in_context = end_pos - context_start
        
        # Check for email address patterns
        email_patterns = [
            r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',  # Standard email
            r'\b[a-zA-Z0-9._%+-]+\s*@\s*[a-zA-Z0-9.-]+\s*\.\s*[a-zA-Z]{2,}\b',  # Email with spaces
        ]
        
        for pattern in email_patterns:
            for match in re.finditer(pattern, context, re.IGNORECASE):
                if match.start() <= word_start_in_context < match.end():
                    return True
        
        # Check for domain name patterns
        domain_patterns = [
            r'\b[a-zA-Z0-9.-]+\.(com|org|net|edu|gov|info|biz|co\.uk|ca|au|de|fr|it|es|ru|jp|cn|in)\b',  # Common TLDs
            r'\bwww\.[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',  # www. domains
            r'\bhttps?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s]*\b',  # Full URLs
        ]
        
        for pattern in domain_patterns:
            for match in re.finditer(pattern, context, re.IGNORECASE):
                if match.start() <= word_start_in_context < match.end():
                    return True
        
        # Check for compound domain-like words (familysearch, familytree, etc.)
        # Look for patterns like: word1word2.tld or word1word2word3.tld
        compound_domain_pattern = r'\b[a-zA-Z]+[a-zA-Z0-9]*\.(com|org|net|edu|gov|info)\b'
        for match in re.finditer(compound_domain_pattern, context, re.IGNORECASE):
            # Check if our word is part of the domain name part (before the TLD)
            domain_part = match.group().split('.')[0].lower()
            if word in domain_part and len(word) >= 4:  # Only for longer fragments
                return True
        
        # Check for specific genealogy website fragments
        genealogy_sites = [
            'familysearch', 'ancestry', 'myheritage', 'findmypast', 'genealogybank',
            'familytree', 'rootsweb', 'geni', 'wikitree', 'billiongraves',
            'findagrave', 'newspapers', 'chroniclingamerica', 'familytreemagazine'
        ]
        
        # Check if word is a fragment of a known genealogy site
        for site in genealogy_sites:
            if word in site and len(word) >= 4:
                # Check if the full site name appears in the context
                if site in context.lower():
                    return True
        
        return False
    
    def _check_all_links_on_page(self, html_content: str, source_url: str):
        """Extract and check all links and resources from a page."""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all different types of links and resources
            links_to_check = []
            
            # 1. Standard hyperlinks (<a href="...">)
            for link in soup.find_all('a', href=True):
                href = link['href']
                if not href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
                    # Check if this anchor tag links to an image file
                    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff', '.tif')
                    if any(href.lower().endswith(ext) for ext in image_extensions):
                        links_to_check.append((href, 'image'))
                    else:
                        links_to_check.append((href, 'hyperlink'))
            
            # 2. Images (<img src="...">)
            for img in soup.find_all('img', src=True):
                src = img['src']
                if not src.startswith(('data:', '#')):  # Skip data URIs and anchors
                    links_to_check.append((src, 'image'))
            
            # 3. CSS stylesheets (<link rel="stylesheet" href="...">)
            for css_link in soup.find_all('link', {'rel': 'stylesheet', 'href': True}):
                href = css_link['href']
                links_to_check.append((href, 'css'))
            
            # 4. JavaScript files (<script src="...">)
            for script in soup.find_all('script', src=True):
                src = script['src']
                if not src.startswith('data:'):  # Skip data URIs
                    links_to_check.append((src, 'javascript'))
            
            # 5. Other media files (audio, video, source, object, embed)
            for media_tag in soup.find_all(['audio', 'video', 'source', 'object', 'embed']):
                for attr in ['src', 'data']:
                    if media_tag.get(attr):
                        url = media_tag[attr]
                        if not url.startswith(('data:', '#')):
                            links_to_check.append((url, 'media'))
            
            # Check all collected links
            for url, link_type in links_to_check:
                # Convert relative URLs to absolute
                absolute_url = urllib.parse.urljoin(source_url, url)
                
                # Detect document files by extension for hyperlinks
                if link_type == 'hyperlink':
                    parsed_url = urllib.parse.urlparse(absolute_url)
                    path_lower = parsed_url.path.lower()
                    document_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar'}
                    if any(path_lower.endswith(ext) for ext in document_extensions):
                        link_type = 'document'
                
                # Check if it's a valid URL
                if self._is_valid_url(absolute_url):
                    should_check = False
                    
                    # Always check external links
                    if not self._is_internal_url(absolute_url, source_url):
                        should_check = True
                    # Also check internal resources (images, documents, CSS, JS, media)
                    elif link_type in ['image', 'document', 'css', 'javascript', 'media']:
                        should_check = True
                    
                    if should_check and absolute_url not in self.external_links_checked:
                        self.external_links_checked.add(absolute_url)
                        self._check_single_link(absolute_url, source_url, link_type)
                        
        except Exception as e:
            logging.debug(f"Error extracting links from {source_url}: {e}")
    
    def _check_single_link(self, url: str, found_on_url: str, link_type: str = 'hyperlink'):
        """Check a single link or resource for accessibility."""
        try:
            # Determine if it's an internal or external link
            is_internal = self._is_internal_url(url, found_on_url)
            link_category = 'internal' if is_internal else 'external'
            
            logging.debug(f"Checking {link_category} {link_type}: {url}")
            
            # Use appropriate timeout
            timeout = self.config['crawling']['external_link_timeout']
            
            # Create session with appropriate headers
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (compatible; WebsiteHealthChecker/1.0)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            })
            
            response = session.get(url, timeout=timeout, allow_redirects=True)
            
            if response.status_code >= 400:
                broken_link = {
                    'url': url,
                    'status_code': response.status_code,
                    'reason': response.reason,
                    'found_on': found_on_url,
                    'link_type': link_category,
                    'resource_type': link_type,
                    'timestamp': datetime.now().isoformat()
                }
                self.broken_links.append(broken_link)
                
                # Choose appropriate icon
                icon = '🏠' if is_internal else '🔗'
                type_icon = {'image': '🖼️', 'document': '📄', 'css': '🎨', 'javascript': '⚡', 'media': '🎵'}.get(link_type, '')
                
                logging.info(f"{icon} {type_icon} {link_type.title()} broken: {url} (HTTP {response.status_code}) found on {found_on_url}")
            else:
                logging.debug(f"✅ {link_type.title()} OK: {url}")
                
        except requests.exceptions.Timeout:
            broken_link = {
                'url': url,
                'status_code': 'TIMEOUT',
                'reason': f'Request timeout after {timeout} seconds',
                'found_on': found_on_url,
                'link_type': link_category,
                'resource_type': link_type,
                'timestamp': datetime.now().isoformat()
            }
            self.broken_links.append(broken_link)
            logging.warning(f"🔗 {link_type.title()} timeout: {url} found on {found_on_url}")
            
        except requests.exceptions.ConnectionError:
            broken_link = {
                'url': url,
                'status_code': 'CONNECTION_ERROR',
                'reason': 'Connection failed',
                'found_on': found_on_url,
                'link_type': link_category,
                'resource_type': link_type,
                'timestamp': datetime.now().isoformat()
            }
            self.broken_links.append(broken_link)
            logging.warning(f"🔗 {link_type.title()} connection error: {url} found on {found_on_url}")
            
        except Exception as e:
            broken_link = {
                'url': url,
                'status_code': 'ERROR',
                'reason': str(e)[:100],
                'found_on': found_on_url,
                'link_type': link_category,
                'resource_type': link_type,
                'timestamp': datetime.now().isoformat()
            }
            self.broken_links.append(broken_link)
            logging.warning(f"🔗 {link_type.title()} error: {url} - {e}")
    
    def process_url(self, url: str) -> List[Dict]:
        """Process a single URL for spell checking and/or link checking."""
        try:
            logging.debug(f"Attempting to fetch: {url}")
            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                logging.debug(f"Successfully fetched {url} (Content-Length: {len(response.content)})")

                # Handle encoding issues
                response.encoding = response.apparent_encoding or 'utf-8'

                errors = []

                # Check links if enabled
                if self.enable_link_checking and self.config['crawling']['check_external_links']:
                    self._check_all_links_on_page(response.text, url)

                # Spell check if enabled
                if self.enable_spell_checking:
                    # Extract text
                    text = self.extract_text(response.text, url)

                    if text.strip():  # Only process if we got actual text
                        word_count = len(re.findall(r'\b\w+\b', text))
                        logging.debug(f"Extracted {len(text)} characters, {word_count} words from {url}")

                        # Perform spell checking
                        errors = self.spell_check_text(text, url)

                        self.stats['words_checked'] += word_count
                        self.stats['errors_found'] += len(errors)

                        logging.info(f"✅ Processed {url}: {len(errors)} spelling errors found, {word_count} words checked")
                    else:
                        logging.warning(f"❌ No text extracted from {url} - page may be empty or contain only non-text content")
                        self.stats['pages_failed'] += 1
                        return errors
                else:
                    # Not spell checking, just log that we processed the page for links
                    logging.info(f"✅ Processed {url} for link checking")

                self.stats['pages_processed'] += 1
                return errors
            else:
                logging.warning(f"❌ HTTP {response.status_code} for {url} - {response.reason}")

                # Track broken links if link checking is enabled
                if self.enable_link_checking:
                    broken_link = {
                        'url': url,
                        'status_code': response.status_code,
                        'reason': response.reason,
                        'found_on': 'Sitemap discovery',
                        'link_type': 'internal',
                        'timestamp': datetime.now().isoformat()
                    }
                    self.broken_links.append(broken_link)
                self.stats['pages_failed'] += 1
                
        except requests.exceptions.Timeout:
            logging.error(f"❌ Timeout error for {url} - page took longer than 30 seconds to load")
            self.stats['pages_failed'] += 1
        except requests.exceptions.ConnectionError as e:
            logging.error(f"❌ Connection error for {url}: {e}")
            self.stats['pages_failed'] += 1
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Request error for {url}: {e}")
            self.stats['pages_failed'] += 1
        except Exception as e:
            logging.error(f"❌ Unexpected error processing {url}: {type(e).__name__}: {e}")
            self.stats['pages_failed'] += 1
        
        return []
    
    def run(self, website_url: str):
        """Main execution method."""
        logging.info(f"Starting spell check for {website_url}")
        
        # Discover URLs
        urls = self.discover_urls(website_url)
        if not urls:
            logging.error("No URLs found to process")
            return
        
        # Limit number of pages if configured
        max_pages = self.config['website']['max_pages']
        if max_pages > 0:
            urls = set(list(urls)[:max_pages])
        
        # Process URLs
        max_workers = self.config['performance']['max_workers']
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_url = {executor.submit(self.process_url, url): url for url in urls}
            
            # Process results with progress bar
            for future in tqdm(as_completed(future_to_url), total=len(urls), desc="Processing pages"):
                url = future_to_url[future]
                try:
                    errors = future.result()
                    self.errors.extend(errors)
                except Exception as e:
                    logging.error(f"Error processing {url}: {e}")
        
        # Generate reports
        self._generate_reports()
        
        # Print summary
        self._print_summary()
    
    def _generate_reports(self):
        """Generate HTML and CSV reports."""
        os.makedirs(self.config['reporting']['output_dir'], exist_ok=True)
        
        if self.config['reporting']['html_report']:
            self._generate_html_report()
        
        if self.config['reporting']['csv_report']:
            self._generate_csv_report()
    
    def _generate_html_report(self):
        """Generate interactive HTML report."""
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
                <p>Comprehensive spell checking and broken link detection for your genealogy website</p>
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
                
                // Simple sorting functionality
                function sortTable(tableId, columnIndex) {
                    const table = document.getElementById(tableId);
                    const rows = Array.from(table.rows).slice(1);
                    
                    rows.sort((a, b) => {
                        const aVal = a.cells[columnIndex].textContent;
                        const bVal = b.cells[columnIndex].textContent;
                        return aVal.localeCompare(bVal);
                    });
                    
                    rows.forEach(row => table.appendChild(row));
                }
            </script>
        </body>
        </html>
        """
        
        # Generate spelling errors table
        error_rows = ""
        for error in self.errors:
            suggestions_text = ", ".join(error['suggestions'][:3]) if error['suggestions'] else "No suggestions"
            
            # Escape HTML content
            import html
            url_escaped = html.escape(error['url'])
            word_escaped = html.escape(error['word'])
            suggestions_escaped = html.escape(suggestions_text)
            context_escaped = html.escape(error['context'][:100])
            
            error_rows += f"""
                <tr>
                    <td><a href="{url_escaped}" class="url-link" target="_blank">{url_escaped}</a></td>
                    <td class="error-word">{word_escaped}</td>
                    <td class="suggestions">{suggestions_escaped}</td>
                    <td class="context">{context_escaped}...</td>
                    <td>{error['confidence']:.2f}</td>
                </tr>
            """
        
        # Generate broken links table
        broken_link_rows = ""
        for broken_link in self.broken_links:
            import html
            url_escaped = html.escape(broken_link['url'])
            reason_escaped = html.escape(broken_link['reason'])
            found_on_escaped = html.escape(broken_link.get('found_on', 'Unknown'))
            link_type = broken_link.get('link_type', 'unknown')
            resource_type = broken_link.get('resource_type', 'hyperlink')
            status_class = f"status-{broken_link['status_code']}" if str(broken_link['status_code']) in ['404', '500'] else ""
            
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
                    <td class="{status_class}">{broken_link['status_code']}</td>
                    <td>{reason_escaped}</td>
                    <td><a href="{html.escape(found_on_escaped)}" class="url-link" target="_blank">{found_on_escaped}</a></td>
                </tr>
            """
        
        # Build dynamic stats section
        stats_html = '<div class="stats">'
        stats_html += f'''
                <div class="stat-box">
                    <h3>{self.stats['pages_processed']}</h3>
                    <p>Pages Processed</p>
                </div>'''

        if self.enable_spell_checking:
            stats_html += f'''
                <div class="stat-box">
                    <h3>{self.stats['words_checked']:,}</h3>
                    <p>Words Checked</p>
                </div>
                <div class="stat-box">
                    <h3>{self.stats['errors_found']}</h3>
                    <p>Spelling Errors</p>
                </div>'''

        if self.enable_link_checking:
            stats_html += f'''
                <div class="stat-box">
                    <h3>{len(self.broken_links)}</h3>
                    <p>Broken Links</p>
                </div>'''

        stats_html += '</div>'

        # Build dynamic tabs section
        tabs_html = '<div class="tabs">'
        if self.enable_spell_checking:
            tabs_html += f'''
                <button class="tab active" onclick="showTab('spelling')">
                    📝 Spelling Errors <span class="spell-error-count">{self.stats['errors_found']}</span>
                </button>'''
        if self.enable_link_checking:
            active_class = "" if self.enable_spell_checking else "active"
            tabs_html += f'''
                <button class="tab {active_class}" onclick="showTab('broken-links')">
                    🔗 Broken Links <span class="broken-link-count">{len(self.broken_links)}</span>
                </button>'''
        tabs_html += '</div>'

        # Build spelling content section
        spelling_content = ""
        if self.enable_spell_checking:
            no_spelling_errors = "<p style='color: #28a745; font-style: italic;'>🎉 No spelling errors found! Your content looks great.</p>" if not self.errors else ""
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

        # Build broken links content section
        broken_links_content = ""
        if self.enable_link_checking:
            no_broken_links = "<p style='color: #28a745; font-style: italic;'>🎉 No broken links found! All pages are accessible.</p>" if not self.broken_links else ""
            active_class = "" if self.enable_spell_checking else "active"
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

        # Use string replacement instead of format to avoid issues with curly braces in content
        html_content = template.replace('{timestamp}', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        html_content = html_content.replace('{pages_processed}', str(self.stats['pages_processed']))
        html_content = html_content.replace('{stats_section}', stats_html)
        html_content = html_content.replace('{tabs_section}', tabs_html)
        html_content = html_content.replace('{spelling_content}', spelling_content)
        html_content = html_content.replace('{broken_links_content}', broken_links_content)
        html_content = html_content.replace('{error_rows}', error_rows)
        html_content = html_content.replace('{broken_link_rows}', broken_link_rows)
        
        output_path = os.path.join(self.config['reporting']['output_dir'], 'spell_check_report.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logging.info(f"HTML report generated: {output_path}")
    
    def _generate_csv_report(self):
        """Generate CSV reports for enabled features."""

        # Generate spelling errors CSV (only if spell checking is enabled)
        if self.enable_spell_checking:
            spelling_path = os.path.join(self.config['reporting']['output_dir'], 'spelling_errors.csv')
            with open(spelling_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['url', 'word', 'suggestions', 'context', 'confidence', 'timestamp']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for error in self.errors:
                    writer.writerow({
                        'url': error['url'],
                        'word': error['word'],
                        'suggestions': ', '.join(error['suggestions']),
                        'context': error['context'],
                        'confidence': error['confidence'],
                        'timestamp': error['timestamp']
                    })

            logging.info(f"Spelling errors CSV: {spelling_path}")

        # Generate broken links CSV (only if link checking is enabled)
        if self.enable_link_checking:
            broken_links_path = os.path.join(self.config['reporting']['output_dir'], 'broken_links.csv')
            with open(broken_links_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['url', 'status_code', 'reason', 'found_on', 'link_type', 'resource_type', 'timestamp']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for broken_link in self.broken_links:
                    writer.writerow({
                        'url': broken_link['url'],
                        'status_code': broken_link['status_code'],
                        'reason': broken_link['reason'],
                        'found_on': broken_link.get('found_on', 'Unknown'),
                        'link_type': broken_link.get('link_type', 'unknown'),
                        'resource_type': broken_link.get('resource_type', 'hyperlink'),
                        'timestamp': broken_link['timestamp']
                    })

            logging.info(f"Broken links CSV: {broken_links_path}")
    
    def _print_summary(self):
        """Print execution summary."""
        print("\n" + "="*50)
        print("WEBSITE HEALTH CHECK SUMMARY")
        print("="*50)

        # Feature status
        features = []
        if self.enable_spell_checking:
            features.append("Spell Checking")
        if self.enable_link_checking:
            features.append("Link Checking")
        print(f"Active features: {', '.join(features) if features else 'None'}")
        print()

        print(f"Pages processed: {self.stats['pages_processed']}")
        print(f"Pages failed: {self.stats['pages_failed']}")

        # Spell checking summary
        if self.enable_spell_checking:
            print(f"Words checked: {self.stats['words_checked']:,}")
            print(f"Spelling errors: {self.stats['errors_found']}")

        # Link checking summary
        if self.enable_link_checking:
            print(f"Broken links: {len(self.broken_links)}")

        # Broken links details (if link checking enabled)
        if self.enable_link_checking:
            if self.broken_links:
                print(f"\n🔗 BROKEN LINKS FOUND:")

                # Categorize by internal vs external
                internal_links = [bl for bl in self.broken_links if bl.get('link_type') == 'internal']
                external_links = [bl for bl in self.broken_links if bl.get('link_type') == 'external']

                print(f"  Internal links: {len(internal_links)}")
                print(f"  External links: {len(external_links)}")

                # Status code breakdown
                status_counts = defaultdict(int)
                for broken_link in self.broken_links:
                    status_counts[broken_link['status_code']] += 1

                print(f"\nStatus code breakdown:")
                # Sort by converting to string for consistent comparison
                for status_code, count in sorted(status_counts.items(), key=lambda x: str(x[0])):
                    print(f"  {status_code}: {count} links")

                print(f"\nFirst few broken links:")
                for broken_link in self.broken_links[:5]:  # Show first 5
                    link_type_icon = "🔗" if broken_link.get('link_type') == 'external' else "🏠"
                    print(f"  {link_type_icon} {broken_link['url']} ({broken_link['status_code']})")

                if len(self.broken_links) > 5:
                    print(f"  ... and {len(self.broken_links) - 5} more (see full report)")
            else:
                print("\n🎉 No broken links found!")

            # External link checking summary
            if self.config['crawling']['check_external_links']:
                print(f"\n🌐 EXTERNAL LINKS CHECKED: {len(self.external_links_checked)}")
            else:
                print(f"\n🌐 External link checking: DISABLED (enable in config.yaml)")

        # Spelling errors details (if spell checking enabled)
        if self.enable_spell_checking:
            if self.errors:
                print(f"\n📝 SPELLING ERRORS:")
                word_counts = defaultdict(int)
                for error in self.errors:
                    word_counts[error['word_lower']] += 1

                print("Top misspelled words:")
                for word, count in sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"  {word}: {count} times")
            else:
                print("\n🎉 No spelling errors found!")

        # Reports generated
        print(f"\n📊 REPORTS GENERATED:")
        print(f"  - HTML Report: reports/spell_check_report.html")
        if self.enable_spell_checking:
            print(f"  - Spelling CSV: reports/spelling_errors.csv")
        if self.enable_link_checking:
            print(f"  - Broken Links CSV: reports/broken_links.csv")


def main():
    """Command line interface."""
    parser = argparse.ArgumentParser(description="Website Health Checker - Spell checking and link validation")
    parser.add_argument("url", help="Website URL to check")
    parser.add_argument("-c", "--config", default="config.yaml", help="Configuration file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--spell-check", dest="spell_check", action="store_true", default=None,
                        help="Enable spell checking (overrides config)")
    parser.add_argument("--no-spell-check", dest="spell_check", action="store_false",
                        help="Disable spell checking (overrides config)")
    parser.add_argument("--link-check", dest="link_check", action="store_true", default=None,
                        help="Enable link checking (overrides config)")
    parser.add_argument("--no-link-check", dest="link_check", action="store_false",
                        help="Disable link checking (overrides config)")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create and run spell checker
    checker = WebsiteSpellChecker(args.config, enable_spell_checking=args.spell_check, enable_link_checking=args.link_check)
    checker.run(args.url)


if __name__ == "__main__":
    main()