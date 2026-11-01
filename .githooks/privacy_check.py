"""Pre-push privacy check for this public repo.

Blocks a push when the outgoing commits contain personal information:
  1. author / committer emails other than this repo's local user.email or GitHub noreply
  2. added lines (text files, and best-effort for binaries) that match a generic pattern
     (email address, user-profile path) or any regex in the local denylist file

The denylist file is gitignored on purpose: the keywords themselves are private.
Enable once per clone:  git config core.hooksPath .githooks
Bypass deliberately:    git push --no-verify
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ZERO = "0" * 40
NOREPLY = re.compile(r"(@users\.noreply\.github\.com|^noreply@github\.com)$", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
USER_PATH = re.compile(r"(?i)(?:\b[A-Z]:[\\/]+Users[\\/]+|/[a-z]/Users/|/home/)[^\\/\s\"'<>]+")
# Tracked, public exceptions (e.g. paper authors' published emails), regex per line.
ALLOWLIST = ".githooks/privacy-allow.txt"
# This checker's own source contains the patterns above; scanning it only self-matches.
SKIP = {".githooks/privacy_check.py"}


def git(repo, *args, binary=False):
    out = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=off", *args],
                         capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode("utf-8", "replace")


def outgoing_commits(repo, remote, refs_text):
    commits = []
    for line in refs_text.splitlines():
        parts = line.split()
        if len(parts) != 4 or parts[1] == ZERO:  # malformed, or a branch deletion
            continue
        local_sha, remote_sha = parts[1], parts[3]
        try:
            if remote_sha == ZERO:
                raise subprocess.CalledProcessError(1, "new branch")
            revs = git(repo, "rev-list", f"{remote_sha}..{local_sha}")
        except subprocess.CalledProcessError:
            revs = git(repo, "rev-list", local_sha, "--not", f"--remotes={remote}")
        commits += [c for c in revs.split() if c not in commits]
    return commits


def load_denylist(path):
    if not path.is_file():
        return []
    patterns = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if raw and not raw.startswith("#"):
            patterns.append(re.compile(raw, re.I))
    return patterns


def scan_text(text, allowed_emails, denylist, allow, emails=True):
    hits = []
    if emails:
        for m in EMAIL.finditer(text):
            if m.group(0).lower() not in allowed_emails and not NOREPLY.search(m.group(0)):
                hits.append(("email", m.group(0)))
    for m in USER_PATH.finditer(text):
        hits.append(("user path", m.group(0)))
    for pat in denylist:
        for m in pat.finditer(text):
            hits.append(("denylist", m.group(0)))
    return [h for h in hits if not any(a.fullmatch(h[1]) for a in allow)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--remote", default="origin", help="remote name (git passes it as $1)")
    ap.add_argument("--repo", default=".", help="repository root")
    ap.add_argument("--denylist", default=".privacy-denylist.local",
                    help="regex-per-line keyword file, relative to --repo")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    repo = args.repo
    own_email = subprocess.run(["git", "-C", repo, "config", "--local", "--get", "user.email"],
                               capture_output=True, text=True).stdout.strip().lower()
    if not own_email:
        print("privacy-check: BLOCKED - set a personal email for this repo first:\n"
              "  git config user.email <personal address>")
        return 1
    allowed_emails = {own_email}
    denylist = load_denylist(Path(repo) / args.denylist)
    allow = load_denylist(Path(repo) / ALLOWLIST)
    if not denylist:
        print(f"privacy-check: note - no denylist at {args.denylist}; generic checks only")

    findings, binaries = [], []
    for sha in outgoing_commits(repo, args.remote, sys.stdin.read()):
        short = sha[:7]
        for who in git(repo, "show", "-s", "--format=%ae%n%ce", sha).split():
            if who.lower() not in allowed_emails and not NOREPLY.search(who):
                findings.append(f"{short} commit metadata: email {who}")

        numstat = git(repo, "show", "--format=", "--numstat", "--no-renames", sha)
        for row in numstat.splitlines():
            added, _, path = row.split("\t", 2)
            if added == "-":
                binaries.append((sha, path))

        current = "?"
        diff = git(repo, "show", "--format=", "-U0", "--no-renames", "--no-color", sha)
        for line in diff.splitlines():
            if line.startswith("+++ "):
                current = (line[6:] if line.startswith("+++ b/") else line[4:]).rstrip("\t")
            elif line.startswith("+") and current not in SKIP:
                for kind, match in scan_text(line[1:], allowed_emails, denylist, allow):
                    findings.append(f"{short} {current}: {kind} -> {match}")

    # Binary bytes decode to noise that looks like emails, so only paths + denylist here.
    for sha, path in binaries:
        blob = git(repo, "show", f"{sha}:{path}", binary=True).decode("utf-8", "ignore")
        for kind, match in scan_text(blob, allowed_emails, denylist, allow, emails=False):
            findings.append(f"{sha[:7]} {path} (binary): {kind} -> {match}")

    if binaries:
        print("privacy-check: binary files in this push - open and check them by eye:")
        for _, path in sorted(set(binaries), key=lambda b: b[1]):
            print(f"  {path}")
    if findings:
        print("privacy-check: BLOCKED - possible personal information:")
        for f in findings:
            print(f"  {f}")
        print("Fix and re-commit, or bypass deliberately with: git push --no-verify")
        return 1
    print("privacy-check: clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
