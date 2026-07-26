import os
import json
import urllib.parse
import urllib.request
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Configuration
YOUTUBE_API_KEYS = [
    os.getenv("YOUTUBE_API_KEY_1"),
    os.getenv("YOUTUBE_API_KEY_2"),
    os.getenv("YOUTUBE_API_KEY_3"),
    os.getenv("YOUTUBE_API_KEY_4"),
    os.getenv("YOUTUBE_API_KEY_5")
]
YOUTUBE_API_KEYS = [k for k in YOUTUBE_API_KEYS if k]

BLOGGER_CLIENT_ID = os.getenv("BLOGGER_CLIENT_ID")
BLOGGER_CLIENT_SECRET = os.getenv("BLOGGER_CLIENT_SECRET")
BLOGGER_REFRESH_TOKEN = os.getenv("BLOGGER_REFRESH_TOKEN")

POSTED_VIDEOS_FILE = "posted_videos.json"
KEYWORD_STATE_FILE = "keyword_state.json"

BLOG_CONFIGS = [
    {
        "blog_id": "7261621395427988771",
        "name": "ระบบกลไก",
        "keywords": ["Mechanism design", "Mechanical movement", "Linkage mechanism"],
        "labels": ["Gadget", "Tech", "Mechanism", "Engineering"],
        "lang": "th"
    },
    {
        "blog_id": "6321192511447492789",
        "name": "Industrial (English)",
        "keywords": ["industrial machinery", "factory automation", "manufacturing process"],
        "labels": ["Video", "Engineering", "Machinery", "Industrial"],
        "lang": "en"
    },
    {
        "blog_id": "7707792750976542809",
        "name": "Machine & Mechanical Design (ใหม่)",
        "keywords": ["machine design", "cad mechanical design", "mechanical engineering design"],
        "labels": ["Design", "Video", "Mechanical", "Machine"],
        "lang": "th"
    },
    {
        "blog_id": "2962551177226991802",
        "name": "Knowledge Engineering (ใหม่)",
        "keywords": ["knowledge Engineering", "engineering knowledge", "systems engineering"],
        "labels": ["Video", "Engineering", "Knowledge", "Systems"],
        "lang": "th"
    },
    {
        "blog_id": "2882579450350054162",
        "name": "CNC Machine Center (ใหม่)",
        "keywords": ["CNC", "CNC milling", "CNC machining center"],
        "labels": ["Video", "CNC", "Machining", "Milling"],
        "lang": "th"
    }
]


def load_json_file(filepath, default_value):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] Warning: อ่านไฟล์ {filepath} ไม่สำเร็จ ({e}) ใช้ค่าเริ่มต้น")
    return default_value


def save_json_file(filepath, data):
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[!] Error: ไม่สามารถบันทึกไฟล์ {filepath} ได้ ({e})")


def get_blogger_service():
    if not (BLOGGER_CLIENT_ID and BLOGGER_CLIENT_SECRET and BLOGGER_REFRESH_TOKEN):
        print("[x] Error: ไม่พบข้อมูล Credentials ของ Blogger ใน Environment Variables")
        return None

    try:
        creds = Credentials(
            token=None,
            refresh_token=BLOGGER_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=BLOGGER_CLIENT_ID,
            client_secret=BLOGGER_CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/blogger"]
        )
        creds.refresh(Request())
        return build("blogger", "v3", credentials=creds)
    except Exception as e:
        print(f"[x] ไม่สามารถเชื่อมต่อ Blogger API ได้: {e}")
        return None


def search_youtube_videos(query, api_key, max_results=10):
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={urllib.parse.quote(query)}&type=video&maxResults={max_results}&key={api_key}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get('items', [])
    except Exception as e:
        print(f"[!] YouTube Search API Error ({api_key[:10]}...): {e}")
        return []


