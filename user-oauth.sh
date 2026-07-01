AUDIENCE="782426757735-7s3966tahaevq86l4k8c7nge4j913bl4.apps.googleusercontent.com"

# 1. Lấy prompt từ tham số truyền vào (mặc định nếu không truyền)
PROMPT="${1:-Why is the sky blue? Answer in 1 short sentence.}"

# 2. Sinh Google ID Token bằng cách impersonate Service Account
export GOOGLE_ID_TOKEN=$(gcloud auth print-identity-token \
  --impersonate-service-account="vertex-express@retail-agent-demo.iam.gserviceaccount.com" \
  --audiences="$AUDIENCE")

export APIGEE_HOST="34.144.192.207.nip.io"
export PROJECT_ID="retail-agent-demo"
export REGION="us-central1"
export API_KEY="bwR35AAXN2zayoU9qnwL8RhqTYmh7q13siGzgvzAgL5rdXH3"

# 3. Tạo JSON payload an toàn bằng jq để tránh lỗi ký tự đặc biệt
PAYLOAD=$(jq -n --arg prompt "$PROMPT" '{
  contents: [
    {
      role: "user",
      parts: [
        {
          text: $prompt
        }
      ]
    }
  ]
}')

# 4. Gửi request tới Apigee LLM Gateway
curl -X POST "https://${APIGEE_HOST}/v2/samples/llm-token-limits/v1/projects/${PROJECT_ID}/locations/${REGION}/publishers/google/models/gemini-2.5-flash:generateContent" \
  -H "Content-Type: application/json" \
  -H "x-apikey: ${API_KEY}" \
  -H "Authorization: Bearer ${GOOGLE_ID_TOKEN}" \
  -d "$PAYLOAD"