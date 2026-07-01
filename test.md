# Hướng dẫn Kiểm thử Thực tế (Real-world Testing Guide)
## Apigee LLM Gateway — Token Limits v2

Tài liệu này hướng dẫn chi tiết cách kiểm thử thực tế hệ thống **Apigee API Proxy (`llm-token-limits-v2`)** đóng vai trò là **LLM Gateway** bảo mật cho mô hình **Gemini 2.5 Flash** trên Vertex AI.

Hướng dẫn này giả lập hai đối tượng thực tế:
1. **Client App (Ứng dụng di động/Web)**: Sử dụng **API Key** để định danh ứng dụng và áp dụng gói dịch vụ (Bronze/Silver).
2. **End-user (Người dùng cuối)**: Sử dụng **Google ID Token (OIDC JWT)** để định danh cá nhân, giúp Apigee đếm và áp dụng hạn mức token riêng biệt cho từng người dùng (Quota per User).

---

## 🛠️ Bước 1: Chuẩn bị thông tin xác thực

Để gửi request thành công qua Apigee LLM Gateway, bạn cần chuẩn bị hai thông tin xác thực sau:

### 1. Lấy Google ID Token (OIDC JWT) của Người dùng
ID Token này đại diện cho danh tính người dùng cuối đã đăng nhập bằng tài khoản Google. Apigee sẽ giải mã token này để lấy trường `sub` (User ID duy nhất) làm khóa định danh bộ đếm Quota.

Chạy lệnh sau trong terminal của bạn (yêu cầu đã cài đặt và đăng nhập `gcloud`):
```bash
# 1. Định nghĩa Audience chính xác được cấu hình trong Apigee VerifyJWT
AUDIENCE="782426757735-7s3966tahaevq86l4k8c7nge4j913bl4.apps.googleusercontent.com"

# 2. Sinh Google ID Token bằng cách impersonate Service Account (để gán Audience tùy chỉnh)
export GOOGLE_ID_TOKEN=$(gcloud auth print-identity-token \
  --impersonate-service-account="vertex-express@retail-agent-demo.iam.gserviceaccount.com" \
  --audiences="$AUDIENCE")

# 3. Kiểm tra token đã sinh
echo $GOOGLE_ID_TOKEN
```

### 2. Lấy API Key từ Apigee Developer App
API Key dùng để xác định ứng dụng của bạn thuộc gói dịch vụ nào:
* **Bronze Key**: Giới hạn **2,000 tokens** mỗi 5 phút.
* **Silver Key**: Giới hạn **5,000 tokens** mỗi 5 phút.

Bạn có thể lấy các Key này từ giao diện quản trị Apigee Console (mục **Apps** thuộc dự án `retail-agent-demo`) hoặc từ kết quả chạy script deploy trước đó.

---

## 🚀 Bước 2: Kiểm thử bằng `cURL` (Giả lập Frontend/Mobile App)

Kịch bản này giả lập một ứng dụng Frontend (React, Flutter, iOS/Android) gọi trực tiếp vào API Gateway của Apigee.

### 1. Thiết lập các biến môi trường kiểm thử
```bash
export APIGEE_HOST="34.144.192.207.nip.io"
export PROJECT_ID="retail-agent-demo"
export REGION="us-central1"
export API_KEY="REPLACE_WITH_YOUR_BRONZE_OR_SILVER_API_KEY"
```

### 2. Thực thi lệnh cURL gửi request đến Gemini 2.5 Flash
```bash
curl -X POST "https://${APIGEE_HOST}/v2/samples/llm-token-limits/v1/projects/${PROJECT_ID}/locations/${REGION}/publishers/google/models/gemini-2.5-flash:generateContent" \
  -H "Content-Type: application/json" \
  -H "x-apikey: ${API_KEY}" \
  -H "Authorization: Bearer ${GOOGLE_ID_TOKEN}" \
  -d '{
    "contents": [
      {
        "role": "user",
        "parts": [
          {
            "text": "Why is the sky blue? Answer in 1 short sentence."
          }
        ]
      }
    ]
  }'
```

