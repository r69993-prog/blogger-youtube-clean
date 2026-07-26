# ภาพรวมและขอบเขตการทำงานของระบบ (Multi-Blog Automated Publisher)

## 1. ภาพรวมของระบบ (System Overview)
ระบบทำงานอัตโนมัติสำหรับการดึงข้อมูลวิดีโอจาก YouTube Data API v3 นำมาเรียบเรียงเป็นบทความโครงสร้าง HTML ระดับ HD และโพสต์ลงบน Blogger หลายบล็อกพร้อมกันโดยอัตโนมัติ พร้อมรองรับการตั้งเวลาโพสต์ล่วงหน้าและการสลับคีย์เวิร์ดอัจฉริยะ

---

## 2. ขอบเขตการทำงาน (System Scope & Features)

### 2.1 การจัดการเนื้อหาและภาษา (Multi-Language Content)
- **รองรับ 2 ภาษาหลัก:** ภาษาไทย (`th`) และภาษาอังกฤษ (`en`)
- **ระบบปรับแต่งรูปแบบตามภาษา:**
  - บล็อกภาษาอังกฤษ (`lang: en`): ใช้ชื่อบทความ เนื้อหา และองค์ประกอบทั้งหมดเป็นภาษาอังกฤษบริสุทธิ์ 100% (ไม่มีภาษาไทยปน)
  - บล็อกภาษาไทย (`lang: th`): ใช้ชื่อบทความและเนื้อหาเป็นภาษาไทย

### 2.2 การสลับและจัดการคีย์เวิร์ด (Keyword Rotation)
- ดึงคีย์เวิร์ดจาก `BLOG_CONFIGS` มาใช้งานทีละคำตามลำดับ
- บันทึกสถานะคีย์เวิร์ดแยกลายบล็อกลงในไฟล์ `keyword_state.json` เพื่อสลับคำค้นหาในรอบถัดไปอัตโนมัติ

### 2.3 ระบบป้องกันการโพสต์ซ้ำ (Deduplication System)
- ตรวจสอบ ID วิดีโอจาก YouTube ที่เคยโพสต์ไปแล้ว
- บันทึก ID วิดีโอที่โพสต์สำเร็จลงในไฟล์ `posted_videos.json` แยกตาม `blog_id`

### 2.4 ระบบตั้งเวลาโพสต์อัตโนมัติ (Automated Scheduling)
- คำนวณเวลาเผยแพร่อัตโนมัติในรูปแบบ ISO 8601 UTC
- กำหนดระยะห่างระหว่างบทความทีละ 1 ชั่วโมง (`+1 hour`) ต่อ 1 โพสต์ เพื่อกระจายช่วงเวลาเผยแพร่

### 2.5 การจัดการ Quota และ API (Error & Quota Handling)
- **YouTube API Keys:** รองรับ Multi-Key โดยระบบจะลองใช้งาน Key ถัดไปอัตโนมัติเมื่อ Key เดิม Quota เต็ม
- **Blogger API Quota:** ดักจับ Error Code `429` (Rate Limit / Quota Exhausted) หาก Quota เต็ม ระบบจะข้ามไปประมวลผลบล็อกถัดไปทันทีโดยไม่ทำให้โปรแกรม Crash

---

## 3. รายชื่อและตั้งค่าบล็อกในระบบ (Blog Configurations)

| Blog ID | ชื่อบล็อก (Blog Name) | ภาษา (Lang) | Labels |
| :--- | :--- | :---: | :--- |
| `7261621395427988771` | ระบบกลไก | `th` | Mechanism, Engineering, Kinematics |
| `6321192511447492789` | Industrial (English) | `en` | Industrial, Automation, Engineering |
| `7707792750976542809` | Machine & Mechanical Design | `en` | MachineDesign, Mechanical, CAD |
| `2962551177226991802` | Knowledge Engineering | `en` | Knowledge, Engineering, Technical |
| `2882579450350054162` | CNC Machine Center | `th` | CNC, Machining, Milling |

---

## 4. โครงสร้างไฟล์ในโปรเจกต์ (Project Structure)
- `main.py`: ไฟล์หลักควบคุมการดึงข้อมูล สร้างเนื้อหา และส่งโพสต์ไปยัง Blogger
- `posted_videos.json`: บันทึกประวัติ ID วิดีโอที่เคยโพสต์แล้ว
- `keyword_state.json`: บันทึกดัชนีคีย์เวิร์ดล่าสุดของแต่ละบล็อก
- `SYSTEM_SUMMARY.md`: เอกสารสรุปขอบเขตและการทำงานของระบบ