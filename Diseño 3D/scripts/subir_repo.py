"""Sube una carpeta a un repo de GitHub en un solo commit usando 'gh api' (no hace falta git)."""
import base64, json, os, subprocess, sys

GH = r"C:\Users\diazr\AppData\Local\Microsoft\WinGet\Packages\GitHub.cli_Microsoft.Winget.Source_8wekyb3d8bbwe\bin\gh.exe"
ROOT, REPO, MSG = sys.argv[1], sys.argv[2], sys.argv[3]
EXCLUIR_DIR = {"__pycache__", ".git"}
EXCLUIR_EXT = {".zip", ".pyc"}


def api(method, path, body=None):
    r = subprocess.run([GH, "api", "-X", method, path, "--input", "-"], input=json.dumps(body or {}).encode(),
                       capture_output=True)
    if r.returncode:
        raise RuntimeError(f"{method} {path}: {r.stdout.decode(errors='ignore')[:300]} {r.stderr.decode(errors='ignore')[:300]}")
    return json.loads(r.stdout or b"{}")


archivos = []
for d, dirs, fs in os.walk(ROOT):
    dirs[:] = [x for x in dirs if x not in EXCLUIR_DIR]
    for f in fs:
        if os.path.splitext(f)[1].lower() in EXCLUIR_EXT or f.startswith("~$"):
            continue
        archivos.append(os.path.join(d, f))

ref = api("GET", f"repos/{REPO}/git/ref/heads/main")
base = ref["object"]["sha"]
base_tree = api("GET", f"repos/{REPO}/git/commits/{base}")["tree"]["sha"]
tree = []
for p in archivos:
    rel = os.path.relpath(p, ROOT).replace("\\", "/")
    blob = api("POST", f"repos/{REPO}/git/blobs", {"content": base64.b64encode(open(p, "rb").read()).decode(), "encoding": "base64"})
    tree.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    print("  +", rel, flush=True)
t = api("POST", f"repos/{REPO}/git/trees", {"base_tree": base_tree, "tree": tree})
c = api("POST", f"repos/{REPO}/git/commits", {"message": MSG, "tree": t["sha"], "parents": [base],
                                              "author": {"name": "Juan Camilo Díaz Rangel",
                                                         "email": "123338842+hulldrapro@users.noreply.github.com"}})
api("PATCH", f"repos/{REPO}/git/refs/heads/main", {"sha": c["sha"]})
print("commit", c["sha"][:7], len(tree), "archivos")
