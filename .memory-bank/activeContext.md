# Required Skills
- gcp-backend

**Core Objective**
Triển khai Apigee API Proxy (`llm-token-limits-v2`) tích hợp xác thực **Google Identity (ID Token JWT)** để quản lý hạn mức tiêu thụ token LLM (quota per user) trên môi trường Apigee eval thuộc dự án `retail-agent-demo`, sử dụng các thông số môi trường đã được cấu hình sẵn trong file `.env` ở thư mục gốc.

**Industry Baseline**
- **OAuth 2.0 & OIDC (OpenID Connect)** — Sử dụng Google ID Token làm phương thức định danh người dùng cuối bảo mật và phi tập trung.
- **AI Gateway Pattern** — Sử dụng chính sách chuyên dụng `<LLMTokenQuota>` của Apigee để đếm và áp dụng hạn mức token trực tiếp từ response payload của LLM.

**Architecture Decisions**

| Decision | Type | Rationale |
|----------|------|-----------|
| Xác thực Google ID Token bằng `VerifyJWT` | `[STANDARD]` | Xác thực offline cực nhanh bằng cách cache JWKS từ Google, không tốn thêm network call sang Google API. |
| Sử dụng `LLMTokenQuota` thay vì `Quota` | `[STANDARD]` | Chính sách chuyên dụng cho AI giúp đơn giản hóa proxy, tự động parse JSON response để đếm token. |
| Kết hợp API Key + JWT | `[STANDARD]` | API Key định danh Client App (lấy quota limit từ API Product), JWT định danh End-User (để phân chia quota per user). |

**Target Branch:** main

**Tech Stack**
- Gateway: Apigee X (môi trường eval trên dự án `retail-agent-demo`)
- Backend: Vertex AI Gemini API
- CLI Tools: `apigeecli`, `gcloud`

**System Design**

*Data Models / Schema Changes*
```
Data Collector: dc_enduser_id_v2 (STRING) — Lưu trữ email của người dùng Google để phục vụ báo cáo Analytics.
Custom Report: tokens-consumption-report-v2 — Báo cáo lượng tiêu thụ token gom nhóm theo api_product, developer_app và dc_enduser_id_v2.
```

*API Specifications*
```
POST /v2/samples/llm-token-limits/v1/projects/retail-agent-demo/locations/us-central1/publishers/google/models/gemini-2.5-flash:generateContent
Auth:     API Key (x-apikey header) + Google ID Token (Authorization Bearer header)
Request:  Vertex AI Gemini request body
Response: Vertex AI Gemini response body (chứa usageMetadata)
```

**Implementation Breakdown (File-by-File)**

| File | Action | Specific Changes |
|------|--------|-----------------|
| `llm-token-limits-v2/apiproxy/policies/JWT-VerifyGoogleIdToken.xml` | Create | Tạo chính sách `VerifyJWT` để xác thực Google ID Token từ header `Authorization` sử dụng Google JWKS. |
| `llm-token-limits-v2/apiproxy/proxies/default.xml` | Modify | Thêm bước `JWT-VerifyGoogleIdToken` vào PreFlow ngay sau `VA-VerifyAPIKey`. |
| `llm-token-limits-v2/apiproxy/policies/LTQ-TokenEnforce.xml` | Modify | Thêm thẻ `<Identifier ref="jwt.JWT-VerifyGoogleIdToken.decoded.claim.sub"/>` để áp dụng hạn mức theo từng user ID của Google. |
| `llm-token-limits-v2/apiproxy/policies/LTQ-TokenCount.xml` | Modify | Thêm thẻ `<Identifier ref="jwt.JWT-VerifyGoogleIdToken.decoded.claim.sub"/>` để đếm token theo từng user ID của Google. |
| `llm-token-limits-v2/apiproxy/policies/DC-CollectTokenCounts.xml` | Modify | Thêm thẻ `<Capture>` để ghi nhận `jwt.JWT-VerifyGoogleIdToken.decoded.claim.email` vào Data Collector `dc_enduser_id_v2`. |
| `llm-token-limits-v2/deploy-llm-token-limits-v2.sh` | Modify | 1. Thêm bước tự động load `.env` ở root và map `PROJECT_ID` sang `PROJECT`. <br>2. Tạo Data Collector `dc_enduser_id_v2` và đưa nó vào chiều (dimension) của Custom Report. |

**TDD Specifications**

*Suite-1 — Unit Tests*
N/A (Apigee Proxy deployment and integration testing)

*Suite-2 — Integration / Acceptance Tests*
- Scenario 1: Verify Google ID Token successfully and apply Quota.
- Scenario 2: Block request when Quota is exceeded.
- Scenario 3: Block request when Google ID Token is invalid or expired.

*Suite-3 — User Acceptance Tests (UAT)*
N/A

**Execution Sequence**
1. Tạo chính sách `JWT-VerifyGoogleIdToken.xml` và cập nhật các chính sách Quota, Data Capture, Proxy Endpoint.
2. Cập nhật script `deploy-llm-token-limits-v2.sh` để tự động đọc file `.env` ở root và map `PROJECT_ID` sang `PROJECT`.
3. Chạy script để deploy toàn bộ tài nguyên lên Apigee.

**Tasks**
- [x] Task 1: Tạo chính sách `JWT-VerifyGoogleIdToken.xml` trong `llm-token-limits-v2/apiproxy/policies/`
- [x] Task 2: Cập nhật `proxies/default.xml` để tích hợp bước xác thực JWT
- [x] Task 3: Cập nhật `LTQ-TokenEnforce.xml` và `LTQ-TokenCount.xml` để thêm `<Identifier>` định danh user
- [x] Task 4: Cập nhật `DC-CollectTokenCounts.xml` để capture email người dùng Google
- [x] Task 5: Cập nhật script `deploy-llm-token-limits-v2.sh` để tự động load `.env` ở root, tạo Data Collector mới và Custom Report nâng cao
- [x] Task 6: Thực thi deploy lên dự án `retail-agent-demo`

**Deployment Target**
- Provider: Google Cloud Platform (GCP)
- Environment: Apigee Eval (`eval` trên dự án `retail-agent-demo`)
- Region: `us-central1` (Iowa)

**Risk Register**
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Google JWKS thay đổi hoặc không truy cập được | Low | High | Apigee tự động cache JWKS cục bộ để tránh gọi mạng liên tục và xử lý lỗi kết nối thông minh. |
| Trùng lặp tên Data Collector nếu đã tồn tại | Medium | Low | Thêm cờ bỏ qua lỗi hoặc kiểm tra sự tồn tại của Data Collector trước khi tạo trong script. |

**Definition of Done**
- [x] Toàn bộ các file cấu hình proxy được cập nhật chính xác.
- [x] Proxy được import và deploy thành công lên Apigee mà không có lỗi biên dịch.
- [x] Các API Products, Developer, và Developer App được khởi tạo thành công.
- [x] Custom Report được tạo thành công trên Apigee Analytics.

**Assumptions**
- Dự án `retail-agent-demo` đã được bật các API cần thiết (Apigee API, Vertex AI API).
- Bạn đã có quyền `Apigee Organization Admin` hoặc quyền tương đương trên dự án GCP này để tạo tài nguyên.

---
Current Phase: DONE
Last Action: Đã hoàn thành triển khai toàn bộ tài nguyên lên Apigee, sửa lỗi bóc tách Bearer, tích hợp Google Authentication với Service Account, cập nhật mô hình lên Gemini 2.5 Flash tại vùng us-central1 và kiểm thử thành công 100%.
