import os
import sys
import argparse
import importlib
import vertexai
from vertexai import types
from vertexai.agent_engines import AdkApp
from google.adk.apps.app import App, ResumabilityConfig

parser = argparse.ArgumentParser(description="Deploy an ADK agent to Agent Runtime.")
parser.add_argument("agent_folder", help="The directory name of the agent to deploy (e.g., simple_agent)")
args = parser.parse_args()
agent_folder = args.agent_folder

# Resolve the package name and distribution directory path
abs_agent_folder = os.path.abspath(agent_folder)
dist_dir = None
package_name = None

if os.path.exists(os.path.join(abs_agent_folder, "pyproject.toml")) or os.path.exists(os.path.join(abs_agent_folder, "setup.py")):
  dist_dir = abs_agent_folder
  dist_name = os.path.basename(abs_agent_folder)
  expected_pkg_name = dist_name.replace("-", "_")
  if os.path.exists(os.path.join(abs_agent_folder, expected_pkg_name)):
    package_name = expected_pkg_name
  else:
    for item in os.listdir(abs_agent_folder):
      item_path = os.path.join(abs_agent_folder, item)
      if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "agent.py")):
        package_name = item
        break
else:
  parent_dir = os.path.dirname(abs_agent_folder)
  if os.path.exists(os.path.join(parent_dir, "pyproject.toml")) or os.path.exists(os.path.join(parent_dir, "setup.py")):
    dist_dir = parent_dir
    package_name = os.path.basename(abs_agent_folder)

if not dist_dir or not package_name:
  dist_dir = abs_agent_folder
  package_name = os.path.basename(abs_agent_folder)

rel_dist_dir = os.path.relpath(dist_dir, os.getcwd())

# Add distribution directory to sys.path to allow correct imports
sys.path.insert(0, dist_dir)

try:
  agent_module = importlib.import_module(f"{package_name}.agent")
  root_agent = agent_module.root_agent
except Exception as e:
  print(f"Error loading agent from '{package_name}.agent': {e}")
  sys.exit(1)

PROJECT_ID=os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION=os.getenv("GOOGLE_CLOUD_LOCATION")
STAGING_BUCKET=os.getenv("STAGING_BUCKET")

# Initialize the Agent Platform client with v1beta1 API for agent identity support
client = vertexai.Client(
  project=PROJECT_ID,
  location=LOCATION,
  http_options=dict(api_version="v1beta1")
)

# Define the App container with resumability enabled
adk_app_container = App(
    name=root_agent.name,
    root_agent=root_agent,
    resumability_config=ResumabilityConfig(is_resumable=True)
)

# Use the proper wrapper class for your Agent Framework
app = AdkApp(app=adk_app_container)

display_name = f"{root_agent.name.replace('_', '-')}"

config = {
  "display_name": display_name,
  "identity_type": types.IdentityType.AGENT_IDENTITY,
  "requirements": [
    "google-cloud-aiplatform[adk,agent_engines]",
    "google-adk>=1.33.0",
    "a2a-sdk>=0.3.4,<0.4.0"
  ],
  "staging_bucket": STAGING_BUCKET,
  "python_version": "3.13",
  "extra_packages": [f"./{rel_dist_dir}"]
}

# Check if the agent is already deployed
existing_agent = None
for a in client.agent_engines.list():
  if a.api_resource.display_name == config["display_name"]:
    existing_agent = a
    break

if existing_agent:
  print(f"Agent '{config['display_name']}' already deployed. Updating: {existing_agent.api_resource.name}")
  remote_app = client.agent_engines.update(
    name=existing_agent.api_resource.name,
    agent=app,
    config=config,
  )
else:
  print(f"Deploying new agent '{config['display_name']}'...")
  remote_app = client.agent_engines.create(
    agent=app,
    config=config,
  )

print(f"Agent deployed successfully. Engine ID: {remote_app.api_resource.name}. Effective Identity: {remote_app.api_resource.spec.effective_identity}")