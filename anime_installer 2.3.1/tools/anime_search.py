from playwright.sync_api import sync_playwright
from rich import print
import time

from tools.subtools.downlowd import anime_download_prepare


def search_anime(page, browser, context):
    try:
        print(' ')
        anime_name = input("Enter the anime name: ")

        search_input_selector = "input[name='q'][class='input-search'][type='text'][placeholder='Search']"
        page.wait_for_selector(search_input_selector, timeout=900000)
        print(' ')
        print(f"Trying to search for {anime_name}.")
        print(' ')

        page.type(search_input_selector, anime_name, delay=200)
        print(f"Typed '{anime_name}' into search field.")
        print(' ')

        results_selector = ".search-results li"
        page.wait_for_selector(results_selector, timeout=900000)
        print("Search results dropdown loaded.")
        print(' ')

        result_items = page.query_selector_all(results_selector)
        if result_items:
            print("[bold green]Found the following search results:[/]")
            for index, item in enumerate(result_items):
                text_content = item.inner_text().strip()
                print(' ')
                print(f"[yellow][+][/] Index {index}: {text_content}")
                print(' ')

            # طلب اختيار الـ index من المستخدم
            while True:
                try:
                    print(' ')
                    chosen_index = int(input("Enter the index of the anime you want to visit (or -1 to exit): "))
                    if chosen_index == -1:
                        print("[blue]Exiting selection.[/]")
                        return None
                    if 0 <= chosen_index < len(result_items):
                        break
                    else:
                        print(f"[red]Invalid index. Please enter a number between 0 and {len(result_items) - 1}.[/]")
                except ValueError:
                    print("[red]Please enter a valid number.[/]")

            # استخراج الرابط من الـ <a> داخل الـ <li> المختار
            selected_item = result_items[chosen_index]
            link_element = selected_item.query_selector("a")
            if link_element:
                href = link_element.get_attribute("href")
                full_url = f"https://animepahe.ru{href}" if href.startswith("/") else href
                print(f"[green]Selected URL: {full_url}[/]")

                # فتح الرابط في علامة تبويب جديدة
                new_page = context.new_page()
                time.sleep(1)
                new_page.goto(full_url, wait_until="domcontentloaded")
                print(f"[green]Opened {full_url} in a new tab.[/]")

                # استدعاء الدالة المعدلة مع تمرير context
                episode_page, download_page, final_download_page = anime_download_prepare(new_page, context)
                new_pages = [new_page]
                if episode_page:
                    new_pages.append(episode_page)
                if download_page:
                    new_pages.append(download_page)
                if final_download_page:
                    new_pages.append(final_download_page)
                return new_pages

            else:
                print("[red]No link found in the selected result.[/]")
                return None

        else:
            print("[red]No search results found.[/]")
            return None

    except TimeoutError as te:
        print(f"[red]Timeout error: {te}. Element not found within the specified time.[/]")
        return None
    except Exception as e:
        print(f"[red]An unexpected error occurred in search_anime: {e}[/]")
        return None