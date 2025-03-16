import time
import random
import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright

def extract_content_from_page(page):
    # Lấy tiêu đề
    title = page.query_selector("div.h3-bold-detail").inner_text() if page.query_selector("div.h3-bold-detail") else "No title found"
    title_safe = "".join(x for x in title if x.isalnum() or x in "._- ")  # Tạo tên tệp an toàn

    # Lấy nội dung
    content = page.query_selector("div.content").inner_text() if page.query_selector("div.content") else "No content found"

    # Lấy ảnh
    image_url = page.query_selector("img.image-news").get_attribute("src") if page.query_selector("img.image-news") else None

    # Lấy audio
    audio_url = page.query_selector("audio source").get_attribute("src") if page.query_selector("audio source") else None

    return {
        "title": title_safe,
        "content": content,
        "image_url": image_url,
        "audio_url": audio_url
    }

def download_file(url, base_url, folder, filename):
    if url:
        # Kiểm tra nếu URL là đường dẫn tương đối
        if not url.startswith("http"):
            url = base_url.rstrip("/") + "/" + url.lstrip("/")
        
        response = requests.get(url)
        if response.status_code == 200:
            with open(os.path.join(folder, filename), 'wb') as f:
                f.write(response.content)

with sync_playwright() as p:
    BASE_URL = "https://german.todainews.com/"
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://german.todainews.com/news?hl=en")

    # Đợi trang tải dữ liệu
    page.wait_for_timeout(5000)

    # Lấy danh sách bài viết
    articles = page.locator("a.news-item").all()
    article_links = [article.get_attribute("href") for article in articles]

    # Lấy danh sách cấp bậc của các bài viết
    level_post_all = page.query_selector_all("div.level-mini")
    levels = [level.inner_text() for level in level_post_all]

    print("Level: ", levels)
    article_links_full = []
    for link in article_links:
        full_link = BASE_URL.rstrip("/") + link
        article_links_full.append(full_link)

    print("Danh sách link bài viết:", article_links_full)

    # Tạo thư mục để lưu ảnh và audio
    os.makedirs("media", exist_ok=True)

    # Lưu nội dung vào danh sách
    contents = []

    # Sử dụng ThreadPoolExecutor để tải tệp song song
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {}
        for link in article_links_full:
            page.goto(link)
            page.wait_for_timeout(5000)

            # Lấy nội dung từ trang chi tiết
            data = extract_content_from_page(page)
            contents.append(data)
            print(f"Nội dung từ {link}:")
            print(data)
            print("=" * 50)

            # Gửi các tác vụ tải tệp
            if data['image_url']:
                future_to_url[executor.submit(download_file, data['image_url'], BASE_URL, "media", f"{data['title']}_image.jpg")] = data['image_url']
            if data['audio_url']:
                future_to_url[executor.submit(download_file, data['audio_url'], BASE_URL, "media", f"{data['title']}_audio.mp3")] = data['audio_url']

        # Chờ các tác vụ hoàn thành
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                future.result()
                print(f"Tải thành công: {url}")
            except Exception as exc:
                print(f"Tải thất bại {url}: {exc}")

    # Lưu nội dung vào tệp
    with open("contents.txt", "w", encoding="utf-8") as f:
        for i, data in enumerate(contents):
            f.write(f"Title: {data['title']}\n")
            f.write(f"Content: {data['content']}\n")
            f.write(f"Level: {levels[i]}\n")
            f.write(f"Image: {data['image_url']}\n")
            f.write(f"Audio: {data['audio_url']}\n")
            f.write("\n\n")

    browser.close()
