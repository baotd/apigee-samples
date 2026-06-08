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

var mcpToolsInfoJson = context.getVariable("mcp.tool_configs.value");
var mcpToolsInfo = {};

if (mcpToolsInfoJson) {
    try {
        var cleanJson = mcpToolsInfoJson.replace(/'/g, '"');
        mcpToolsInfo = JSON.parse(cleanJson);
        // Ensure APIGEE_HOST placeholder is resolved to actual hostname if present
        var apigeeHost = context.getVariable("request.header.host");
        for (var toolName in mcpToolsInfo) {
            if (mcpToolsInfo.hasOwnProperty(toolName)) {
                var targetUrl = mcpToolsInfo[toolName].target.url;
                if (targetUrl.indexOf("APIGEE_HOST") !== -1 && apigeeHost) {
                    mcpToolsInfo[toolName].target.url = targetUrl.replace("APIGEE_HOST", apigeeHost);
                }
            }
        }
    } catch(e) {
        print("Error parsing mcpToolsInfo: " + e.message);
    }
}
