#!/bin/bash

# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# 1. Lấy prompt từ tham số truyền vào (mặc định nếu không truyền)
PROMPT="${1:-Why is the sky blue? Answer in 1 short sentence.}"

# 2. Kiểm tra API Key từ biến môi trường hoặc yêu cầu nhập vào
if [ -z "$API_KEY" ]; then
  echo -n "Vui lòng nhập API Key từ Self-Service Portal: "
  read -s API_KEY
  echo ""
fi

if [ -z "$API_KEY" ]; then
  echo "Lỗi: API Key không được để trống."
  exit 1
fi

export APIGEE_HOST="34.144.192.207.nip.io"
export PROJECT_ID="retail-agent-demo"
export REGION="us-central1"

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

echo "--- Đang gửi yêu cầu tới Gemini qua Apigee LLM Gateway (Chỉ dùng API Key) ---"
echo "Câu hỏi: $PROMPT"
echo ""

# 4. Gửi request tới Apigee LLM Gateway (Không truyền Authorization header)
curl -i -X POST "https://${APIGEE_HOST}/v2/samples/llm-token-limits/v1/projects/${PROJECT_ID}/locations/${REGION}/publishers/google/models/gemini-2.5-flash:generateContent" \
  -H "Content-Type: application/json" \
  -H "x-apikey: ${API_KEY}" \
  -d "$PAYLOAD"
