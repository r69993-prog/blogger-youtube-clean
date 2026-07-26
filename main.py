import os
import json
import time
import html
import random
from datetime import datetime
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# ==========================================
# CONSTANTS & CONFIGURATIONS
# ==========================================
POSTED_VIDEOS_FILE = "posted_videos.json"
KEYWORD_STATE_FILE = "keyword_state.json"

BLOG_CONFIGS = [
    {
        "blog_id": "7261621395427988771",
        "blog_name": "ระบบกลไก",
        "keywords": ["Mechanism design", "Kinematics", "Linkage mechanism", "Mechanical gears", "Mechanical transmission"],
        "labels": ["Mechanism", "Engineering", "Kinematics"]
    },
    {
        "blog_id": "6321192511447492789",
        "blog_name": "Industrial (English)",
        "keywords": ["industrial machinery", "factory automation", "manufacturing technology", "heavy industry", "industrial engineering"],
        "labels": ["Industrial", "Automation", "Engineering"]
    },
    {
        "blog_id": "7707792750976542809",
        "blog_name": "Machine & Mechanical Design (ใหม่)",
        "keywords": ["machine design", "mechanical design", "CAD design", "3D CAD modeling", "solidworks design"],
        "labels": ["MachineDesign", "Mechanical", "CAD"]
    },
    {
        "blog_id": "2962551177226991802",
        "blog_name": "Knowledge Engineering (ใหม่)",
        "keywords": ["knowledge Engineering", "engineering principles", "engineering fundamentals", "technical engineering", "engineering education"],
        "labels": ["Knowledge", "Engineering", "Technical"]
    },
    {
        "blog_id": "2882579450350054162",
        "blog_name": "CNC Machine Center (ใหม่)",
        "keywords": ["CNC", "CNC milling", "CNC machining", "CNC center", "machining center"],
        "labels": ["CNC", "Machining", "Milling"]
    }
]

# ==========================================
# HELPER FUNCTIONS FOR FILE I/O
# ==========================================
def load_json_file(filename, default_value):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[!] ไม่สามารถอ่านไฟล์ {filename} ได้: {e}")
            return default_value
    return default_value

def save_json_file(filename, data):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[!] ไม่สามารถบันทึกไฟล์ {filename} ได้: {e}")

# ==========================================
# CLIENT INITIALIZATION FUNCTIONS
# ==========================================
def get_youtube_client():
    api_keys = []
    for i in range(1, 6):
        key = os.environ.get(f"YOUTUBE_API_KEY_{i}")
        if key and key.strip():
            api_keys.append(key.strip())
            
    if not api_keys:
        fallback_key = os.environ.get("YOUTUBE_API_KEY")
        if fallback_key and fallback_key.strip():
            api_keys.append(fallback_key.strip())

    if not api_keys:
        print("[x] Error: ไม่พบ YOUTUBE_API_KEY ใน Environment Variables")
        return None

    for idx, key in enumerate(api_keys, 1):
        try:
            client = googleapiclient.discovery.build("youtube", "v3", developerKey=key)
            request = client.search().list(q="test", part="id", maxResults=1)
            request.execute()
            print(f"[+] ใช้งาน YouTube API Key ตัวที่ {idx} สำเร็จ")
            return client
        except Exception as e:
            print(f"[!] YouTube API Key ตัวที่ {idx} ไม่สามารถใช้งานได้ หรือ Quota เต็ม: {e}")
            
    print("[x] Error: YouTube API Keys ทั้งหมดไม่สามารถใช้งานได้")
    return None

def get_blogger_client():
    client_id = os.environ.get("BLOGGER_CLIENT_ID")
    client_secret = os.environ.get("BLOGGER_CLIENT_SECRET")
    refresh_token = os.environ.get("BLOGGER_REFRESH_TOKEN")

    if not all([client_id, client_secret, refresh_token]):
        print("[x] Error: ไม่พบ Blogger Credentials ใน Environment Variables")
        return None

    try:
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/blogger"]
        )
        creds.refresh(Request())
        return googleapiclient.discovery.build("blogger", "3", credentials=creds)
    except Exception as e:
        print(f"[x] Error การยืนยันตัวตน Blogger API: {e}")
        return None

# ==========================================
# CONTENT CREATION & PROCESSING
# ==========================================
def sanitize_text(text):
    return html.unescape(text).strip()

