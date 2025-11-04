#!/usr/bin/env python3

import requests

def test_image_links():
    """Test if the image links are actually broken."""
    
    image_links = [
        "https://wordpress-810691-5571285.cloudwaysapps.com/wp-content/uploads/2025/05/Tier_15-scaled.jpg",
        "https://wordpress-810691-5571285.cloudwaysapps.com/wp-content/uploads/2025/05/Tier_17-scaled.jpg", 
        "https://wordpress-810691-5571285.cloudwaysapps.com/wp-content/uploads/2025/05/Tier20-scaled.jpg"
    ]
    
    for link in image_links:
        try:
            response = requests.head(link, timeout=10, allow_redirects=True)
            print(f"Status {response.status_code}: {link}")
            if response.status_code != 200:
                print(f"  ❌ BROKEN LINK!")
            else:
                print(f"  ✅ Link is working")
        except Exception as e:
            print(f"ERROR: {link}")
            print(f"  ❌ {str(e)}")

if __name__ == "__main__":
    test_image_links()