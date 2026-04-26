"""
Amazon Reviews Scraper API - Reliable review extraction for Amazon products.
Handles errors gracefully and returns structured JSON.
"""
import asyncio
import json
import re
from urllib.parse import urlparse, parse_qs

from apify import Actor
from apify.storages import KeyValueStore


async def main():
    """Main actor function."""
    actor_input = await Actor.get_input()
    
    if not actor_input:
        raise ValueError("No input provided. Need 'url' or 'asin'")
    
    url = actor_input.get("url", "")
    asin = actor_input.get("asin", "")
    max_reviews = actor_input.get("max_reviews", 10)
    
    # Get ASIN from URL if provided
    if url:
        asin = extract_asin(url) or asin
    
    if not asin:
        raise ValueError("Invalid ASIN or URL. Provide Amazon product URL or ASIN.")
    
    domain = actor_input.get("domain", "com")  # amazon.com, co.uk, de, etc.
    
    # Build Amazon Reviews URL
    reviews_url = f"https://www.amazon.{domain}/product-reviews/{asin}/"
    if actor_input.get("page", 1) > 1:
        reviews_url += f"ref=cm_cr_dp_view_show_more?ie=UTF8&pageNumber={actor_input.get('page', 1)}"
    
    # Scrape with Apify Playwright
    reviews = await scrape_reviews(reviews_url, max_reviews)
    
    # Output results
    await Actor.push_data(reviews)
    
    # Store metadata
    metadata = {
        "asin": asin,
        "domain": f"amazon.{domain}",
        "reviews_found": len(reviews),
        "success": True if reviews else False,
    }
    await Actor.set_value("metadata", metadata)


def extract_asin(url: str) -> str:
    """Extract ASIN from Amazon URL."""
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'/product/([A-Z0-9]{10})',
        r'^([A-Z0-9]{10})$',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return ""


async def scrape_reviews(url: str, max_reviews: int) -> list:
    """Scrape Amazon reviews using Playwright."""
    from playwright.async_api import async_playwright
    
    reviews = []
    
    # Get proxy if configured
    actor_input = await Actor.get_input()
    proxy = actor_input.get("proxy", {})
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy=proxy if proxy.get("use_apify_proxy") else None,
        )
        context = await browser.new_context(
            locale="en-US",
            viewport={"width": 1280, "height": 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        
        page = await context.new_page()
        
        try:
            # Navigate to reviews page
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # Wait for reviews to load
            await page.wait_for_selector('[data-hook="review"]', timeout=10000)
            
            # Scroll to load more reviews
            for _ in range(min(3, max_reviews // 10)):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)
            
            # Extract reviews
            review_elements = await page.query_selector_all('[data-hook="review"]')
            
            for el in review_elements[:max_reviews]:
                try:
                    review = await extract_review(el)
                    if review:
                        reviews.append(review)
                except Exception as e:
                    Actor.log(f"Error extracting review: {e}")
                    continue
                    
        except Exception as e:
            Actor.log(f"Error scraping: {e}")
            # Try alternative - may be blocked, try with JS disabled
            try:
                await page.goto(url, wait_until="load", timeout=15000)
                await asyncio.sleep(2)
                review_elements = await page.query_selector_all('[data-hook="review"]')
                
                for el in review_elements[:max_reviews]:
                    review = await extract_review(el)
                    if review:
                        reviews.append(review)
            except Exception as e2:
                Actor.log(f"Fallback also failed: {e2}")
        
        finally:
            await browser.close()
    
    return reviews


async def extract_review(el):
    """Extract single review data from element."""
    # Rating stars
    stars_el = await el.query_selector('[data-hook="review-star-rating"]')
    stars_text = await stars_el.inner_text() if stars_el else ""
    rating = 0
    star_match = re.search(r'([\d.]+)\s*out', stars_text)
    if star_match:
        rating = float(star_match.group(1))
    
    # Review title
    title_el = await el.query_selector('[data-hook="review-title"]')
    title = await title_el.inner_text() if title_el else ""
    
    # Review body
    body_el = await el.query_selector('[data-hook="review-body"]')
    body = await body_el.inner_text() if body_el else ""
    
    # Author
    author_el = await el.query_selector('.a-profile-name')
    author = await author_el.inner_text() if author_el else "Anonymous"
    
    # Date
    date_el = await el.query_selector('[data-hook="review-date"]')
    date_text = await date_el.inner_text() if date_el else ""
    
    # Verified purchase
    verified_el = await el.query_selector('[data-hook="avp"]')
    verified = await verified_el.inner_text() if verified_el else ""
    
    # Helpful votes
    helpful_el = await el.query_selector('[data-hook="review-voting"]')
    helpful_text = await helpful_el.inner_text() if helpful_el else ""
    helpful_match = re.search(r'(\d+)\s*people', helpful_text)
    helpful = int(helpful_match.group(1)) if helpful_match else 0
    
    return {
        "rating": rating,
        "title": title.strip(),
        "body": body.strip(),
        "author": author.strip(),
        "date": date_text.strip(),
        "verified_purchase": "Verified Purchase" in verified_text,
        "helpful_count": helpful,
    }


if __name__ == "__main__":
    asyncio.run(main())