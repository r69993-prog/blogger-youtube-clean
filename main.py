import os
import pickle
import time
import json
import re
import random
from datetime import datetime, timedelta, timezone
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

def load_config():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, 'config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

CONFIG = load_config()

def get_blogger_service():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(current_dir, 'token.pickle')
    
    if not os.path.exists(token_path):
        raise Exception(f"ไม่พบไฟล์ token.pickle ที่ path: {token_path}")
        
    with open(token_path, 'rb') as token:
        creds = pickle.load(token)
        
    if creds and creds.expired and creds.refresh_token:
        try:
            print("Token expired. Refreshing token...")
            creds.refresh(Request())
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
            print("Token refreshed and saved successfully.")
        except Exception as e:
            print(f"ไม่สามารถรีเฟรช Token ได้: {e}")
            
    return build('blogger', 'v3', credentials=creds)

def get_existing_posts_data(service, blog_id):
    existing_titles = set()
    latest_schedule_time = None
    
    try:
        request_live = service.posts().list(blogId=blog_id, maxResults=50, status="LIVE")
        response_live = request_live.execute()
        if "items" in response_live:
            for post in response_live["items"]:
                existing_titles.add(post["title"])
    except Exception as e:
        print(f"ไม่สามารถดึงข้อมูลโพสต์ LIVE สำหรับบล็อก {blog_id} ได้: {e}")
        
    try:
        request_scheduled = service.posts().list(blogId=blog_id, maxResults=50, status="SCHEDULED")
        response_scheduled = request_scheduled.execute()
        if "items" in response_scheduled:
            for post in response_scheduled["items"]:
                existing_titles.add(post["title"])
                pub_time_str = post["published"].replace("Z", "+00:00")
                pub_time = datetime.fromisoformat(pub_time_str)
                if latest_schedule_time is None or pub_time > latest_schedule_time:
                    latest_schedule_time = pub_time
    except Exception as e:
        print(f"ไม่สามารถดึงข้อมูลโพสต์ SCHEDULED สำหรับบล็อก {blog_id} ได้: {e}")
        
    return existing_titles, latest_schedule_time

def clean_text_multilingual(text, lang="EN"):
    if lang == "TH":
        cleaned = re.sub(r'[^\u0e00-\u0e7f\w\s\-\.\,\?\!\'\"]', '', text)
    else:
        cleaned = re.sub(r'[^\w\s\-\.\,\?\!\'\"]', '', text)
    return ' '.join(cleaned.split())

def restructure_title_seo(raw_title, blog_config):
    lang = blog_config.get("language", "EN")
    clean_title = clean_text_multilingual(raw_title, lang)
    
    if lang == "TH":
        seo_title = f"เจาะลึกระบบ: {clean_title}"
    else:
        words = clean_title.split()
        if len(words) >= 4:
            part_1 = " ".join(words[:2])
            part_2 = " ".join(words[2:])
            seo_title = f"Deep Dive: {part_2} - Comprehensive Analysis of {part_1}"
        else:
            seo_title = f"The Ultimate Guide to {clean_title}"
            
    raw_suffix = blog_config.get('seo_title_suffix', '')
    if isinstance(raw_suffix, list):
        chosen_suffix = random.choice(raw_suffix) if raw_suffix else ''
    else:
        chosen_suffix = raw_suffix
        
    clean_suffix = clean_text_multilingual(chosen_suffix, lang)
    
    if clean_suffix:
        return f"{seo_title} {clean_suffix}"
    return seo_title

def search_youtube_videos_for_blog(blog_config, api_keys, exhausted_keys):
    if not api_keys:
        print("[x] ไม่พบรหัส YOUTUBE_API_KEYS ในคอนฟิก")
        return []

    all_videos = []
    lang = blog_config.get("language", "EN")
    keywords = blog_config.get("youtube_search_keywords", [])
    
    if not keywords:
        return []

    selected_keyword = random.choice(keywords)
    search_success = False

    for api_key in api_keys:
        if not api_key or "ใส่_" in api_key or api_key in exhausted_keys:
            continue
            
        try:
            print(f"กำลังค้นหาคำว่า: {selected_keyword} สำหรับ {blog_config['blog_name']} (ใช้ API Key...)...")
            youtube = build('youtube', 'v3', developerKey=api_key)
            request = youtube.search().list(
                q=selected_keyword,
                part="snippet",
                type="video",
                maxResults=blog_config.get("max_results_per_run", 1),
                order="relevance"
            )
            response = request.execute()
            
            if "items" in response:
                for item in response["items"]:
                    video_id = item["id"]["videoId"]
                    snippet = item["snippet"]
                    
                    raw_title = snippet["title"]
                    seo_title = restructure_title_seo(raw_title, blog_config)
                    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                    
                    video_data = {
                        'raw_title': raw_title,
                        'seo_title': seo_title,
                        'link': f"https://www.youtube.com/watch?v={video_id}",
                        'video_id': video_id,
                        'thumbnail': thumbnail_url,
                        'description': clean_text_multilingual(snippet.get("description", ""), lang),
                        'search_keyword': selected_keyword
                    }
                    all_videos.append(video_data)
            search_success = True
            break
        except Exception as api_err:
            err_msg = str(api_err)
            if "quotaExceeded" in err_msg or "rateLimitExceeded" in err_msg or "403" in err_msg or "429" in err_msg:
                print(f"[!] API Key โควตาเต็ม บันทึกจำเพื่อข้าม Key นี้ในรอบปัจจุบัน...")
                exhausted_keys.add(api_key)
                continue
            else:
                print(f"[x] การค้นหาด้วยคีย์เวิร์ด '{selected_keyword}' เกิดข้อผิดพลาด: {api_err}")
                break

    if not search_success:
        print(f"[x] ทุก API Key เต็มหมดแล้ว ไม่สามารถใช้งานคีย์เวิร์ด: {selected_keyword}")
        
    return all_videos