def generate_post_title(blog_name, raw_title):
    clean_title = sanitize_text(raw_title)
    patterns = [
        f"เจาะลึกวิศวกรรม: {clean_title} | {blog_name}",
        f"วิเคราะห์ระบบและกลไก: {clean_title}",
        f"การทำงานเชิงลึก: {clean_title} ({blog_name})",
        f"นวัตกรรมทางเทคโนโลยี: {clean_title}"
    ]
    return random.choice(patterns)

def generate_post_content(video_id, title, description, blog_name):
    clean_title = sanitize_text(title)
    clean_desc = sanitize_text(description)
    
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    embed_url = f"https://www.youtube.com/embed/{video_id}"
    
    formatted_description = clean_desc if clean_desc else f"รายงานและรายละเอียดทางเทคนิคสำหรับหัวข้อ {clean_title}"

    html_content = f"""<article style="background-color: #ffffff; color: #2c3e50; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.8; margin: 0px auto; max-width: 850px; padding: 25px; border-radius: 12px; box-shadow: rgba(0, 0, 0, 0.05) 0px 4px 20px;">
    
    <div style="margin-bottom: 20px; text-align: left;">
        <span style="background-color: #ebf8ff; color: #2b6cb0; font-size: 13px; font-weight: 700; padding: 6px 14px; border-radius: 20px; border: 1px solid #bee3f8; text-transform: uppercase; letter-spacing: 0.5px;">{blog_name}</span>
    </div>

    <div style="border-radius: 12px; box-shadow: rgba(0, 0, 0, 0.12) 0px 8px 24px; margin-bottom: 30px; overflow: hidden; text-align: center; background-color: #f8fafc;">
        <img alt="{clean_title}" src="{thumbnail_url}" style="border: 0px; display: block; height: auto; margin: 0px auto; max-width: 100%; width: 100%; object-fit: cover;" />
    </div>

    <section style="background-color: #f7fafc; border-left: 4px solid #3182ce; border-radius: 0px 8px 8px 0px; margin-bottom: 35px; padding: 20px;">
        <h2 style="color: #2b6cb0; font-size: 22px; font-weight: 600; margin-bottom: 12px; margin-top: 0px; line-height: 1.4;">ภาพรวมทางเทคนิค: {clean_title}</h2>
        <p style="color: #4a5568; font-size: 16px; margin: 0px; text-align: justify;">บทความนี้จัดทำขึ้นเพื่อเจาะลึกและวิเคราะห์การทำงานของหัวข้อ '{clean_title}' โดยครอบคลุมถึงโครงสร้างกลไกและระบบการทำงานเชิงวิศวกรรม เพื่อช่วยให้ผู้สนใจสามารถทำความเข้าใจองค์ประกอบและพารามิเตอร์สำคัญได้อย่างรายละเอียดครบถ้วน</p>
    </section>

    <section style="margin-bottom: 35px; text-align: center;">
        <div style="border-radius: 12px; box-shadow: rgba(0, 0, 0, 0.12) 0px 8px 24px; height: 0px; margin: 0px auto; max-width: 100%; overflow: hidden; padding-bottom: 56.25%; position: relative; background-color: #000000;">
            <iframe allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen="" src="{embed_url}" style="border: 0; height: 100%; left: 0; position: absolute; top: 0; width: 100%;" title="{clean_title}">
            </iframe>
        </div>
    </section>

    <section style="background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 35px; padding: 25px; box-shadow: rgba(0, 0, 0, 0.02) 0px 2px 8px;">
        <h3 style="border-bottom: 2px solid #edf2f7; color: #2d3748; font-size: 19px; font-weight: 600; margin-bottom: 16px; margin-top: 0px; padding-bottom: 10px;">การวิเคราะห์โครงสร้างและการทำงานเชิงลึก</h3>
        <p style="color: #4a5568; font-size: 15px; margin: 0px; white-space: pre-wrap; word-break: break-word; line-height: 1.7;">{formatted_description}</p>
    </section>

    <section style="background-color: #ebf8ff; border-radius: 8px; border: 1px solid #bee3f8; margin-bottom: 25px; padding: 20px;">
        <h4 style="color: #2b6cb0; font-size: 16px; font-weight: 600; margin-bottom: 8px; margin-top: 0px;">สรุปสาระสำคัญของระบบ</h4>
        <p style="color: #2d3748; font-size: 15px; margin: 0px; text-align: justify;">จากการศึกษาและวิเคราะห์กรณีของ '{clean_title}' พบว่าการทำความเข้าใจกลไกการขับเคลื่อนและโครงสร้างภายในจะช่วยเพิ่มประสิทธิภาพในการใช้งานและการบำรุงรักษาตามมาตรฐานวิศวกรรมได้อย่างแม่นยำ</p>
    </section>

    <footer style="border-top: 1px solid #e2e8f0; color: #718096; font-size: 13px; margin-top: 30px; padding-top: 15px; text-align: right;">
        แหล่งข้อมูลอ้างอิงวิดีโอต้นฉบับ: <a href="{video_url}" style="color: #3182ce; font-weight: 600; text-decoration: none;" target="_blank" rel="noopener noreferrer">Resource Link</a>
    </footer>
</article>"""
    return html_content

