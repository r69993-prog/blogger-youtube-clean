import os
import json
import time
import html
import random
from datetime import datetime, timedelta, timezone
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
        "lang": "th",
        "keywords": ["Mechanism design", "Kinematics", "Linkage mechanism", "Mechanical gears", "Mechanical transmission", "Cam mechanism", "Four bar linkage"],
        "labels": ["Mechanism", "Engineering", "Kinematics"]
    },
    {
        "blog_id": "6321192511447492789",
        "blog_name": "Industrial technology ",
        "lang": "en",
        "keywords": ["industrial machinery", "factory automation", "manufacturing technology", "heavy industry", "industrial engineering", "smart manufacturing", "robotic assembly"],
        "labels": ["Industrial", "Automation", "Engineering"]
    },
    {
        "blog_id": "7707792750976542809",
        "blog_name": "Machine & Mechanical Design",
        "lang": "en",
        "keywords": ["machine design", "mechanical design", "CAD design", "3D CAD modeling", "solidworks design", "machine element design", "mechanical assembly"],
        "labels": ["MachineDesign", "Mechanical", "CAD"]
    },
    {
        "blog_id": "2962551177226991802",
        "blog_name": "Knowledge Engineering",
        "lang": "en",
        "keywords": ["knowledge Engineering", "engineering principles", "engineering fundamentals", "technical engineering", "engineering education", "applied mechanics", "thermodynamics basics"],
        "labels": ["Knowledge", "Engineering", "Technical"]
    },
    {
        "blog_id": "2882579450350054162",
        "blog_name": "CNC Machine Center",
        "lang": "th",
        "keywords": ["CNC", "CNC milling", "CNC machining", "CNC center", "machining center", "G-code programming", "CNC lathe"],
        "labels": ["CNC", "Machining", "Milling"]
    },
    {
        "blog_id": "2055991579883803861",
        "blog_name": "นิวแมติกส์และไฮดรอลิกส์",
        "lang": "th",
        "keywords": ["Pneumatics", "Hydraulics", "Actuator", "Valve", "Cylinder", "Pump", "Compressor", "Fluid power", "Air pressure", "Hose"],
        "labels": ["Pneumatics", "Hydraulics", "Engineering"]
    }
]

# Global scheduling tracker
NEXT_SCHEDULED_TIME = datetime.now(timezone.utc) + timedelta(hours=1)

# คำขยายสำหรับผสมค้นหาให้เจอคลิปหลากหลาย
SEARCH_MODIFIERS = ["tutorial", "working principle", "animation", "overview", "system", "explained", "basics", "advanced"]

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
        return googleapiclient.discovery.build("blogger", "v3", credentials=creds)
    except Exception as e:
        print(f"[x] Error การยืนยันตัวตน Blogger API: {e}")
        return None

# ==========================================
# RETRY & POSTING HELPER (เพิ่มส่วนนี้แก้ 429)
# ==========================================
def insert_post_with_retry(blogger, blog_id, body, max_retries=3):
    """
    ส่งโพสต์ลง Blogger พร้อมระบบลองใหม่อัตโนมัติ หากเจอ Rate Limit (429)
    """
    delay = 15  # รอนาทีละ 15 วินาทีในรอบแรก
    for attempt in range(1, max_retries + 1):
        try:
            return blogger.posts().insert(
                blogId=blog_id,
                body=body,
                isDraft=False
            ).execute()
        except googleapiclient.errors.HttpError as e:
            is_rate_limit = e.resp.status in [429, 503] or "quota" in str(e).lower() or "rateLimitExceeded" in str(e).lower()
            
            if is_rate_limit and attempt < max_retries:
                print(f"[!] ติด Rate Limit/Quota ชั่วคราว (429) จะลองใหม่อีกครั้งใน {delay} วินาที... (ครั้งที่ {attempt}/{max_retries})")
                time.sleep(delay)
                delay *= 2  # เพิ่มเวลารอเป็นเท่าตัว (15s -> 30s)
            else:
                raise e

# ==========================================
# CONTENT CREATION & PROCESSING
# ==========================================
def sanitize_text(text):
    return html.unescape(text).strip()

def generate_post_title(blog_name, raw_title, lang="th"):
    clean_title = sanitize_text(raw_title)
    if lang == "en":
        patterns = [
            f"Technical Analysis: {clean_title} | {blog_name}",
            f"Engineering Insights: {clean_title}",
            f"In-Depth Overview: {clean_title} ({blog_name})",
            f"Technology & Innovation: {clean_title}"
        ]
    else:
        patterns = [
            f"เจาะลึกวิศวกรรม: {clean_title} | {blog_name}",
            f"วิเคราะห์ระบบและกลไก: {clean_title}",
            f"การทำงานเชิงลึก: {clean_title} ({blog_name})",
            f"นวัตกรรมทางเทคโนโลยี: {clean_title}"
        ]
    return random.choice(patterns)

