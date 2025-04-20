# element_mapper.py
import sys
import asyncio # Need asyncio for potential async context
from playwright.async_api import async_playwright # Use async version
from rich import print as rprint
from rich.table import Table

TARGETS = {
    "chatgpt": "https://chat.openai.com",
    "deepseek": "https://chat.deepseek.com"
}

async def extract_accessible_elements(page):
    el_types = {
        "button": "button",
        "input": "input",
        "textarea": "textarea",
        # Add other potentially relevant tags like links?
        # "link": "a"
    }

    table = Table(title=f"[bold green]Accessible Elements on {page.url}", show_lines=True)
    table.add_column("Tag")
    table.add_column("Role")
    table.add_column("Name (ARIA)") # Use Name for accessible name
    table.add_column("Label (ARIA)")
    table.add_column("Placeholder")
    table.add_column("Visible Text")
    table.add_column("Selector Hint") # Simplified representation

    for tag, sel in el_types.items():
        elements = await page.query_selector_all(sel)
        rprint(f"Found {len(elements)} <{tag}> elements.")
        for el in elements:
            try:
                # Check visibility first
                is_visible = await el.is_visible()
                if not is_visible:
                    continue # Skip hidden elements

                # Get attributes using evaluate for robustness
                role = await page.evaluate("(el) => el.getAttribute('role')", el) or "implicit"
                aria_label = await page.evaluate("(el) => el.getAttribute('aria-label')", el) or ""
                aria_labelledby = await page.evaluate("(el) => el.getAttribute('aria-labelledby')", el) or ""
                placeholder = await page.evaluate("(el) => el.getAttribute('placeholder')", el) or ""
                name_attr = await page.evaluate("(el) => el.getAttribute('name')", el) or ""
                id_attr = await page.evaluate("(el) => el.getAttribute('id')", el) or ""
                
                # Use Playwright's accessible name computation if possible (might require more complex setup)
                # For simplicity, we'll use aria-label or name attribute as a proxy for 'name'
                acc_name = aria_label or name_attr
                acc_label = aria_labelledby # Often references another element's ID

                text = await el.inner_text()
                text = text.strip().replace('\n', ' ')
                
                # Generate a hint for Playwright selectors
                selector_hint = f"<{tag}"
                if id_attr: selector_hint += f" id='{id_attr}'"
                if name_attr: selector_hint += f" name='{name_attr}'"
                if aria_label: selector_hint += f" aria-label='{aria_label}'"
                if placeholder: selector_hint += f" placeholder='{placeholder}'"
                if text and len(text) < 50: selector_hint += f" text='{text[:47]}...'"
                selector_hint += ">"

                table.add_row(
                    tag, 
                    role, 
                    acc_name, 
                    acc_label, 
                    placeholder, 
                    text if len(text) < 70 else text[:67]+'...', # Limit visible text length
                    selector_hint
                 )
            except Exception as e:
                rprint(f"[red]Error processing element {tag}: {e}")
                continue

    rprint(table)

async def main(target_url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        rprint(f"Navigating to {target_url}...")
        try:
            await page.goto(target_url, timeout=30_000, wait_until='networkidle')
            rprint(f"Page loaded. Waiting a bit for dynamic content...")
            await page.wait_for_timeout(3000) # Extra wait for potential dynamic loads
            rprint("Extracting elements...")
            await extract_accessible_elements(page)
        except Exception as e:
            rprint(f"[bold red]Error during navigation or extraction: {e}")
        finally:
            rprint("[yellow]Inspecting complete. Browser window remains open.")
            rprint("[yellow]Press Enter in this terminal when you are finished inspecting to close the browser.")
            await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline) # Wait for Enter key
            await browser.close()
            rprint("Browser closed.")

if __name__ == "__main__":
    service_name = sys.argv[1].lower() if len(sys.argv) > 1 else None
    target_url = TARGETS.get(service_name)

    if not target_url:
        # Corrected f-string formatting for rich tags
        usage_message = (
            f"[bold red]Usage:[/]\n"
            f"  python element_mapper.py [service]\n"
            f"Example:\n"
            f"  python element_mapper.py chatgpt\n"
            f"Available services: {', '.join(TARGETS.keys())}"
        )
        rprint(usage_message)
        sys.exit(1)

    asyncio.run(main(target_url)) 