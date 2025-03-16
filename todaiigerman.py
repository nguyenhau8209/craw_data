import asyncio
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.async_api import async_playwright

async def extract_content_from_page(link):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(link)
        await page.wait_for_timeout(5000)

        # Lấy tiêu đề
        title = await page.query_selector("div.h3-bold-detail")
        title_text = await title.inner_text() if title else "No title found"
        title_safe = "".join(x for x in title_text if x.isalnum() or x in "._- ")  # Tạo tên tệp an toàn

        # Lấy nội dung
        content = await page.query_selector("div.content")
        content_text = await content.inner_text() if content else "No content found"

        # Lấy ảnh
        image = await page.query_selector("img.image-news")
        image_url = await image.get_attribute("src") if image else None

        # Lấy audio
        audio = await page.query_selector("audio source")
        audio_url = await audio.get_attribute("src") if audio else None

        await browser.close()  # Đóng trình duyệt sau khi sử dụng

        return {
            "title": title_safe,
            "content": content_text,
            "image_url": image_url,
            "audio_url": audio_url
        }

async def extract_video_info(link):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(link)
        await page.wait_for_timeout(5000)

        # Lấy thông tin video
        iframe = await page.query_selector("iframe")
        title_element = await page.query_selector("h3")  # Giả sử tiêu đề nằm trong thẻ h3
        level_element = await page.query_selector("div.level")
        video_link = await iframe.get_attribute("src") if iframe else None
        video_title = await title_element.inner_text() if title_element else "No title found"
        video_level = await level_element.inner_text() if level_element else "No level found"

        await browser.close()
        return (video_title, video_link, video_level)

async def get_video_links():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        # Điều hướng đến trang video
        await page.goto("https://german.todainews.com/video?hl=en")
        await page.wait_for_timeout(5000)

        # Lấy danh sách liên kết video
        video_links = []
        video_items = await page.locator("a.video-item").all()  # Giả sử mỗi video có một liên kết với class 'video-item'
        for item in video_items:
            link = await item.get_attribute("href")
            video_links.append(link)
            await asyncio.sleep(2)  # Thêm độ trễ giữa các yêu cầu

        await browser.close()
        return video_links

async def main():
    BASE_URL = "https://german.todainews.com/"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Lấy danh sách bài viết từ trang new
        await page.goto("https://german.todainews.com/news?hl=en")
        await page.wait_for_timeout(5000)
        articles = await page.locator("a.news-item").all()
        article_links = [await article.get_attribute("href") for article in articles]
        article_links_full = [BASE_URL.rstrip("/") + link for link in article_links]

        # Lấy danh sách liên kết video từ trang video
        video_links = await get_video_links()
        video_links_full = [BASE_URL.rstrip("/") + link for link in video_links]

        print("Danh sách link bài viết:", article_links_full)
        print("Danh sách link video:", video_links_full)

        # Tạo thư mục để lưu ảnh và audio
        os.makedirs("media", exist_ok=True)

        # Lưu nội dung vào danh sách
        contents = []

        # Sử dụng ThreadPoolExecutor để lấy nội dung song song
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_link = {executor.submit(asyncio.run, extract_content_from_page(link)): link for link in article_links_full}

            # Chờ các tác vụ hoàn thành
            for future in as_completed(future_to_link):
                link = future_to_link[future]
                try:
                    data = future.result()
                    contents.append(data)
                    print(f"Nội dung từ {link}:")
                    print(data)
                    print("=" * 50)
                except Exception as exc:
                    print(f"Lỗi khi lấy nội dung từ {link}: {exc}")

        # Lưu thông tin video vào danh sách
        video_contents = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_link = {executor.submit(asyncio.run, extract_video_info(link)): link for link in video_links_full}

            # Chờ các tác vụ hoàn thành
            for future in as_completed(future_to_link):
                link = future_to_link[future]
                try:
                    data = future.result()
                    video_contents.append(data)
                    print(f"Thông tin video từ {link}:")
                    print(data)
                    print("=" * 50)
                except Exception as exc:
                    print(f"Lỗi khi lấy thông tin video từ {link}: {exc}")

        # Lưu nội dung và video vào tệp
        with open("news_contents.txt", "w", encoding="utf-8") as f:
            for data in contents:
                f.write(f"Title: {data['title']}\n")
                f.write(f"Content: {data['content']}\n")
                f.write(f"Image: {data['image_url']}\n")
                f.write(f"Audio: {data['audio_url']}\n")
                f.write("\n\n")
        
        with open("video_links.txt", "w", encoding="utf-8") as f:
            for title, link, level in video_contents:
                f.write(f"Title: {title}\n")
                f.write(f"Link: {link}\n")
                f.write(f"Level: {level}\n\n")

        await browser.close()

# Chạy hàm main
asyncio.run(main())
