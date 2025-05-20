from playwright.sync_api import sync_playwright
from rich import print
import re
import os
import time
import pathlib
import requests
from tqdm import tqdm

def anime_download_prepare(new_page, context):
    try:
        # الانتظار حتى يظهر قسم المحتوى
        content_selector = ".anime-content"
        new_page.wait_for_selector(content_selector, timeout=30000)
        print(' ')
        print("[bold green]Extracting Anime Content:[/]")

        # استخراج قسم الملخص والمعلومات
        detail_selector = ".tab-content.anime-detail"
        detail_content = new_page.query_selector(detail_selector)
        if detail_content:
            print(' ')
            print("[bold cyan]=== Summary and Information ===[/]")

            # استخراج الملخص
            synopsis = detail_content.query_selector(".anime-synopsis")
            if synopsis:
                print(' ')
                print("[yellow]Synopsis:[/]")
                print(synopsis.inner_text().strip())
                print(' ')

            # استخراج المعلومات
            info = detail_content.query_selector(".anime-info")
            if info:
                print("[yellow]Information:[/]")
                # استخراج كل فقرة <p> داخل anime-info
                info_paragraphs = info.query_selector_all("p")
                for p in info_paragraphs:
                    text = p.inner_text().strip()
                    if text:
                        print(f"  {text}")
                # استخراج الأنواع (Genres)
                genres = info.query_selector(".anime-genre")
                if genres:
                    genre_items = genres.query_selector_all("li")
                    genres_text = ", ".join([item.inner_text().strip() for item in genre_items])
                    print(f"  Genres: {genres_text}")
                print(' ')

        # استخراج عدد الحلقات
        episode_count_selector = ".episode-count"
        episode_count_element = new_page.query_selector(episode_count_selector)
        if episode_count_element:
            episode_count_text = episode_count_element.inner_text().strip()  # مثل "Episodes (11)"
            match = re.search(r'\((\d+)\)', episode_count_text)
            if match:
                total_episodes = int(match.group(1))
                print(f"[bold green]Total Episodes: {total_episodes}[/]")
            else:
                print("[red]Could not determine the total number of episodes.[/]")
                return None, None
        else:
            print("[red]Episode count element not found.[/]")
            return None, None

        # الانتظار حتى تظهر قائمة الحلقات
        episodes_selector = ".episode-wrap"
        new_page.wait_for_selector(episodes_selector, timeout=30000)

        # جلب جميع عناصر الحلقات
        episode_items = new_page.query_selector_all(episodes_selector)
        if not episode_items:
            print("[red]No episodes found.[/]")
            return None, None

        # طلب اختيار رقم الحلقة من المستخدم
        while True:
            try:
                print(' ')
                chosen_episode = int(input(f"Enter the episode number you want to select (1 to {total_episodes}, or -1 to exit): "))
                if chosen_episode == -1:
                    print("[blue]Exiting episode selection.[/]")
                    return None, None
                if 1 <= chosen_episode <= total_episodes:
                    break
                else:
                    print(f"[red]Invalid episode number. Please enter a number between 1 and {total_episodes}.[/]")
            except ValueError:
                print("[red]Please enter a valid number.[/]")

        # البحث عن الحلقة المختارة بناءً على رقم الحلقة
        selected_episode_link = None
        for episode in episode_items:
            episode_number_element = episode.query_selector(".episode-number")
            if episode_number_element:
                episode_number_text = episode_number_element.inner_text().strip()  # مثل "Episode 1"
                episode_number_text = episode_number_text.replace("Episode", "").strip()
                match = re.search(r'\d+', episode_number_text)
                if match:
                    episode_number = int(match.group(0))
                    if episode_number == chosen_episode:
                        watch_link_element = episode.query_selector("a.play")
                        if watch_link_element:
                            watch_link = watch_link_element.get_attribute("href")
                            full_watch_link = f"https://animepahe.ru{watch_link}" if watch_link.startswith("/") else watch_link
                            selected_episode_link = full_watch_link
                            break
                else:
                    print(f"[red]Could not extract episode number from text: {episode_number_text}[/]")
                    continue
            else:
                print("[red]Episode number element not found for an episode.[/]")
                continue

        # فتح رابط الحلقة في علامة تبويب جديدة
        episode_page = None
        if selected_episode_link:
            print(' ')
            print(f"[green]Opening Episode {chosen_episode} in a new tab: {selected_episode_link}[/]")
            episode_page = context.new_page()
            time.sleep(1)
            episode_page.goto(selected_episode_link, wait_until="domcontentloaded")
            print(f"[green]Successfully opened Episode {chosen_episode} page.[/]")
            print(' ')
        else:
            print(f"[red]Could not find the watch link for Episode {chosen_episode}.[/]")
            return None, None

        # دالة فرعية لاستخراج الجودات واختيار الجودة وفتح ر Hawkins
        def extract_and_select_quality(episode_page, context, episode_link, max_attempts=5):
            attempt = 1
            current_page = episode_page

            while attempt <= max_attempts:
                try:
                    # إعداد مراقبة الإعلانات المنبثقة
                    popups = []
                    def handle_popup(page):
                        popups.append(page)
                        print(f"[yellow]Detected a popup: {page.url}. Closing it...[/]")
                        page.close()

                    context.on("page", handle_popup)

                    # النقر على زر "Download" لإظهار القائمة المنسدلة
                    download_button_selector = "a#downloadMenu"
                    current_page.wait_for_selector(download_button_selector, timeout=30000)
                    current_page.click(download_button_selector)
                    print(f"[green]Attempt {attempt}: Clicked on Download button to show download options.[/]")

                    # إزالة المراقب بعد النقر
                    context.remove_listener("page", handle_popup)

                    # إغلاق أي إعلانات منبثقة تم اكتشافها
                    for popup in popups:
                        if not popup.is_closed():
                            popup.close()

                    # استخراج جودات التحميل من صفحة الحلقة
                    download_links_selector = ".dropdown-menu#pickDownload a.dropdown-item"
                    current_page.wait_for_selector(download_links_selector, timeout=30000, state="attached")
                    download_items = current_page.query_selector_all(download_links_selector)
                    
                    if not download_items:
                        print(f"[red]Attempt {attempt}: No download links found.[/]")
                        raise Exception("No download links found after clicking Download button.")

                    # تخزين الجودات وروابطها
                    quality_links = {}
                    available_qualities = set()
                    for item in download_items:
                        text = item.inner_text().strip()  # مثل "BoarHead · 1080p (196MB) BD eng"
                        link = item.get_attribute("href")  # مثل "https://pahe.win/IcqFI"
                        
                        # استخراج الجودة باستخدام تعبير منتظم
                        quality_match = re.search(r'(\d+p)', text)
                        if quality_match:
                            quality = quality_match.group(1)  # مثل "1080p"
                            available_qualities.add(quality)
                            quality_links[quality] = link

                    if not quality_links:
                        print(f"[red]Attempt {attempt}: Could not extract any download qualities.[/]")
                        raise Exception("No download qualities extracted.")

                    # عرض الجودات المتاحة
                    print(' ')
                    print("[bold green]Available Download Qualities:[/]")
                    for quality in available_qualities:
                        print(f"  - {quality}")
                    print(' ')

                    # طلب اختيار الجودة من المستخدم
                    while True:
                        chosen_quality = input("Enter the quality you want to download (e.g., 1080p, or -1 to exit): ").strip()
                        if chosen_quality == "-1":
                            print("[blue]Exiting quality selection.[/]")
                            return None
                        if chosen_quality in quality_links:
                            break
                        else:
                            print(f"[red]Invalid quality. Please choose one of: {', '.join(available_qualities)}[/]")

                    # فتح رابط التحميل في علامة تبويب جديدة (صفحة التحويل)
                    download_link = quality_links[chosen_quality]
                    print(' ')
                    print(f"[green]Opening download link for {chosen_quality} in a new tab: {download_link}[/]")
                    download_page = context.new_page()
                    time.sleep(1)
                    download_page.goto(download_link, wait_until="domcontentloaded")
                    print(f"[green]Successfully opened download page for {chosen_quality}.[/]")

                    # الانتظار 5 ثوانٍ للتأكد من ظهور زر "Continue"
                    print("[yellow]Waiting 5 seconds for the final download link to appear...[/]")
                    download_page.wait_for_timeout(5000)

                    # استخراج رابط التحميل النهائي من زر "Continue"
                    final_download_selector = "a.btn.btn-secondary.btn-block.redirect"
                    final_download_link = download_page.query_selector(final_download_selector)
                    if not final_download_link:
                        print("[red]Could not find the final download link (Continue button).[/]")
                        download_page.close()
                        return None

                    final_download_url = final_download_link.get_attribute("href")
                    if not final_download_url:
                        print("[red]Could not extract the final download URL from the Continue button.[/]")
                        download_page.close()
                        return None

                    # فتح رابط التحميل النهائي في علامة تبويب جديدة
                    print(f"[green]Opening final download link in a new tab: {final_download_url}[/]")
                    final_download_page = context.new_page()
                    time.sleep(1)
                    final_download_page.goto(final_download_url, wait_until="domcontentloaded")
                    print(f"[green]Successfully opened final download page.[/]")

                    # استخراج حجم الحلقة من زر التحميل
                    download_button_selector = "button.button.is-uppercase.is-success.is-fullwidth"
                    final_download_page.wait_for_selector(download_button_selector, timeout=30000)
                    size_text = final_download_page.query_selector(f"{download_button_selector} span").inner_text()
                    size_match = re.search(r'\(([\d\.]+ [KMG]B)\)', size_text)
                    if size_match:
                        file_size = size_match.group(1)
                        print(f"[bold green]Episode Size: {file_size}[/]")
                    else:
                        print("[red]Could not extract episode size.[/]")
                        file_size = None

                    # استخراج اسم الملف من العنوان
                    file_name = final_download_page.query_selector("h1.title").inner_text().strip()
                    print(f"[green]File Name: {file_name}[/]")

                    # استخراج رابط التحميل النهائي من النموذج
                    form_action = final_download_page.query_selector("form").get_attribute("action")
                    token = final_download_page.query_selector("input[name='_token']").get_attribute("value")
                    print(f"[green]Form Action URL: {form_action}[/]")
                    print(f"[green]Token: {token}[/]")

                    # إعداد مراقبة الإعلانات المنبثقة أثناء النقر على زر التحميل
                    popups = []
                    context.on("page", handle_popup)

                    # محاولة النقر على زر التحميل
                    print("[yellow]Clicking the download button to start downloading...[/]")
                    try:
                        with final_download_page.expect_download() as download_info:
                            final_download_page.click(download_button_selector)
                        download = download_info.value
                        download_path = pathlib.Path.home() / "Downloads"
                        print(f"[green]Downloading to: {download_path}/{file_name}[/]")
                        download.save_as(download_path / file_name)

                        # مراقبة تقدم التحميل
                        print("[yellow]Monitoring download progress...[/]")
                        file_path = download_path / file_name
                        total_size = float(re.search(r'([\d\.]+)', file_size).group(1)) * (1024 ** 2)  # تحويل MB إلى بايت
                        if "GB" in file_size:
                            total_size *= 1024  # تحويل GB إلى MB إذا لزم الأمر

                        while not file_path.exists():
                            time.sleep(1)

                        while True:
                            if file_path.exists():
                                current_size = file_path.stat().st_size
                                percentage = (current_size / total_size) * 100
                                print(f"[cyan]Download Progress: {percentage:.2f}%[/]")
                                if percentage >= 100:
                                    print("[bold green]Download Completed![/]")
                                    break
                            time.sleep(1)

                    except Exception as e:
                        print(f"[red]Failed to download using Playwright: {e}[/]")
                        print("[yellow]Attempting to download using requests...[/]")

                        # تحميل الملف يدويًا باستخدام requests
                        headers = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                            "Referer": final_download_url
                        }
                        data = {
                            "_token": token
                        }
                        response = requests.post(form_action, headers=headers, data=data, stream=True, allow_redirects=True)

                        # الحصول على الرابط النهائي بعد إعادة التوجيه
                        final_url = response.url
                        print(f"[green]Final Download URL: {final_url}[/]")

                        # تحميل الملف باستخدام requests مع شريط تقدم
                        download_path = pathlib.Path.home() / "Downloads" / file_name
                        total_size = int(response.headers.get('content-length', 0))
                        with open(download_path, 'wb') as f:
                            with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                                for chunk in response.iter_content(chunk_size=1024):
                                    if chunk:
                                        f.write(chunk)
                                        pbar.update(len(chunk))

                        print("[bold green]Download Completed![/]")

                    # إزالة المراقب بعد النقر
                    context.remove_listener("page", handle_popup)

                    # إغلاق أي إعلانات منبثقة تم اكتشافها
                    for popup in popups:
                        if not popup.is_closed():
                            popup.close()

                    print(' ')
                    return download_page, final_download_page

                except Exception as e:
                    if "net::ERR_SOCKET_NOT_CONNECTED" in str(e):
                        print(f"[red]Network error (net::ERR_SOCKET_NOT_CONNECTED) on attempt {attempt}.[/]")
                    else:
                        print(f"[red]Attempt {attempt} failed: {e}[/]")
                    attempt += 1
                    if attempt > max_attempts:
                        print(f"[red]Max attempts ({max_attempts}) reached. Could not extract download qualities.[/]")
                        return None

                    # إغلاق الصفحة الحالية وإعادة فتح الرابط في علامة تبويب جديدة
                    print(f"[yellow]Retrying in a new tab (Attempt {attempt}/{max_attempts})...[/]")
                    current_page.close()
                    current_page = context.new_page()
                    time.sleep(2)
                    current_page.goto(episode_link, wait_until="domcontentloaded")
                    print(f"[green]Reopened Episode {chosen_episode} page for retry.[/]")

            return None

        # استدعاء الدالة الفرعية لاستخراج الجودات وفتح رابط التحميل
        result = extract_and_select_quality(episode_page, context, selected_episode_link)
        if result is None:
            return episode_page, None
        download_page, final_download_page = result
        return episode_page, download_page, final_download_page

    except TimeoutError as te:
        print(f"[red]Timeout error while extracting anime content: {te}[/]")
        return None, None, None
    except Exception as e:
        print(f"[red]An unexpected error occurred while extracting anime content: {e}[/]")
        return None, None, None