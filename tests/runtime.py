"""Load the exact implementation shipped in the installable skill."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/github-repo-setup/scripts"))
from github_workflow import GitHub, GitHubFailure, Workflow, failure_category  # noqa: E402,F401
