#!/usr/bin/env python3

import requests
from bs4 import BeautifulSoup
import urllib.parse

def test_genealogy_page_links():
    """Test link extraction from the genealogy room page specifically."""
    
    url = "https://wordpress-810691-5571285.cloudwaysapps.com/about-us/genealogy-room/"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Extract links like the main script does
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
        
        # Convert relative URLs to absolute
        absolute_links = []
        for href, link_type in links_to_check:
            absolute_url = urllib.parse.urljoin(url, href)
            absolute_links.append((absolute_url, link_type))
        
        # Look for the specific broken image link
        target_link = "https://wordpress-810691-5571285.cloudwaysapps.com/wp-content/uploads/2025/05/Tier_15-scaled.jpg"
        
        found_target = False
        image_links = []
        
        for link_url, link_type in absolute_links:
            if link_type == 'image':
                image_links.append(link_url)
                if target_link in link_url:
                    found_target = True
                    print(f"✅ Found target image link: {link_url}")
        
        print(f"\nTotal image links found in <a href> tags: {len(image_links)}")
        for img_link in image_links:
            print(f"  - {img_link}")
        
        if found_target:
            print(f"\n✅ SUCCESS: The target broken image link was detected!")
        else:
            print(f"\n❌ PROBLEM: Target link {target_link} was not found")
            print("Let me check if it exists in the HTML source...")
            
            if target_link in response.text:
                print("✅ Link exists in HTML source")
            else:
                print("❌ Link not found in HTML source at all")
        
        return found_target
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_genealogy_page_links()