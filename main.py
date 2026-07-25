import os
import json
import pickle
import time
import re
import urllib.parse
from datetime import datetime, timezone
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

def get_blogger_service():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token expired. Refreshing token...")
            creds.refresh(Request())
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
            print("Token refreshed and saved successfully.")
        else:
            raise Exception("Invalid or missing credentials. Please generate a new token.pickle.")

    blogger = build('blogger', 'v3', credentials=creds)
    return blogger

def get_youtube_service(api_key):
    if not api_key:
        raise Exception("YOUTUBE_API_KEY is missing in config.json")
    return build('youtube', 'v3', developerKey=api_key)

def clean_tag(text):
    clean = re.sub(r'[^a-zA-Z0-9ก-๙\s]', '', text)
    clean = clean.replace('\n', ' ').strip()
    words = clean.split()
    return ' '.join(words[:3]) if words else "General"

def search_youtube(youtube, query, max_results=5):
    request = youtube.search().list(
        q=query,
        part='snippet',
        type='video',
        maxResults=max_results,
        order='relevance'
    )
    response = request.execute()
    return response.get('items', [])

def get_existing_posts(blogger, blog_id):
    existing_titles = set()
    page_token = None
    while True:
        request = blogger.posts().list(
            blogId=blog_id,
            fetchBodies=False,
            pageToken=page_token
        )
        response = request.execute()
        items = response.get('items', [])
        for item in items:
            existing_titles.add(item['title'].strip())
        page_token = response.get('nextPageToken')
        if not page_token:
            break
    return existing_titles

def create_blogger_post(blogger, blog_id, title, video_id, description, labels, publish_time):
    embed_code = f'<iframe width="560" height="315" src="https://www.youtube.com/embed/{video_id}" frameborder="0" allowfullscreen></iframe>'
    content = f'<div style="text-align: center;">{embed_code}</div><br/><p>{description}</p>'
    
    body = {
        'kind': 'blogger#post',
        'title': title,
        'content': content,
        'labels': labels,
        'published': publish_time
    }
    
    request = blogger.posts().insert(
        blogId=blog_id,
        body=body,
        isDraft=False
    )
    return request.execute()

def main():
    if not os.path.exists('config.json'):
        print("Error: config.json not found.")
        return

    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)

    api_key = config.get('YOUTUBE_API_KEY')
    youtube = get_youtube_service(api_key)
    blogger = get_blogger_service()

    for blog in config.get('blogs', []):
        blog_name = blog.get('blog_name', 'Unknown Blog')
        blog_id = blog.get('BLOG_ID')
        keywords = blog.get('youtube_search_keywords', [])
        seo_suffix = blog.get('seo_title_suffix', '')
        base_labels = blog.get('blogger_labels', [])
        max_posts = blog.get('max_results_per_run', 1)
        
        if not blog_id:
            print(f"[!] ข้ามการทำงานเนื่องจากไม่พบ BLOG_ID สำหรับ: {blog_name}")
            continue

        print(f"\n--- เริ่มต้นประมวลผลบล็อก: {blog_name} ({blog_id}) ---")
        
        try:
            existing_titles = get_existing_posts(blogger, blog_id)
        except Exception as e:
            print(f"[!] ไม่สามารถดึงข้อมูลโพสต์เดิมได้สำหรับบล็อก {blog_name}: {e}")
            continue

        found_videos = []
        seen_video_ids = set()

        for kw in keywords:
            print(f"กำลังค้นหาคำว่า: {kw} สำหรับ {blog_name}...")
            try:
                items = search_youtube(youtube, kw, max_results=5)
                for item in items:
                    v_id = item['id']['videoId']
                    if v_id not in seen_video_ids:
                        seen_video_ids.add(v_id)
                        found_videos.append((kw, item))
            except Exception as e:
                print(f"[!] ข้อผิดพลาดในการค้นหา YouTube สำหรับคีย์เวิร์ด {kw}: {e}")

        print(f"พบวิดีโอจากการค้นหาสำหรับบล็อก {blog_name} ทั้งหมด {len(found_videos)} รายการ")
        
        added_count = 0
        for kw, item in found_videos:
            if added_count >= max_posts:
                break

            v_id = item['id']['videoId']
            raw_title = item['snippet']['title']
            raw_desc = item['snippet']['description']
            
            clean_kw = clean_tag(kw)
            
            if seo_suffix:
                post_title = f"Deep Dive: {raw_title} - {seo_suffix}"
            else:
                post_title = f"Deep Dive: {raw_title} - Comprehensive Analysis of {clean_kw}"
            
            if raw_title.strip() in existing_titles or post_title.strip() in existing_titles:
                print(f"[-] ข้ามโพสต์ซ้ำ: {raw_title}")
                continue

            labels = list(base_labels)
            if clean_kw not in labels:
                labels.append(clean_kw)

            publish_time = datetime.now(timezone.utc).isoformat()
            
            try:
                create_blogger_post(blogger, blog_id, post_title, v_id, raw_desc, labels, publish_time)
                print(f"[+] [{added_count + 1}] ตั้งเวลาสำเร็จบนบล็อก ({blog_name}): {post_title} | Labels: {labels}")
                existing_titles.add(post_title.strip())
                added_count += 1
            except Exception as e:
                print(f"[!] เกิดข้อผิดพลาดในการสร้างโพสต์: {e}")

        print(f"เสร็จสิ้นการทำงานบล็อก: {blog_name} เพิ่มได้ {added_count} บทความ")

    print("\n====================================")
    print("เสร็จสิ้นการทำงานระบบ Multi-Blog ทุกบล็อกประจำรอบนี้")
    print("====================================")

if __name__ == '__main__':
    main()