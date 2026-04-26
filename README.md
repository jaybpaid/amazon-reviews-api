# Amazon Reviews API
- Scrapes product reviews from Amazon
- Handles blocking and returns structured JSON
- Multi-domain support (.com, .co.uk, .de, etc.)

## Input
- `url` - Full Amazon product reviews URL
- `asin` - Product ASIN (10 chars)
- `domain` - Amazon domain (com, co.uk, de, etc.)
- `max_reviews` - Number of reviews (1-100)

## Output
Returns JSON with:
- rating, title, body, author, date
- verified_purchase, helpful_count

## Why This Works Better
- Proper error handling for blocking
- Multiple domain support
- Works when other scrapers fail
- Structured data, not HTML

## Usage
```
curl -X POST https://api.apify.com/v2/acts/<actor-id>/run-sync \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"url": "https://www.amazon.com/product-reviews/B08N5WRWNW"}'
```