### 🎯 Kết quả mong đợi (HTTP 200 OK)
Bạn sẽ nhận được phản hồi chuẩn từ Vertex AI Gemini API. Ở cuối phản hồi sẽ có trường `usageMetadata` chứa số lượng token tiêu thụ thực tế:
```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "text": "The sky is blue because of Rayleigh scattering, where Earth's atmosphere scatters shorter wavelengths of light (blue and violet) more than other colors."
          }
        ],
        "role": "model"
      },
      "finishReason": "STOP",
      "avgLogprobs": -0.12345
    }
  ],
  "usageMetadata": {
    "promptTokenCount": 15,
    "candidatesTokenCount": 28,
    "totalTokenCount": 43
  }
}
```
*Lúc này, Apigee đã tự động trích xuất số `28` (candidatesTokenCount) và cộng dồn vào bộ đếm Quota của User ID tương ứng.*

---

## 🐍 Bước 3: Kiểm thử bằng Python SDK (Giả lập Backend App)

Kịch bản này giả lập một ứng dụng Backend (Django, FastAPI, Node.js) tích hợp mô hình Gemini bằng cách sử dụng thư viện SDK chính thức của Google (`google-genai`), nhưng định tuyến lưu lượng qua Apigee Gateway để kiểm soát bảo mật và hạn mức.

### 1. Cài đặt thư viện Google GenAI SDK
```bash
pip install google-genai
```

### 2. Tạo file script kiểm thử `test_app.py`
```python
import os
from google import genai
from google.genai import types

# 1. Cấu hình thông tin kết nối qua Apigee LLM Gateway
PROJECT_ID = "retail-agent-demo"
LOCATION = "us-central1"
APIGEE_HOST = "34.144.192.207.nip.io"
API_ENDPOINT = f"https://{APIGEE_HOST}/v2/samples/llm-token-limits"

# Lấy API Key và ID Token từ biến môi trường
API_KEY = os.getenv("API_KEY", "REPLACE_WITH_YOUR_API_KEY")
GOOGLE_ID_TOKEN = os.getenv("GOOGLE_ID_TOKEN", "REPLACE_WITH_YOUR_GOOGLE_ID_TOKEN")

# 2. Khởi tạo Client trỏ qua Apigee Gateway bằng cách override base_url
client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
    http_options=types.HttpOptions(
        api_version='v1', 
        base_url=API_ENDPOINT, 
        headers={
            "x-apikey": API_KEY,
            "Authorization": f"Bearer {GOOGLE_ID_TOKEN}"
        }
    )
)

# 3. Gọi mô hình Gemini 2.5 Flash
try:
    print("--- Đang gửi yêu cầu tới Gemini qua Apigee Gateway ---")
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents="What is the capital of France?"
    )
    print("\n[Thành công] Phản hồi từ mô hình:")
    print(response.text)
    
    if response.usage_metadata:
        print(f"\n[Thống kê Token]:")
        print(f"- Prompt Tokens: {response.usage_metadata.prompt_token_count}")
        print(f"- Response Tokens: {response.usage_metadata.candidates_token_count}")
        print(f"- Total Tokens: {response.usage_metadata.total_token_count}")
except Exception as e:
    print(f"\n[Lỗi] Không thể gọi API: {e}")
```

---

## 🛑 Bước 4: Kiểm thử kịch bản vượt ngưỡng Quota (Rate Limiting)

Để xác nhận chính sách chặn Quota hoạt động chính xác, chúng ta sẽ giả lập hành vi gửi liên tiếp các câu hỏi dài để vượt ngưỡng giới hạn **2,000 tokens** của gói **Bronze**.

### Tạo file script kiểm thử Quota `test_quota.py`
```python
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
            print(f"\n[BỊ CHẶN THÀNH CÔNG] Yêu cầu {i} đã bị chặn chính xác bởi Apigee LLM Gateway!")
            details = getattr(e, "details", None)
            code = getattr(e, "code", None)
            if isinstance(details, dict):
                fault = details.get("fault", {})
                faultstring = fault.get("faultstring", "")
                errorcode = fault.get("detail", {}).get("errorcode", "")
                print(f"- HTTP Status Code: {code}")
                print(f"- Fault String: {faultstring}")
                print(f"- Error Code: {errorcode}")
            else:
                print(f"- Chi tiết lỗi: {e}")
        else:
            import traceback
            traceback.print_exc()
            print(f"\n❌ [LỖI THỬ NGHIỆM] Yêu cầu {i} thất bại do lỗi khác (không phải lỗi Quota):")
            print(e)
        break
```