def generate_post_content(title, video_id, description, keyword, blog_name, lang="th"):
    thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
    fallback_thumb = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    clean_desc = description.replace("\n", "<br>") if description else "รายละเอียดวิดีโอเทคโนโลยีและการออกแบบทางวิศวกรรม"
    
    if lang == "en":
        overview_header = "📌 Overview & Technical Breakdown"
        keyword_badge = f"Key Topic: {keyword}"
        blog_badge = f"Category: {blog_name}"
        share_text = "Share this content:"
    else:
        overview_header = "📌 รายละเอียดและวิเคราะห์เจาะลึก (Overview)"
        keyword_badge = f"หัวข้อหลัก: {keyword}"
        blog_badge = f"หมวดหมู่บล็อก: {blog_name}"
        share_text = "แชร์เนื้อหานี้:"

    html_content = f"""
<div style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.8; color: #2c3e50; max-width: 850px; margin: 0 auto; padding: 25px; border: 1px solid #e1e8ed; border-radius: 12px; background-color: #ffffff; box-shadow: 0 6px 18px rgba(0,0,0,0.06);">
  <h1 style="color: #1a73e8; font-size: 26px; border-bottom: 3px solid #1a73e8; padding-bottom: 12px; margin-top: 0;">{title}</h1>
  
  <div style="text-align: center; margin: 20px 0;">
    <img src="{thumbnail_url}" onerror="this.onerror=null;this.src='{fallback_thumb}';" alt="{title} - {keyword}" style="width: 100%; max-height: 480px; object-fit: cover; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);" />
  </div>

  <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; background: #000000; border-radius: 10px; margin: 25px 0;">
    <iframe src="https://www.youtube.com/embed/{video_id}" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border-radius: 10px;"></iframe>
  </div>

  <div style="background-color: #f8f9fa; border-left: 5px solid #1a73e8; padding: 18px 22px; margin: 25px 0; border-radius: 0 10px 10px 0;">
    <h3 style="margin-top: 0; color: #1a252f; font-size: 20px;">{overview_header}</h3>
    <p style="color: #4a5568; font-size: 15px; margin-bottom: 0;">{clean_desc}</p>
  </div>

  <div style="display: flex; flex-wrap: wrap; gap: 10px; margin-top: 30px; justify-content: space-between; align-items: center; background-color: #e8f0fe; padding: 15px 20px; border-radius: 8px;">
    <span style="color: #1967d2; font-weight: bold; font-size: 14px;">🏷️ {keyword_badge}</span>
    <span style="color: #1a73e8; font-weight: bold; font-size: 14px;">📁 {blog_badge}</span>
  </div>
</div>
"""
    return html_content


def main():
    print("====================================")
    print(f"[!] เริ่มทำงานรอบอัตโนมัติ เวลา: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("====================================")

    if not YOUTUBE_API_KEYS:
        print("[x] Error: ไม่พบ YOUTUBE_API_KEY ใน Environment Variables")
        return

    blogger_service = get_blogger_service()
    if not blogger_service:
        return

    posted_videos = load_json_file(POSTED_VIDEOS_FILE, [])
    keyword_state = load_json_file(KEYWORD_STATE_FILE, {})

    api_key_index = 0
    current_api_key = YOUTUBE_API_KEYS[api_key_index]

    for config in BLOG_CONFIGS:
        blog_id = config["blog_id"]
        blog_name = config["name"]
        keywords = config["keywords"]
        labels = config["labels"][:4]
        lang = config.get("lang", "th")

        print(f"\n--- เริ่มต้นประมวลผลบล็อก: {blog_name} ({blog_id}) ---")

        kw_index = keyword_state.get(blog_id, 0) % len(keywords)
        current_keyword = keywords[kw_index]
        keyword_state[blog_id] = kw_index + 1

        print(f"กำลังค้นหาคำว่า: {current_keyword} สำหรับ {blog_name}...")

        videos = search_youtube_videos(current_keyword, current_api_key, max_results=10)

        if not videos and len(YOUTUBE_API_KEYS) > 1:
            api_key_index = (api_key_index + 1) % len(YOUTUBE_API_KEYS)
            current_api_key = YOUTUBE_API_KEYS[api_key_index]
            print(f"[!] สลับไปใช้ YouTube API Key สำรองลำดับที่ {api_key_index + 1}")
            videos = search_youtube_videos(current_keyword, current_api_key, max_results=10)

        print(f"พบวิดีโอจากการค้นหาสำหรับบล็อก {blog_name} ทั้งหมด {len(videos)} รายการ")

        added_count = 0
        for item in videos:
            if added_count >= 2:
                break

            video_id = item.get("id", {}).get("videoId")
            if not video_id:
                continue

            # ป้องกันคลิปซ้ำ 100%
            if video_id in posted_videos:
                print(f"[-] ข้ามวิดีโอซ้ำ (ID: {video_id})")
                continue

            snippet = item.get("snippet", {})
            title = snippet.get("title", "No Title")
            description = snippet.get("description", "")

            post_body = {
                "kind": "blogger#post",
                "blog": {"id": blog_id},
                "title": title,
                "content": generate_post_content(title, video_id, description, current_keyword, blog_name, lang),
                "labels": labels
            }

            try:
                posted_post = blogger_service.posts().insert(blogId=blog_id, body=post_body, isDraft=False).execute()
                posted_videos.append(video_id)
                added_count += 1
                print(f"[+] [{added_count}] โพสต์สำเร็จบนบล็อก ({blog_name}): {title} | ID: {posted_post.get('id')}")
            except Exception as e:
                print(f"[!] เกิดข้อผิดพลาดในการโพสต์ลง Blogger: {e}")
                if "rateLimitExceeded" in str(e) or "quota" in str(e).lower():
                    print("[!] Blogger API Quota เต็ม ข้ามไปประมวลผลขั้นตอนถัดไป")
                    break

        print(f"เสร็จสิ้นการทำงานบล็อก: {blog_name} เพิ่มได้ {added_count} บทความ")

    save_json_file(POSTED_VIDEOS_FILE, posted_videos)
    save_json_file(KEYWORD_STATE_FILE, keyword_state)

    print("\n====================================")
    print("เสร็จสิ้นการทำงานระบบ Multi-Blog ทุกบล็อกประจำรอบนี้")
    print("====================================")


if __name__ == "__main__":
    main()