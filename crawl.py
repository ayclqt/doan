import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer

async def crawl_website(base_url, output_file):
    # Define the schema for product data extraction
    schema = {
        "name": "Product",
        "baseSelector": "article, .product-item, .item",  # Adjust based on website structure
        "fields": [
            {"name": "name", "selector": "h3, .product-name, .item-name", "type": "text"},
            {"name": "price", "selector": ".price, .product-price, .item-price", "type": "text"},
            {"name": "description", "selector": ".description, .product-desc", "type": "text"},
            {"name": "category", "selector": ".category, .breadcrumb", "type": "text"},
            {"name": "specifications", "selector": ".specs, .product-specs", "type": "text"},
            {"name": "image_urls", "selector": ".product-img img, .item-img img", "type": "attribute", "attribute": "src"},
            {"name": "product_url", "selector": "a", "type": "attribute", "attribute": "href"},
            {"name": "brand", "selector": ".brand, .manufacturer", "type": "text"},
            {"name": "availability", "selector": ".stock, .availability", "type": "text"},
            {"name": "ratings", "selector": ".rating, .star-rating", "type": "text"}
        ]
    }

    # Browser configuration: Enable JavaScript and headless mode
    browser_config = BrowserConfig(
        headless=True,
        java_script_enabled=True,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    # JavaScript to handle "Load More" buttons or pagination
    js_handle_pagination = """
    (async () => {
        const loadMoreButton = document.querySelector('.load-more, .next-page');
        if (loadMoreButton) {
            loadMoreButton.scrollIntoView();
            loadMoreButton.click();
            await new Promise(r => setTimeout(r, 1000));
        }
    })();
    """

    # Crawler configuration: Use deep crawling and extraction strategy
    crawler_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        extraction_strategy=JsonCssExtractionStrategy(schema),
        js_code=[js_handle_pagination]
    )

    scorer = KeywordRelevanceScorer(
        keywords=['dtdd', 'laptop', 'dien-thoai', 'may-tinh-xach-tay'],
        weight=0.7
    )
    # Initialize crawler
    async with AsyncWebCrawler(config=browser_config) as crawler:
        # Run deep crawl with DFS strategy
        strategy = BestFirstCrawlingStrategy(
            max_depth=2,
            include_external=False,
            max_pages=1000,
            url_scorer=scorer
        )
        result = await crawler.arun(
            url=base_url,
            config=crawler_config,
            strategy=strategy
        )

        # Save extracted data to JSON
        products = []
        for page_result in result:
            if page_result.success and page_result.extracted_content:
                extracted = json.loads(page_result.extracted_content)
                products.extend(extracted)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)

        print(f"Successfully crawled {base_url}. Saved {len(products)} products to {output_file}")

async def main():
    # Crawl Thế Giới Di Động (Smartphones category)
    await crawl_website(
        "https://www.thegioididong.com/dtdd",
        "tgdd_products.json"
    )
    # Crawl FPT Shop (Smartphones category)
    await crawl_website(
        "https://fptshop.com.vn/dien-thoai",
        "fptshop_products.json"
    )

# await main()
if __name__ == "__main__":
    asyncio.run(main())