import os
import time
import subprocess
import google.auth.credentials
from google import genai
from google.genai import types

PROJECT_ID = "retail-agent-demo"
LOCATION = "us-central1"
APIGEE_HOST = "34.144.192.207.nip.io"
API_ENDPOINT = f"https://{APIGEE_HOST}/v2/samples/llm-token-limits"

# BẮT BUỘC: Sử dụng Bronze API Key để dễ dàng vượt ngưỡng 2000 tokens
API_KEY = "bwR35AAXN2zayoU9qnwL8RhqTYmh7q13siGzgvzAgL5rdXH3" 

# Tự động sinh GOOGLE_ID_TOKEN nếu chưa được set trong môi trường
GOOGLE_ID_TOKEN = os.getenv("GOOGLE_ID_TOKEN")
if not GOOGLE_ID_TOKEN:
    print("GOOGLE_ID_TOKEN không tìm thấy trong môi trường. Đang tự động sinh token bằng gcloud...")
    try:
        AUDIENCE = "782426757735-7s3966tahaevq86l4k8c7nge4j913bl4.apps.googleusercontent.com"
        SA = "vertex-express@retail-agent-demo.iam.gserviceaccount.com"
        cmd = [
            "gcloud", "auth", "print-identity-token",
            f"--impersonate-service-account={SA}",
            f"--audiences={AUDIENCE}"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        GOOGLE_ID_TOKEN = result.stdout.strip()
        print("Tự động sinh GOOGLE_ID_TOKEN thành công!")
    except Exception as e:
        print(f"Lỗi khi tự động sinh token bằng gcloud: {e}")
        print("Vui lòng đảm bảo bạn đã đăng nhập gcloud và có quyền impersonate SA.")
        GOOGLE_ID_TOKEN = "REPLACE_WITH_YOUR_GOOGLE_ID_TOKEN"

# Định nghĩa lớp Credentials tùy chỉnh để truyền ID Token vào Authorization header
# Tránh việc google-genai SDK tự động ghi đè bằng Access Token mặc định
class ApigeeIDTokenCredentials(google.auth.credentials.Credentials):
    def __init__(self, id_token):
        super().__init__()
        self.token = id_token

    def refresh(self, request):
        pass

creds = ApigeeIDTokenCredentials(GOOGLE_ID_TOKEN)

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
    credentials=creds,
    http_options=types.HttpOptions(
        api_version='v1', 
        base_url=API_ENDPOINT, 
        headers={
            "x-apikey": API_KEY
        }
    )
)

# Danh sách các câu hỏi dài nhằm tiêu tốn nhiều token phản hồi nhất có thể
prompts = [
    "Why is the sky blue? Provide a very long, detailed, and exhaustive explanation like a science journal.",
    "Explain the physics of rainbows in extreme detail, with mathematical concepts.",
    "Write a long essay about the history of quantum mechanics and its key founders.",
    "Describe the working principle of a nuclear reactor in a very long and deep explanation."
]

print("\n--- Bắt đầu gửi các request liên tục để kích hoạt chặn Quota ---")
total_tokens_used = 0

for i, prompt in enumerate(prompts, 1):
    try:
        print(f"\n[Yêu cầu {i}] Đang gửi câu hỏi...")
        start_time = time.time()
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=prompt
        )
        duration = time.time() - start_time
        print(f"[Thành công] Nhận phản hồi sau {duration:.2f} giây.")
        
        if response.usage_metadata:
            tokens = response.usage_metadata.total_token_count
            total_tokens_used += tokens
            print(f"-> Token tiêu thụ trong request này: {tokens}")
            print(f"-> Tổng tích lũy hiện tại: {total_tokens_used} / 2000 tokens")
            
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Quota Exceeded" in error_msg:
            print(f"\n[BỊ CHẶN THÀNH CÔNG] Lỗi xảy ra ở yêu cầu {i}:")
            print(e)
            print("\n🎉 Tuyệt vời! Hệ thống đã chặn chính xác khi vượt quá hạn mức 2000 tokens của gói Bronze!")
        else:
            import traceback
            traceback.print_exc()
            print(f"\n❌ [LỖI THỬ NGHIỆM] Yêu cầu {i} thất bại do lỗi khác (không phải lỗi Quota):")
            print(e)
        break
