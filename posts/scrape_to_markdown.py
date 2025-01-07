from playwright.sync_api import sync_playwright
from markdownify import markdownify as md
from pathlib import Path

urls = """
https://inspirehep.net/literature/1889335
https://inspirehep.net/literature/2512593
https://inspirehep.net/literature/2017107
https://inspirehep.net/literature/2687746
https://inspirehep.net/literature/1928162
"""

urls = [x.strip() for x in urls.split("\n") if x and not x.isspace()]


def scrape_to_markdown(urls, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    with sync_playwright() as p:
        # Launch a headless browser
        browser = p.chromium.launch(headless=True)

        for url in urls:
            output_fn = (
                url.replace("://", "_").replace("/", "_").replace(".", "_") + ".md"
            )
            ofile = output_dir / output_fn
            page = browser.new_page()

            # Navigate to the page
            page.goto(url)

            # Wait for JavaScript-rendered content to load
            # (Adjust the selector or timeout as needed for your specific page)
            page.wait_for_load_state(
                "networkidle"
            )  # Wait for network requests to finish

            # Get the rendered HTML content
            rendered_html = page.content()

            page.close()

            # Convert HTML to Markdown
            markdown_content = md(rendered_html)

            # Save the Markdown to a file
            with open(ofile, "w", encoding="utf-8") as file:
                file.write(markdown_content)

            print(f"Saved {ofile!r}")

        # Close the browser
        browser.close()


scrape_to_markdown(urls, "scraped")