### 🎯 Kết quả mong đợi khi chạy `test_quota.py`
* **Yêu cầu 1**: Thành công, tổng số token tích lũy đạt khoảng ~1,200 - 1,500 tokens (hoặc vượt ngưỡng 2,000 tokens ngay lập tức nếu câu trả lời của Gemini rất dài).
* **Yêu cầu tiếp theo**: Sẽ bị Apigee chặn ngay lập tức ở đầu vào (PreFlow) và trả về lỗi **`HTTP 429`** kèm thông báo lỗi Quota từ Apigee:
  ```
  [BỊ CHẶN THÀNH CÔNG] Yêu cầu 2 đã bị chặn chính xác bởi Apigee LLM Gateway!
  - HTTP Status Code: 429
  - Fault String: Rate limit LLM Token quota violation. Quota limit exceeded. Identifier : 100912709467197734190
  - Error Code: policies.llmtokenquota.LLMTokenQuotaViolation
  ```

---

## 🔍 Bước 5: Giám sát trực quan bằng Apigee Debug (Trace)

Để xem chi tiết cách Apigee xử lý từng bước xác thực và đếm token:

1. Đăng nhập vào **Apigee Console**.
2. Đi tới mục **API Proxies** -> Chọn **`llm-token-limits-v2`**.
3. Chuyển sang tab **Debug** (hoặc **Trace**).
4. Chọn môi trường `eval` và bấm **Start Debug Session**.
5. Gửi request bằng cURL hoặc chạy script Python.
6. Bạn sẽ thấy luồng xử lý trực quan:
   * **`VA-VerifyAPIKey`**: Xác thực API Key thành công và lấy thông tin gói dịch vụ (Bronze/Silver).
   * **`JWT-VerifyGoogleIdToken`**: Giải mã ID Token thành công, hiển thị các trường claim như `sub` (User ID) và `email`.
   * **`LTQ-TokenEnforce`**: Kiểm tra bộ đếm Quota hiện tại của User ID đó có vượt ngưỡng cho phép của gói Product hay không.
   * **`LTQ-TokenCount`**: (Ở chiều phản hồi) Đọc trường `usageMetadata.candidatesTokenCount` từ JSON trả về của Vertex AI và cộng dồn vào bộ đếm Quota trong cache.

---

## ❌ Xử lý lỗi thường gặp (Troubleshooting)

| Mã lỗi / Tên lỗi | Nguyên nhân | Cách khắc phục |
|------------------|--------------|----------------|
| **`steps.jwt.InvalidToken`** | ID Token bị hết hạn, sai Audience, hoặc truyền sai định dạng Bearer. | 1. Sinh lại ID Token mới bằng lệnh `gcloud`. <br>2. Đảm bảo truyền đúng Audience (`782426757735-7s3966tahaevq86l4k8c7nge4j913bl4.apps.googleusercontent.com`). <br>3. Đảm bảo header có định dạng `Authorization: Bearer <TOKEN>`. |
| **`QuotaExceeded` (HTTP 429)** | Người dùng đã tiêu thụ vượt quá số lượng token cho phép trong chu kỳ 5 phút. | Đợi hết chu kỳ 5 phút để bộ đếm reset, hoặc chuyển sang sử dụng **Silver API Key** để có hạn mức cao hơn (5,000 tokens). |
| **`GoogleTokenGenerationFailure`** | Apigee Service Account thiếu quyền sinh token để gọi Vertex AI backend. | Đảm bảo Apigee Service Agent (`service-782426757735@gcp-sa-apigee.iam.gserviceaccount.com`) đã được cấp quyền `Service Account Token Creator` trên Service Account `vertex-express@retail-agent-demo.iam.gserviceaccount.com`. |
| **`400 FAILED_PRECONDITION`** | Vùng (Region) được chọn chưa hỗ trợ mô hình Gemini 2.5 Flash. | Đảm bảo sử dụng vùng `us-central1` trong URL gọi API. |
