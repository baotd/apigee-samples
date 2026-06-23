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

import os
import sys
import json
import subprocess
from generate_mcp_config import parse_oas_to_mcp

def run_cmd(args):
    print(f"Running: {' '.join(args)}")
    res = subprocess.run(args, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Stderr: {res.stderr}")
    return res

def main():
    org = os.getenv("PROJECT_ID")
    env = os.getenv("APIGEE_ENV", "eval")
    token = os.getenv("TOKEN")
    
    if not org or not token:
        print("Error: PROJECT_ID and TOKEN environment variables must be set.")
        sys.exit(1)
        
    apigeecli_path = os.path.expanduser("~/.apigeecli/bin/apigeecli")
    if not os.path.exists(apigeecli_path):
        apigeecli_path = "apigeecli" # fallback to PATH
        
    map_name = "MCP-Configs"
    
    # 1. Create KVM map (ignore error if it already exists)
    create_map_cmd = [
        apigeecli_path, "kvms", "create",
        "--name", map_name,
        "--env", env,
        "--org", org,
        "--token", token
    ]
    run_cmd(create_map_cmd)
    
    # Define specs to parse and load
    specs = {
        "customers": "config/customers/customers.yaml",
        "orders": "config/orders/orders.yaml",
        "shipping": "config/shipping/shipping.yaml",
        "returns": "config/returns/returns.yaml"
    }
    
    for service, spec_path in specs.items():
        if not os.path.exists(spec_path):
            print(f"Skipping {service}: spec path {spec_path} not found.")
            continue
            
        print(f"Parsing spec: {spec_path}")
        tools_list_obj, tools_info_obj = parse_oas_to_mcp(spec_path)
        
        tools_list_str = json.dumps({'tools': tools_list_obj}).replace('"', "'")
        tools_info_str = json.dumps(tools_info_obj).replace('"', "'")
        
        # Keys matching AM-BuildKVMKeys template
        list_key = f"{service}_tools_list"
        info_key = f"{service}_tools_info"
        
        # Load tools list
        # Try to delete first to ensure we write fresh value, or create/update
        delete_list_entry = [
            apigeecli_path, "kvms", "entries", "delete",
            "--map", map_name,
            "--key", list_key,
            "--env", env,
            "--org", org,
            "--token", token
        ]
        run_cmd(delete_list_entry)
        
        create_list_entry = [
            apigeecli_path, "kvms", "entries", "create",
            "--map", map_name,
            "--key", list_key,
            "--value", tools_list_str,
            "--env", env,
            "--org", org,
            "--token", token
        ]
        run_cmd(create_list_entry)
        
        # Load tools info
        delete_info_entry = [
            apigeecli_path, "kvms", "entries", "delete",
            "--map", map_name,
            "--key", info_key,
            "--env", env,
            "--org", org,
            "--token", token
        ]
        run_cmd(delete_info_entry)
        
        create_info_entry = [
            apigeecli_path, "kvms", "entries", "create",
            "--map", map_name,
            "--key", info_key,
            "--value", tools_info_str,
            "--env", env,
            "--org", org,
            "--token", token
        ]
        run_cmd(create_info_entry)
        
    print("✅ MCP KVM Configurations successfully deployed!")

if __name__ == '__main__':
    main()
