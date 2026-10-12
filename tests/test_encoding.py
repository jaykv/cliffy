"""Manifests and generated code are UTF-8, whatever the locale of the terminal is."""

import os
import subprocess
import sys


def run_in_c_locale(code: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Runs code in an interpreter whose locale encoding cannot encode non-ASCII text"""
    env = {**os.environ, "LC_ALL": "C", "LANG": "C", "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"}
    return subprocess.run([sys.executable, "-c", code, *args], env=env, capture_output=True, text=True)


def test_write_to_file_does_not_depend_on_locale(tmp_path):
    # `cli load` printed a traceback for any manifest with an emoji in a help text when LANG was C / POSIX
    output_path = tmp_path / "generated.py"
    code = "import sys; from cliffy.helper import write_to_file; write_to_file(sys.argv[1], 'x = \"\\u2728\"')"

    result = run_in_c_locale(code, str(output_path))

    assert result.returncode == 0, result.stderr
    assert output_path.read_bytes() == 'x = "✨"'.encode()


def test_manifest_is_read_as_utf8_whatever_the_locale(tmp_path):
    manifest_path = tmp_path / "manifest.yaml"
    manifest_path.write_bytes("name: uni\nversion: '1'\nhelp: héllo ✨\ncommands:\n  a: print(1)\n".encode())
    code = (
        "import sys; from cliffy.transformer import Transformer\n"
        "with open(sys.argv[1], encoding='utf-8') as f: T = Transformer(f, validate_requires=False)\n"
        "assert T.manifest.help == 'h\\xe9llo \\u2728', ascii(T.manifest.help)"
    )

    result = run_in_c_locale(code, str(manifest_path))

    assert result.returncode == 0, result.stderr