def generate_post_content(video_id, title, description, blog_name, lang="th"):
    clean_title = sanitize_text(title)
    clean_desc = sanitize_text(description)
    
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    embed_url = f"https://www.youtube.com/embed/{video_id}"
    
    if lang == "en":
        formatted_description = clean_desc if clean_desc else f"Technical documentation and detailed report for {clean_title}."
        
        overview_heading = f"Technical Overview: {clean_title}"
        overview_text = f"This article provides an in-depth technical analysis of '{clean_title}', covering key mechanism structures, engineering operational principles, and essential parameters for technical understanding."
        details_heading = "In-Depth Structural & System Analysis"
        summary_heading = "Key Takeaways & System Summary"
        summary_text = f"Through careful analysis of '{clean_title}', understanding internal mechanisms and driving systems significantly optimizes operational efficiency and maintenance standards."
        resource_text = "Original Video Resource Link"
    else:
        formatted_description = clean_desc if clean_desc else f"รายงานและรายละเอียดทางเทคนิคสำหรับหัวข้อ {clean_title}"
        
        overview_heading = f"ภาพรวมทางเทคนิค: {clean_title}"
        overview_text = f"บทความนี้จัดทำขึ้นเพื่อเจาะลึกและวิเคราะห์การทำงานของหัวข้อ '{clean_title}' โดยครอบคลุมถึงโครงสร้างกลไกและระบบการทำงานเชิงวิศวกรรม เพื่อช่วยให้ผู้สนใจสามารถทำความเข้าใจองค์ประกอบและพารามิเตอร์สำคัญได้อย่างรายละเอียดครบถ้วน"
        details_heading = "การวิเคราะห์โครงสร้างและการทำงานเชิงลึก"
        summary_heading = "สรุปสาระสำคัญของระบบ"
        summary_text = f"จากการศึกษาและวิเคราะห์กรณีของ '{clean_title}' พบว่าการทำความเข้าใจกลไกการขับเคลื่อนและโครงสร้างภายในจะช่วยเพิ่มประสิทธิภาพในการใช้งานและการบำรุงรักษาตามมาตรฐานวิศวกรรมได้อย่างแม่นยำ"
        resource_text = "แหล่งข้อมูลอ้างอิงวิดีโอต้นฉบับ"

    html_content = f"""<article style="background-color: #ffffff; color: #2c3e50; font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.8; margin: 0px auto; max-width: 850px; padding: 25px; border-radius: 12px; box-shadow: rgba(0, 0, 0, 0.05) 0px 4px 20px;">
    
    <div style="margin-bottom: 20px; text-align: left;">
        <span style="background-color: #ebf8ff; color: #2b6cb0; font-size: 13px; font-weight: 700; padding: 6px 14px; border-radius: 20px; border: 1px solid #bee3f8; text-transform: uppercase; letter-spacing: 0.5px;">{blog_name}</span>
    </div>

    <div style="border-radius: 12px; box-shadow: rgba(0, 0, 0, 0.12) 0px 8px 24px; margin-bottom: 30px; overflow: hidden; text-align: center; background-color: #f8fafc;">
        <img alt="{clean_title}" src="{thumbnail_url}" style="border: 0px; display: block; height: auto; margin: 0px auto; max-width: 100%; width: 100%; object-fit: cover;" />
    </div>

    <section style="background-color: #f7fafc; border-left: 4px solid #3182ce; border-radius: 0px 8px 8px 0px; margin-bottom: 35px; padding: 20px;">
        <h2 style="color: #2b6cb0; font-size: 22px; font-weight: 600; margin-bottom: 12px; margin-top: 0px; line-height: 1.4;">{overview_heading}</h2>
        <p style="color: #4a5568; font-size: 16px; margin: 0px; text-align: justify;">{overview_text}</p>
    </section>

    <section style="margin-bottom: 35px; text-align: center;">
        <div style="border-radius: 12px; box-shadow: rgba(0, 0, 0, 0.12) 0px 8px 24px; height: 0px; margin: 0px auto; max-width: 100%; overflow: hidden; padding-bottom: 56.25%; position: relative; background-color: #000000;">
            <iframe allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen="" src="{embed_url}" style="border: 0; height: 100%; left: 0; position: absolute; top: 0; width: 100%;" title="{clean_title}">
            </iframe>
        </div>
    </section>

    <section style="background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 35px; padding: 25px; box-shadow: rgba(0, 0, 0, 0.02) 0px 2px 8px;">
        <h3 style="border-bottom: 2px solid #edf2f7; color: #2d3748; font-size: 19px; font-weight: 600; margin-bottom: 16px; margin-top: 0px; padding-bottom: 10px;">{details_heading}</h3>
        <p style="color: #4a5568; font-size: 15px; margin: 0px; white-space: pre-wrap; word-break: break-word; line-height: 1.7;">{formatted_description}</p>
    </section>

    <section style="background-color: #ebf8ff; border-radius: 8px; border: 1px solid #bee3f8; margin-bottom: 25px; padding: 20px;">
        <h4 style="color: #2b6cb0; font-size: 16px; font-weight: 600; margin-bottom: 8px; margin-top: 0px;">{summary_heading}</h4>
        <p style="color: #2d3748; font-size: 15px; margin: 0px; text-align: justify;">{summary_text}</p>
    </section>

    <footer style="border-top: 1px solid #e2e8f0; color: #718096; font-size: 13px; margin-top: 30px; padding-top: 15px; text-align: right;">
        {resource_text}: <a href="{video_url}" style="color: #3182ce; font-weight: 600; text-decoration: none;" target="_blank" rel="noopener noreferrer">Resource Link</a>
    </footer>
</article>"""
    return html_content

