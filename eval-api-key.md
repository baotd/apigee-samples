2. Tổng kết các tài nguyên đã triển khai trên retail-agent-demo
- API Proxy: llm-token-limits-v2 (Revision 2) — Đã deploy thành công và ở trạng thái READY.
- API Endpoint: https://eval-group/v2/samples/llm-token-limits
- API Products:
- ai-product-bronze-v2 (Hạn mức: 2000 tokens / 5 phút)
- ai-product-silver-v2 (Hạn mức: 5000 tokens / 5 phút)
- Developer App: ai-consumer-app-v2
- BRONZE API Key: bwR35AAXN2zayoU9qnwL8RhqTYmh7q13siGzgvzAgL5rdXH3
- SILVER API Key: MCAsN2KsqgGZDZ8v7lH2e9ei9o9RY6A4thObMpYy1EwTXUxT
- Analytics & Reports:
- Đã tạo Data Collector dc_enduser_id_v2 để lưu trữ email người dùng Google.
- Đã tạo báo cáo tùy chỉnh Tokens Consumption Report v2 trên Apigee Analytics để theo dõi lượng tiêu thụ token theo từng email người dùng.
3. Hướng dẫn kiểm thử nhanh bằng cURL
Bạn có thể chạy lệnh dưới đây trong terminal của mình để kiểm tra hoạt động của hệ thống:
# 1. Lấy Google ID Token của bạn
ID_TOKEN=$(gcloud auth print-identity-token)

# 2. Gọi API qua Apigee Proxy
curl -X POST "https://34.144.192.207.nip.io/v2/samples/llm-token-limits/v1/projects/retail-agent-demo/locations/asia-southeast2/publishers/google/models/gemini-2.5-flash:generateContent" \
  -H "x-apikey: bwR35AAXN2zayoU9qnwL8RhqTYmh7q13siGzgvzAgL5rdXH3" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{
      "parts": [{
        "text": "Hãy viết một câu chào ngắn gọn."
      }]
    }]
  }'
Hệ thống đã sẵn sàng hoạt động ở cấp độ production với đầy đủ tính năng bảo mật xác thực Google Identity và quản lý hạn mức token theo từng người dùng cuối!