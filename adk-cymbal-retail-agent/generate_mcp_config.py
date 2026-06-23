# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import yaml
import json
import sys
import os

def parse_oas_to_mcp(spec_path):
    with open(spec_path, 'r') as f:
        spec = yaml.safe_load(f)
    
    servers = spec.get('servers', [])
    default_url = servers[0].get('url', 'https://mocktarget.apigee.net') if servers else 'https://mocktarget.apigee.net'
    
    tools_list = []
    tools_info = {}
    
    paths = spec.get('paths', {})
    for path, path_info in paths.items():
        # Common parameters for all operations under this path
        common_parameters = path_info.get('parameters', [])
        
        for verb, op_info in path_info.items():
            if verb in ['parameters', 'summary', 'description', 'servers']:
                continue
            
            operation_id = op_info.get('operationId')
            if not operation_id:
                # Generate fallback operation ID if missing
                operation_id = f"{verb}_{path.replace('/', '_').strip('_')}"
            
            description = op_info.get('summary') or op_info.get('description') or f"Invokes {verb.upper()} on {path}"
            
            # Extract parameters
            parameters = common_parameters + op_info.get('parameters', [])
            
            path_params = []
            query_params = []
            header_params = []
            
            properties = {}
            required_properties = []
            
            for param in parameters:
                param_name = param.get('name')
                param_in = param.get('in')
                param_required = param.get('required', False)
                param_schema = param.get('schema', {'type': 'string'})
                param_desc = param.get('description', '')
                
                if param_in == 'path':
                    path_params.append(param_name)
                elif param_in == 'query':
                    query_params.append(param_name)
                elif param_in == 'header':
                    header_params.append(param_name)
                
                # Add to inputSchema properties
                properties[param_name] = {
                    'type': param_schema.get('type', 'string'),
                    'description': param_desc
                }
                if param_required:
                    required_properties.append(param_name)
            
            # Handle Request Body for POST/PUT/PATCH
            body_param = None
            payload_schema = None
            content_type = "application/json"
            
            if 'requestBody' in op_info:
                request_body = op_info['requestBody']
                content = request_body.get('content', {})
                for c_type, c_info in content.items():
                    content_type = c_type
                    # Retrieve the schema (ignoring ref expansion for schema wrapper simplification)
                    payload_schema = c_info.get('schema', {})
                    break
                
                # In MCP schema, request body is mapped to a parameter named 'body' or the operationId
                body_param = "body"
                properties[body_param] = {
                    'type': payload_schema.get('type', 'object') if payload_schema else 'object',
                    'description': request_body.get('description', 'Request body payload')
                }
                if request_body.get('required', False):
                    required_properties.append(body_param)
            
            # Build inputSchema matching JSON-RPC tools/list specification
            input_schema = {
                'type': 'object',
                'properties': properties
            }
            if required_properties:
                input_schema['required'] = required_properties
            
            # Append to tools_list
            tools_list.append({
                'name': operation_id,
                'description': description,
                'inputSchema': input_schema
            })
            
            # Build tools_info mapping metadata
            tools_info[operation_id] = {
                'target': {
                    'url': default_url,
                    'pathSuffix': "" if path == "/" else path,
                    'verb': verb.upper(),
                    'headers': {
                        'content-type': content_type,
                        'accept': 'application/json'
                    }
                },
                'schemas': {
                    'request': payload_schema if payload_schema else {}
                },
                'inputParams': {
                    'body': body_param or "",
                    'path': path_params,
                    'query': query_params,
                    'headers': header_params
                }
            }
            
    return tools_list, tools_info

def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_mcp_config.py <spec_file.yaml> <output_dir>")
        sys.exit(1)
        
    spec_file = sys.argv[1]
    output_dir = sys.argv[2]
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    tools_list, tools_info = parse_oas_to_mcp(spec_file)
    
    with open(os.path.join(output_dir, 'tools_list.json'), 'w') as f:
        json.dump({'tools': tools_list}, f, indent=2)
        
    with open(os.path.join(output_dir, 'tools_info.json'), 'w') as f:
        json.dump(tools_info, f, indent=2)
        
    print(f"✅ Successfully generated MCP configs in {output_dir}")

if __name__ == '__main__':
    main()
