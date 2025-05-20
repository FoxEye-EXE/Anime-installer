from playwright.sync_api import sync_playwright
from rich import print


from tools.anime_search import search_anime
from tools.help_tool import get_help
from tools.subtools.opning import get_open

if __name__ == "__main__":

    get_open()
    print(' ')
    print('+==============================================================================================+')


    print(' ')
    print(' ')
    print(' ')
    print('   [yellow]input start to stert program or help to see the how to use the program or out to end the program[/]')
    print(' ')
    
    while True:
        print(' ')
        xx = input('   Start/help/out:  ')
        user_in = xx.lower()
        print(' ')

        if user_in == 'help':
            get_help()

        if user_in == 'out':
            break

        if user_in == 'start':
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    )
                    page = context.new_page()

                    # الانتقال إلى الموقع
                    page.goto("https://animepahe.ru/", timeout=900000, wait_until="domcontentloaded")
                    print(' ')
                    print("[green]Page loaded successfully.[/]")

                    # استدعاء دالة البحث
                    result = search_anime(page, browser, context)
                    if result:
                        print(' ')
                        input("Press Enter to close the browser...")

            except Exception as e:
                print(f"[red]Failed to load page or perform search: {e}[/]")

            finally:
                # إغلاق الموارد بشكل صحيح
                try:
                    if page:
                        page.close()
                    if context:
                        context.close()
                    if browser:
                        browser.close()
                    print("[blue]Browser closed.[/]")
                except Exception as e:
                    print(f"[red]Error while closing resources: {e}[/]")

        print(' ')