def generate_article_html(video, lang="EN"):
    clean_desc = video['description']
    raw_title = video['raw_title']
    
    if lang == "TH":
        if not clean_desc:
            clean_desc = "รายละเอียดข้อมูลระบบกลไกและวิศวกรรมโครงสร้างสำหรับการวิเคราะห์ระบบอัตโนมัติเบื้องต้น"
        intro_text = f"บทความนี้จัดทำขึ้นเพื่อเจาะลึกและวิเคราะห์การทำงานของหัวข้อ '{raw_title}' โดยครอบคลุมถึงโครงสร้างกลไกและระบบการทำงานเชิงวิศวกรรม เพื่อช่วยให้ผู้สนใจสามารถทำความเข้าใจองค์ประกอบและพารามิเตอร์สำคัญได้อย่างละเอียด"
        heading_1 = f"ภาพรวมทางเทคนิค: {raw_title}"
        heading_2 = "การวิเคราะห์โครงสร้างและการทำงานเชิงลึก"
        conclusion_heading = "สรุปสาระสำคัญของระบบ"
        conclusion_text = f"จากการศึกษาและวิเคราะห์กรณีของ '{raw_title}' พบว่าการทำความเข้าใจกลไกการขับเคลื่อนและโครงสร้างภายในจะช่วยเพิ่มประสิทธิภาพในการใช้งานและการบำรุงรักษาตามมาตรฐานวิศวกรรม"
        footer_text = "แหล่งข้อมูลอ้างอิงวิดีโอต้นฉบับ:"
    else:
        if not clean_desc:
            clean_desc = "Advanced methodology and modern deployment practices in specialized engineering systems."
        intro_text = f"This deployment blueprint delivers an analytical inspection of '{raw_title}'. By breaking down operational parameters and examining structural components, engineers can synthesize data pathways to achieve lean performance benchmarks."
        heading_1 = f"Technical Framework: {raw_title}"
        heading_2 = "Operational Analysis & Core Specifications"
        conclusion_heading = "Analytical Conclusion"
        conclusion_text = f"Synthesizing these configurations for '{raw_title}' demonstrates that applying these process steps lowers systemic friction, simplifies troubleshooting pipelines, and supports reliability engineering standards."
        footer_text = "Original Knowledge Resource:"

    html = f"""<article style="font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 850px; margin: 0 auto; padding: 20px; color: #2c3e50; line-height: 1.8; background-color: #ffffff;">
    
    <div style="text-align: center; margin-bottom: 30px; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.12);">
        <img src="{video['thumbnail']}" alt="Technical Visual Presentation" style="width: 100%; max-width: 750px; height: auto; display: block; margin: 0 auto; border: 0;"/>
    </div>

    <section style="margin-bottom: 35px; border-left: 4px solid #3182ce; padding-left: 20px; background-color: #f7fafc; padding-top: 15px; padding-bottom: 15px; border-radius: 0 8px 8px 0;">
        <h2 style="color: #2b6cb0; font-size: 22px; margin-top: 0; margin-bottom: 10px; font-weight: 600;">{heading_1}</h2>
        <p style="font-size: 16px; margin: 0; color: #4a5568;">{intro_text}</p>
    </section>

    <section style="margin-bottom: 35px; text-align: center;">
        <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.12); max-width: 750px; margin: 0 auto;">
            <iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;"
                    src="https://www.youtube.com/embed/{video['video_id']}" 
                    title="Embedded Resource Video Feed"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                    allowfullscreen>
            </iframe>
        </div>
    </section>

    <section style="margin-bottom: 35px; background-color: #ffffff; border: 1px solid #e2e8f0; padding: 25px; border-radius: 8px;">
        <h3 style="color: #2d3748; font-size: 19px; margin-top: 0; margin-bottom: 12px; font-weight: 600; border-bottom: 2px solid #edf2f7; padding-bottom: 8px;">{heading_2}</h3>
        <p style="font-size: 15px; color: #4a5568; white-space: pre-wrap; margin: 0;">{clean_desc}</p>
    </section>

    <section style="margin-bottom: 25px; background-color: #ebf8ff; border: 1px solid #bee3f8; padding: 20px; border-radius: 8px;">
        <h4 style="color: #2b6cb0; font-size: 16px; margin-top: 0; margin-bottom: 8px; font-weight: 600;">{conclusion_heading}</h4>
        <p style="font-size: 15px; margin: 0; color: #2d3748;">{conclusion_text}</p>
    </section>

    <footer style="margin-top: 30px; padding-top: 15px; border-top: 1px solid #e2e8f0; font-size: 13px; color: #718096; text-align: right;">
        {footer_text} <a href="{video['link']}" target="_blank" style="color: #3182ce; text-decoration: none; font-weight: 500;">Resource Link</a>
    </footer>
</article>"""
    return html