def process_blog(config, youtube, blogger, posted_videos, keyword_state):
    blog_id = config["blog_id"]
    blog_name = config["blog_name"]
    keywords = config["keywords"]
    labels = config.get("labels", [])

    print(f"\n--- เริ่มต้นประมวลผลบล็อก: {blog_name} ({blog_id}) ---")

    if blog_id not in posted_videos:
        posted_videos[blog_id] = []

    current_kw_idx = keyword_state.get(blog_id, 0) % len(keywords)
    keyword = keywords[current_kw_idx]
    
    keyword_state[blog_id] = (current_kw_idx + 1) % len(keywords)

    print(f"กำลังค้นหาคำว่า: {keyword} สำหรับ {blog_name}...")

    try:
        search_response = youtube.search().list(
            q=keyword,
            part="id,snippet",
            maxResults=10,
            type="video",
            relevanceLanguage="en"
        ).execute()
    except Exception as e:
        print(f"[!] เกิดข้อผิดพลาดในการค้นหา YouTube: {e}")
        return

    videos = search_response.get("items", [])
    print(f"พบวิดีโอจากการค้นหาสำหรับบล็อก {blog_name} ทั้งหมด {len(videos)} รายการ")

    added_count = 0
    max_posts_per_run = 2

    for item in videos:
        if added_count >= max_posts_per_run:
            break

        video_id = item["id"]["videoId"]
        if video_id in posted_videos[blog_id]:
            continue

        title = item["snippet"]["title"]
        description = item["snippet"]["description"]

        post_title = generate_post_title(blog_name, title)
        post_content = generate_post_content(video_id, title, description, blog_name)

        body = {
            "kind": "blogger#post",
            "title": post_title,
            "content": post_content,
            "labels": labels
        }

        try:
            post = blogger.posts().insert(blogId=blog_id, body=body).execute()
            print(f"[+] [{added_count + 1}] โพสต์สำเร็จบนบล็อก ({blog_name}): {post_title} | ID: {post.get('id')}")
            posted_videos[blog_id].append(video_id)
            added_count += 1
            time.sleep(2)
        except googleapiclient.errors.HttpError as e:
            if e.resp.status == 429 or "quota" in str(e).lower():
                print(f"[!] เกิดข้อผิดพลาดในการโพสต์ลง Blogger: {e}")
                print("[!] Blogger API Quota เต็ม ข้ามไปประมวลผลขั้นตอนถัดไป")
                break
            else:
                print(f"[!] เกิดข้อผิดพลาดในการโพสต์ลง Blogger: {e}")
        except Exception as e:
            print(f"[!] เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")

    print(f"เสร็จสิ้นการทำงานบล็อก: {blog_name} เพิ่มได้ {added_count} บทความ")

# ==========================================
# MAIN ENTRY POINT
# ==========================================
def main():
    print("====================================")
    print(f"[!] เริ่มทำงานรอบอัตโนมัติ เวลา: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("====================================")

    posted_videos = load_json_file(POSTED_VIDEOS_FILE, {})
    keyword_state = load_json_file(KEYWORD_STATE_FILE, {})

    youtube = get_youtube_client()
    blogger = get_blogger_client()

    if not youtube or not blogger:
        print("[x] ไม่สามารถรันโปรแกรมได้เนื่องจาก Client ไม่พร้อมทำงาน")
        return

    for config in BLOG_CONFIGS:
        process_blog(config, youtube, blogger, posted_videos, keyword_state)

    save_json_file(POSTED_VIDEOS_FILE, posted_videos)
    save_json_file(KEYWORD_STATE_FILE, keyword_state)

    print("\n====================================")
    print("เสร็จสิ้นการทำงานระบบ Multi-Blog ทุกบล็อกประจำรอบนี้")
    print("====================================")

if __name__ == "__main__":
    main()