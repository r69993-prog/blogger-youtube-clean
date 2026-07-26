import os
import json
import time
import random
from datetime import datetime, timedelta
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

CONFIG_FILE = "config.json"
POSTED_VIDEOS_FILE = "posted_videos.json"
KEYWORD_STATE_FILE = "keyword_state.json"

def load_json_file(filepath, default_value):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default_value
    return default_value

def save_json_file(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[!] ไม่สามารถบันทึกไฟล์ {filepath}: {str(e)}")

def get_posted_video_ids():
    return set(load_json_file(POSTED_VIDEOS_FILE, []))

def save_posted_video_id(video_id):
    posted = get_posted_video_ids()
    posted.add(video_id)
    save_json_file(POSTED_VIDEOS_FILE, list(posted))

def get_next_keyword(blog_id, keywords):
    if not keywords:
        return ""
    state = load_json_file(KEYWORD_STATE_FILE, {})
    current_index = state.get(blog_id, 0)
    selected_keyword = keywords[current_index % len(keywords)]
    state[blog_id] = (current_index + 1) % len(keywords)
    save_json_file(KEYWORD_STATE_FILE, state)
    return selected_keyword

def get_blogger_service():
    client_id = os.environ.get("BLOGGER_CLIENT_ID")
    client_secret = os.environ.get("BLOGGER_CLIENT_SECRET")
    refresh_token = os.environ.get("BLOGGER_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("[x] Error: ไม่พบข้อมูล Credentials ของ Blogger ใน Environment Variables")
        return None

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )

    if creds.expired or not creds.valid:
        print("Token expired. Refreshing token...")
        creds.refresh(Request())
        print("Token refreshed and saved successfully.")

    return googleapiclient.discovery.build("blogger", "v3", credentials=creds)

def search_youtube_videos(keyword, api_keys, exhausted_keys, max_results=2):
    for key in api_keys:
        if key in exhausted_keys:
            continue
        try:
            youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=key)
            request = youtube.search().list(
                q=keyword,
                part="snippet",
                type="video",
                maxResults=max_results,
                order="date"
            )
            response = request.execute()
            return response.get("items", []), key
        except googleapiclient.errors.HttpError as e:
            if e.resp.status in [400, 403]:
                print(f"[!] API Key โควตาเต็ม บันทึกจำเพื่อข้าม Key นี้ในรอบปัจจุบัน...")
                exhausted_keys.add(key)
            else:
                print(f"[!] เกิดข้อผิดพลาดกับ API Key: {str(e)}")
        except Exception as e:
            print(f"[!] เกิดข้อผิดพลาดทั่วไปในการค้นหา YouTube: {str(e)}")

    print(f"[x] ทุก API Key เต็มหมดแล้ว ไม่สามารถใช้งานคีย์เวิร์ด: {keyword}")
    return None, None

def is_video_already_posted(blogger_service, blog_id, video_id):
    if video_id in get_posted_video_ids():
        return True
    try:
        posts = blogger_service.posts().list(blogId=blog_id, fetchBodies=False, maxResults=50).execute()
        items = posts.get("items", [])
        for post in items:
            if video_id in post.get("title", "") or video_id in post.get("url", ""):
                save_posted_video_id(video_id)
                return True
        return False
    except Exception:
        return False

def create_blogger_post(blogger_service, blog_id, title, content, labels, publish_time):
    body = {
        "kind": "blogger#post",
        "title": title,
        "content": content,
        "labels": labels,
        "published": publish_time.isoformat() + "Z"
    }
    return blogger_service.posts().insert(blogId=blog_id, body=body, isDraft=False).execute()

def process_blog(blog_config, api_keys, exhausted_keys, blogger_service):
    blog_name = blog_config.get("blog_name", "")
    blog_id = blog_config.get("BLOG_ID", "")
    language = blog_config.get("language", "TH")
    seo_suffix = blog_config.get("seo_title_suffix", "")
    max_results = blog_config.get("max_results_per_run", 2)
    keywords = blog_config.get("youtube_search_keywords", [])
    base_labels = blog_config.get("blogger_labels", [])

    print(f"\n--- เริ่มต้นประมวลผลบล็อก: {blog_name} ({blog_id}) ---")

    keyword = get_next_keyword(blog_id, keywords)
    if not keyword:
        print(f"[!] ไม่พบคำค้นหาสำหรับบล็อก: {blog_name}")
        return

    print(f"กำลังค้นหาคำว่า: {keyword} สำหรับ {blog_name} (ใช้ API Key...)...")
    videos, used_key = search_youtube_videos(keyword, api_keys, exhausted_keys, max_results)

    if videos is None:
        return

    if not videos:
        print(f"ไม่พบวิดีโอจากคีย์เวิร์ดสำหรับบล็อก: {blog_name}")
        return

    print(f"พบวิดีโอจากการค้นหาสำหรับบล็อก {blog_name} ทั้งหมด {len(videos)} รายการ")

    posted_count = 0
    now = datetime.utcnow()

    for idx, item in enumerate(videos):
        video_id = item["id"]["videoId"]
        snippet = item["snippet"]
        raw_title = snippet["title"]
        description = snippet.get("description", "")

        if is_video_already_posted(blogger_service, blog_id, video_id):
            print(f"[-] ข้ามโพสต์ซ้ำ: {raw_title}")
            continue

        if language == "TH":
            post_title = f"เจาะลึกระบบ: {raw_title} {seo_suffix}".strip()
        else:
            post_title = f"Deep Dive: {raw_title} - Comprehensive Analysis of {seo_suffix}".strip()

        embed_html = f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe>'
        post_content = f"<h3>{post_title}</h3><p>{description}</p><br/>{embed_html}"

        labels = list(set(base_labels + [keyword]))
        publish_time = now + timedelta(minutes=(idx + 1) * 30)

        try:
            create_blogger_post(blogger_service, blog_id, post_title, post_content, labels, publish_time)
            save_posted_video_id(video_id)
            posted_count += 1
            print(f"[+] [{posted_count}] ตั้งเวลาสำเร็จบนบล็อก ({blog_name}): {post_title} | Labels: {labels}")
        except googleapiclient.errors.HttpError as e:
            if e.resp.status in [400, 403]:
                print(f"\n[!] โควตา Blogger API เต็มระบบหยุดทำงานอย่างปลอดภัยในบล็อกนี้")
                break
            else:
                print(f"[!] เกิดข้อผิดพลาดในการโพสต์ลง Blogger: {str(e)}")
        except Exception as e:
            print(f"[!] เกิดข้อผิดพลาดทั่วไปในการสร้างโพสต์: {str(e)}")

    print(f"เสร็จสิ้นการทำงานบล็อก: {blog_name} เพิ่มได้ {posted_count} บทความ")

def main():
    print("====================================")
    print(f"[!] เริ่มทำงานรอบอัตโนมัติ เวลา: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("====================================")

    if not os.path.exists(CONFIG_FILE):
        print(f"[x] Error: ไม่พบไฟล์ {CONFIG_FILE}")
        return

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    api_keys = config.get("YOUTUBE_API_KEYS", [])
    blogs = config.get("blogs", [])

    blogger_service = get_blogger_service()
    if not blogger_service:
        print("[x] ไม่สามารถเชื่อมต่อ Blogger API ได้")
        return

    exhausted_keys = set()

    for blog_config in blogs:
        process_blog(blog_config, api_keys, exhausted_keys, blogger_service)

    print("\n====================================")
    print("เสร็จสิ้นการทำงานระบบ Multi-Blog ทุกบล็อกประจำรอบนี้")
    print("====================================")

if __name__ == "__main__":
    main()