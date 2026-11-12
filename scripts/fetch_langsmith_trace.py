"""Fetch the most recent LangSmith trace for the droneops project (read-only)."""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from langsmith import Client

api_url = os.environ.get("LANGSMITH_ENDPOINT") or None
key = os.environ.get("LANGSMITH_API_KEY")
project = os.environ.get("LANGSMITH_PROJECT", "drone-ops-agent")
print("api_url:", api_url, "project:", project, "key_set:", bool(key))

client = Client(api_url=api_url, api_key=key)
projects = list(client.list_projects(limit=20))
print("projects:", [(p.name, str(p.id)) for p in projects])

runs = list(client.list_runs(project_name=project, limit=10))
print("runs:", len(runs))
for r in runs[:10]:
    print("-", r.name, r.run_type, r.status, r.start_time, "trace_id=", r.trace_id, "id=", r.id)
