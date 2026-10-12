"""Drive the compiled Flutter app against a real API in Chromium, without mocks.

Start API :5001 and static frontend :5173 first. Optionally set
PLAYWRIGHT_BROWSER_EXECUTABLE to an installed Chrome binary. In CI install
Chromium with `python -m playwright install --with-deps chromium`.
"""
import argparse
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


def wait_label(page, text):
    page.wait_for_function("""expected => document.body.innerText.includes(expected) ||
        Array.from(document.querySelectorAll('[aria-label]')).some(
            element => (element.getAttribute('aria-label') || '').includes(expected))""", arg=text)


def enable_accessibility(page):
    placeholder = page.locator('flt-semantics-placeholder')
    placeholder.wait_for(state='attached')
    placeholder.evaluate('(element) => element.click()')
    wait_label(page, 'Find my next trip')


def run(url, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        executable = os.getenv('PLAYWRIGHT_BROWSER_EXECUTABLE')
        browser = playwright.chromium.launch(headless=True, **({'executable_path': executable} if executable else {}))
        try:
            for width, height, name in [(1440, 1000, 'desktop'), (390, 844, 'mobile')]:
                page = browser.new_page(viewport={'width': width, 'height': height})
                page.set_default_timeout(30_000)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(url, wait_until='networkidle')
                enable_accessibility(page)
                assert 'TripGenie' in page.title()
                page.screenshot(path=str(output / f'{name}-discovery.png'))
                # Discovery search exercises frontend URL encoding and API filtering.
                search = page.get_by_role('textbox', name='Search destinations or experiences')
                search.click()
                expect(search).to_be_focused()
                # Allow Flutter's accessibility/native-editor focus handoff to settle.
                page.wait_for_timeout(300)
                page.keyboard.press('ControlOrMeta+A')
                page.keyboard.insert_text('Goa')
                with page.expect_response(lambda r: '/api/v1/destinations?' in r.url and 'q=Goa' in r.url) as pending:
                    page.keyboard.press('Enter')
                discovery = pending.value.json()
                assert pending.value.status == 200 and discovery['data']
                wait_label(page, f"Page 1 · {discovery['meta']['total']} destinations")
                page.get_by_role('button', name='Find my next trip', exact=True).click()
                budget = page.get_by_role('textbox', name='Daily budget (INR)')
                budget.click()
                expect(budget).to_be_focused()
                page.wait_for_timeout(300)
                page.keyboard.press('ControlOrMeta+A')
                page.keyboard.insert_text('3500')
                page.keyboard.press('Tab')
                page.wait_for_timeout(300)
                expect(budget).to_have_value('3500')
                with page.expect_response(lambda r: r.url.endswith('/api/v1/recommendations') and r.request.method == 'POST') as pending:
                    page.get_by_role('button', name='Find my destinations', exact=True).click()
                response = pending.value
                assert response.status == 200
                actual_budget = response.request.post_data_json['daily_budget']
                assert actual_budget == 3500, f'Edited budget was not transmitted: {actual_budget}'
                matches = response.json()['data']
                assert len(matches) == 5
                names = [row['destination']['name'].casefold() for row in matches]
                assert len(set(names)) == 5
                for row in matches:
                    assert abs(row['score'] - sum(component['contribution'] for component in row['breakdown'].values())) < 1e-9
                wait_label(page, 'Your destination shortlist.')
                page.get_by_role('button', name='Plan trip', exact=True).first.scroll_into_view_if_needed()
                page.screenshot(path=str(output / f'{name}-recommendations.png'))
                with page.expect_response(lambda r: r.url.endswith('/api/v1/itineraries') and r.request.method == 'POST') as pending:
                    page.get_by_role('button', name='Plan trip', exact=True).first.click()
                response = pending.value
                assert response.status == 200 and len(response.json()['data']['days']) == 3
                wait_label(page, 'DAY 1')
                snapshot = page.locator('body').aria_snapshot()
                assert 'A flexible starting point' in snapshot and 'DAY 1' in snapshot
                assert response.json()['data']['destination_name'] in snapshot
                page.screenshot(path=str(output / f'{name}-itinerary.png'))
                assert not errors, errors
                print(f'{name}: real discovery → personalized top five → three-day itinerary passed')
                page.close()
        finally:
            browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:5173')
    parser.add_argument('--output', default='artifacts/browser')
    args = parser.parse_args()
    run(args.url, args.output)
