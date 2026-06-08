/*
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

function main() {
    var mcpId = context.getVariable("mcp.id") || null;
    var toolsListJson = context.getVariable("mcp.tools_list.value");
    var tools = [];

    if (toolsListJson) {
        try {
            var cleanJson = toolsListJson.replace(/'/g, '"');
            var parsed = JSON.parse(cleanJson);
            tools = parsed.tools || [];
        } catch(e) {
            print("Error parsing tools list: " + e.message);
        }
    }

    var rpcResponse = {
        "jsonrpc": "2.0",
        "id": mcpId,
        "result": {
            "tools": tools
        }
    };

    context.setVariable("response.status.code", "200");
    context.setVariable("response.header.Content-Type", "application/json");
    context.setVariable("response.content", JSON.stringify(rpcResponse, null, 2));
}

main();