def run_search_posting_multi_blog():
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"\n====================================")
    print(f"[!] เริ่มทำงานรอบอัตโนมัติ เวลา: {current_time}")
    print(f"====================================")
    
    try:
        service = get_blogger_service()
        
        api_keys = CONFIG.get("YOUTUBE_API_KEYS", [])
        if not api_keys and CONFIG.get("YOUTUBE_API_KEY"):
            api_keys = [CONFIG.get("YOUTUBE_API_KEY")]
            
        blogs_list = CONFIG.get("blogs", [])
        exhausted_keys = set()
        
        for blog in blogs_list:
            blog_id = blog.get("BLOG_ID")
            blog_name = blog.get("blog_name", "Unknown Blog")
            lang = blog.get("language", "EN")
            interval_hours = CONFIG.get('time_interval_hours', 3)
            
            print(f"\n--- เริ่มต้นประมวลผลบล็อก: {blog_name} ({blog_id}) ---")
            
            existing_titles, latest_schedule_time = get_existing_posts_data(service, blog_id)
            videos = search_youtube_videos_for_blog(blog, api_keys, exhausted_keys)
            
            if not videos:
                print(f"ไม่พบวิดีโอจากคีย์เวิร์ดสำหรับบล็อก: {blog_name}")
                continue
                
            print(f"พบวิดีโอจากการค้นหาสำหรับบล็อก {blog_name} ทั้งหมด {len(videos)} รายการ")
            
            if latest_schedule_time:
                current_schedule = latest_schedule_time + timedelta(hours=interval_hours)
            else:
                current_schedule = datetime.now(timezone.utc) + timedelta(minutes=10)
                
            posted_count = 0
            
            for video in videos:
                if video['seo_title'] in existing_titles or video['raw_title'] in existing_titles:
                    print(f"[-] ข้ามโพสต์ซ้ำ: {video['raw_title']}")
                    continue
                    
                html_content = generate_article_html(video, lang)
                scheduled_iso = current_schedule.isoformat()
                
                base_labels = blog.get("blogger_labels", ["Video"])
                if isinstance(base_labels, list):
                    dynamic_labels = list(set(base_labels + [video['search_keyword']]))
                else:
                    dynamic_labels = [base_labels, video['search_keyword']]
                
                body = {
                    "kind": "blogger#post",
                    "title": video['seo_title'],
                    "content": html_content,
                    "published": scheduled_iso,
                    "labels": dynamic_labels
                }
                
                try:
                    request = service.posts().insert(blogId=blog_id, body=body, isDraft=False)
                    response = request.execute()
                    posted_count += 1
                    print(f"[+] [{posted_count}] ตั้งเวลาสำเร็จบนบล็อก ({blog_name}): {video['seo_title']} | Labels: {dynamic_labels}")
                    
                    current_schedule += timedelta(hours=interval_hours)
                    time.sleep(10)
                    
                except Exception as api_err:
                    if "rateLimitExceeded" in str(api_err) or "429" in str(api_err):
                        print("\n[!] โควตา Blogger API เต็มระบบหยุดทำงานอย่างปลอดภัยในบล็อกนี้")
                        break
                    else:
                        print(f"[x] เกิดข้อผิดพลาดในบทความนี้: {api_err}")
                
            print(f"เสร็จสิ้นการทำงานบล็อก: {blog_name} เพิ่มได้ {posted_count} บทความ")
            
        print("\n====================================")
        print(f"เสร็จสิ้นการทำงานระบบ Multi-Blog ทุกบล็อกประจำรอบนี้")
        print("====================================")
        
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการทำงานของระบบอัตโนมัติ: {e}")

if __name__ == "__main__":
    run_search_posting_multi_blog()