def get_next_keyword(blog_id, keywords, keyword_state):
    last_idx = keyword_state.get(blog_id, -1)
    next_idx = (last_idx + 1) % len(keywords)
    keyword_state[blog_id] = next_idx
    return keywords[next_idx]

def process_blog(config, youtube, blogger, posted_videos, keyword_state):
    global NEXT_SCHEDULED_TIME
    blog_id = config["blog_id"]
    blog_name = config["blog_name"]
    lang = config.get("lang", "th")
    keywords = config["keywords"]
    labels = config.get("labels", [])

    print(f"\n--- เริ่มต้นประมวลผลบล็อก: {blog_name} ({blog_id}) [ภาษา: {lang.upper()}] ---")

    if blog_id not in posted_videos:
        posted_videos[blog_id] = []

    base_keyword = get_next_keyword(blog_id, keywords, keyword_state)
    modifier = random.choice(SEARCH_MODIFIERS)
    search_query = f"{base_keyword} {modifier}"
    
    order_type = random.choice(["relevance", "date"])

    print(f"กำลังค้นหาคำว่า: '{search_query}' (เรียงตาม: {order_type}) สำหรับ {blog_name}...")

    try:
        search_response = youtube.search().list(
            q=search_query,
            part="id,snippet",
            maxResults=50,
            type="video",
            order=order_type,
            relevanceLanguage=lang
        ).execute()
    except Exception as e:
        print(f"[!] เกิดข้อผิดพลาดในการค้นหา YouTube: {e}")
        return

    videos = search_response.get("items", [])
    random.shuffle(videos)
    print(f"พบวิดีโอจากการค้นหาสำหรับบล็อก {blog_name} ทั้งหมด {len(videos)} รายการ")

    added_count = 0
    max_posts_per_run = 1

    for item in videos:
        if added_count >= max_posts_per_run:
            break

        video_id = item["id"]["videoId"]
        if video_id in posted_videos[blog_id]:
            print(f"[-] ข้ามวิดีโอซ้ำ (Video ID: {video_id})")
            continue

        title = item["snippet"]["title"]
        description = item["snippet"]["description"]

        post_title = generate_post_title(blog_name, title, lang)
        post_content = generate_post_content(video_id, title, description, blog_name, lang)

        publish_time_iso = NEXT_SCHEDULED_TIME.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        body = {
            "kind": "blogger#post",
            "title": post_title,
            "content": post_content,
            "labels": labels,
            "published": publish_time_iso
        }

        try:
            # ใช้นวัตกรรมใหม่ insert_post_with_retry เพื่อป้องกัน 429
            post = insert_post_with_retry(blogger, blog_id, body, max_retries=3)
            
            print(f"[+] [{added_count + 1}] ตั้งเวลาโพสต์สำเร็จบนบล็อก ({blog_name}): {post_title} | เวลาเผยแพร่ UTC: {publish_time_iso}")
            posted_videos[blog_id].append(video_id)
            added_count += 1
            
            # เว้นช่วงระหว่างโพสต์แบบสุ่ม 1 ถึง 2 ชั่วโมง
            random_interval_minutes = random.randint(60, 120)
            NEXT_SCHEDULED_TIME += timedelta(minutes=random_interval_minutes)
            
            # หน่วงเวลาเล็กน้อยหลังโพสต์สำเร็จ
            time.sleep(5)
        except googleapiclient.errors.HttpError as e:
            if e.resp.status == 429 or "quota" in str(e).lower():
                print(f"[!] Blogger API Quota เต็มของวัน หรือโดนบล็อกเกินกำหนด ข้ามไปบล็อกถัดไป")
                break
            else:
                print(f"[!] เกิดข้อผิดพลาดในการโพสต์ลง Blogger: {e}")
        except Exception as e:
            print(f"[!] เกิดข้อผิดพลาดที่ไม่คาดคิด: {e}")

    # หน่วงเวลา 5 วินาทีเมื่อเปลี่ยนไปประมวลผลบล็อกถัดไป
    time.sleep(5)
    print(f"เสร็จสิ้นการทำงานบล็อก: {blog_name} เพิ่มได้ {added_count} บทความ")

# ==========================================
# MAIN ENTRY POINT
# ==========================================
def main():
    global NEXT_SCHEDULED_TIME
    print("====================================")
    print(f"[!] เริ่มทำงานรอบอัตโนมัติ เวลา: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("====================================")

    # โพสต์แรกเริ่มหลังจากรันระบบไปแล้ว 1 ชั่วโมง
    NEXT_SCHEDULED_TIME = datetime.now(timezone.utc) + timedelta(hours=1)

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
