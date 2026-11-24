import os
import subprocess
import sys


def test_papa_grades_offline_on_a_machine_without_nltk_data(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("The report was written by the team.\n")
    blocked = "http://127.0.0.1:9"
    env = {"PATH": os.environ["PATH"], "HOME": str(tmp_path), "PYTHONPATH": os.pathsep.join(sys.path),
           "https_proxy": blocked, "HTTPS_PROXY": blocked, "http_proxy": blocked, "HTTP_PROXY": blocked}
    result = subprocess.run([sys.executable, "-m", "papa", str(doc), "--report", "concise"],
                            capture_output=True, text=True, env=env, timeout=120)
    assert result.returncode == 0, result.stderr[-500:]
    assert "nltk_data" not in result.stderr
    assert "Passive voice: 'was written'" in result.stdout
