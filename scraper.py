"""
Ekantipur Playwright scraper (single file).

- Top 5 articles from https://ekantipur.com/entertainment (title, url, image, author).
- Cartoon of the day: first slide on the homepage cartoon strip, plus author from the
  caption line on https://ekantipur.com/cartoon (homepage markup has no artist text).

Run: python scraper.py
"""

import json

from playwright.sync_api import Locator, sync_playwright


def _text(locator: Locator) -> str | None:
    if locator.count() == 0:
        return None
    raw = locator.first.text_content()
    if raw is None:
        return None
    s = raw.strip()
    return s or None


def _attr(locator: Locator, name: str) -> str | None:
    if locator.count() == 0:
        return None
    v = locator.first.get_attribute(name)
    return v if v else None


def _image_url(img: Locator) -> str | None:
    return _attr(img, "data-src") or _attr(img, "src")


def _parse_cartoon_description_line(line: str) -> tuple[str | None, str | None]:
    """Parse 'Title - Author' from cartoon listing caption."""
    if not line:
        return None, None
    parts = line.rsplit(" - ", 1)
    if len(parts) != 2:
        return line.strip() or None, None
    title_part, author_part = parts[0].strip(), parts[1].strip()
    return title_part or None, author_part or None


def scrape_ekantipur() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        data: dict = {
            "entertainment_news": [],
            "cartoon_of_the_day": {},
        }

        try:
            # --- Entertainment (listing uses div.category, not article.teaser) ---
            print("Navigating to Entertainment section...")
            page.goto("https://ekantipur.com/entertainment", wait_until="domcontentloaded")

            seen_urls: set[str] = set()
            for block in page.locator("div.category-inner-wrapper").all():
                if len(data["entertainment_news"]) >= 5:
                    break
                desc = block.locator("div.category-description")
                link = desc.locator("h2 a[href]")
                if link.count() == 0:
                    continue
                href = (link.first.get_attribute("href") or "").strip()
                if "/entertainment/" not in href:
                    continue
                if href in seen_urls:
                    continue
                seen_urls.add(href)

                title = _text(link)
                img = block.locator("div.category-image img")
                image_url = _image_url(img)
                author_el = desc.locator("div.author-name")
                author = _text(author_el)

                data["entertainment_news"].append(
                    {
                        "title": title,
                        "url": href if href.startswith("http") else f"https://ekantipur.com{href}",
                        "image_url": image_url,
                        "category": "मनोरञ्जन",
                        "author": author,
                    }
                )

            # --- Cartoon of the Day (homepage slider + author from /cartoon listing) ---
            print("Fetching Cartoon of the Day from homepage...")
            page.goto("https://ekantipur.com", wait_until="domcontentloaded")

            # Homepage labels this block as कार्टुन (h4); व्यंग्यचित्र may appear on other builds.
            cartoon_block = page.locator("div.section-news:has(.cartoon-slider)")
            if cartoon_block.count() == 0:
                cartoon_block = page.locator("section.e-section:has(.cartoon-slider)")

            cartoon_title: str | None = None
            cartoon_image: str | None = None

            if cartoon_block.count() > 0:
                slide = cartoon_block.locator(".swiper-slide.c-slide").first
                img = slide.locator("img")
                cartoon_title = _attr(img, "alt")
                cartoon_image = _image_url(img)

            cartoon_author: str | None = None
            listing_title: str | None = None

            # Author text is not in the homepage swiper; first caption on /cartoon matches the featured strip.
            print("Resolving cartoon author from cartoon listing...")
            page.goto("https://ekantipur.com/cartoon", wait_until="domcontentloaded")
            caption = page.locator("div.cartoon-wrapper").first.locator("div.cartoon-description p")
            caption_text = _text(caption)
            listing_title, cartoon_author = _parse_cartoon_description_line(caption_text or "")

            if not cartoon_title and listing_title:
                cartoon_title = listing_title

            if cartoon_title or cartoon_image or cartoon_author:
                data["cartoon_of_the_day"] = {
                    "title": cartoon_title,
                    "image_url": cartoon_image,
                    "author": cartoon_author,
                }

        except Exception as e:
            print(f"An error occurred: {e}")

        finally:
            with open("output.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print("Success! Data saved to output.json")
            browser.close()


run_scraper = scrape_ekantipur


if __name__ == "__main__":
    run_scraper()
