import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

# อนุญาตให้ใช้ HTTP สำหรับการทดสอบ
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

SCOPES = ['https://www.googleapis.com/auth/blogger']

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    client_secrets_path = os.path.join(current_dir, 'client_secrets.json')
    token_path = os.path.join(current_dir, 'token.pickle')

    if not os.path.exists(client_secrets_path):
        print(f"Error: client_secrets.json not found at {client_secrets_path}")
        return

    # บังคับ Redirect กลับมาที่ localhost แบบตรงๆ
    flow = InstalledAppFlow.from_client_secrets_file(
        client_secrets_path, 
        SCOPES, 
        redirect_uri='http://localhost:8080/'
    )

    auth_url, _ = flow.authorization_url(prompt='consent')

    print("\n=== กรุณาทำตามขั้นตอนด้านล่าง ===")
    print("1. คลิกลิงก์นี้เพื่อเปิดเบราว์เซอร์:")
    print(auth_url)
    print("\n2. ล็อกอินและกดยอมรับสิทธิ์ตามปกติ")
    print("3. เมื่อเสร็จแล้ว หน้าเว็บอาจจะโหลดไม่ขึ้น (Site can't be reached / Localhost refused to connect)")
    print("4. ไม่ต้องตกใจ! ให้ Copy URL ทั้งหมดจากช่อง Address Bar ของเบราว์เซอร์ในหน้านั้นมา")
    
    redirect_response = input("\n5. วาง URL ที่ Copy มาลงที่นี่ แล้วกด Enter: ")

    # ดึงค่า Token จาก URL ที่ผู้ใช้วาง
    flow.fetch_token(authorization_response=redirect_response.strip())
    creds = flow.credentials

    with open(token_path, 'wb') as token:
        pickle.dump(creds, token)
    
    print("\nToken generated successfully!")

if __name__ == '__main__':
    main()