"""Run the documented examples in each shell, capturing native arguments offline."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "skills/github-repo-setup/references/github-operations.md"


class ShellExamples(unittest.TestCase):
    def exercise(self, dialect, executable):
        if not executable:
            self.skipTest(f"{dialect} shell unavailable")
        pattern = r"<!-- shell-test:" + dialect + r" -->\n```[^\n]*\n(.*?)\n```"
        snippet = re.search(pattern, DOC.read_text(encoding="utf-8"), re.S)[1]
        with tempfile.TemporaryDirectory(prefix="workflow-shell-") as directory:
            root = Path(directory)
            log = root / "argv.jsonl"
            capture = root / "capture.py"
            capture.write_text("import json,sys\nwith open(sys.argv[1], 'a', encoding='utf-8') as stream:\n stream.write(json.dumps(sys.argv[2:]) + '\\n')\n", encoding="utf-8")
            environment = os.environ.copy()
            environment.update(CAPTURE_PYTHON=sys.executable.replace("\\", "/"), CAPTURE_HELPER=capture.as_posix(), CAPTURE_LOG=log.as_posix())
            if dialect == "powershell":
                stub = 'function gh { & $env:CAPTURE_PYTHON $env:CAPTURE_HELPER $env:CAPTURE_LOG @args; if ($LASTEXITCODE -ne 0) { throw "Capture failed" } }\n'
                command = [executable, "-NoProfile", "-NonInteractive", "-Command", stub + snippet]
            else:
                stub = 'gh() { "$CAPTURE_PYTHON" "$CAPTURE_HELPER" "$CAPTURE_LOG" "$@"; }\n'
                command = [executable, "-c", "set -eu\n" + stub + snippet]
            result = subprocess.run(command, cwd=directory, env=environment, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(calls, [
                ["repo", "view", "github.com/OWNER/REPOSITORY", "--json", "nameWithOwner,url,viewerPermission,defaultBranchRef"],
                ["api", "--hostname", "github.com", "graphql", "-f", "query=query($id:ID!){node(id:$id){id}}", "-f", "id=PROJECT_NODE_ID"],
            ])

    def test_windows_powershell_arguments(self):
        self.exercise("powershell", shutil.which("powershell") or shutil.which("pwsh"))

    def test_posix_arguments(self):
        # Avoid the Windows WSL launcher when a real Git Bash is available.
        candidate = Path(os.environ.get("ProgramFiles", "")) / "Git/bin/bash.exe"
        shell = str(candidate) if os.name == "nt" and candidate.is_file() else shutil.which("sh")
        self.exercise("posix", shell)


if __name__ == "__main__":
    unittest.main()
