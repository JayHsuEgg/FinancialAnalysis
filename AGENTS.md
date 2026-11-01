# AGENTS.md — read before reviewing, editing, or pushing this repo

> Single source of AI instructions for this repo. `CLAUDE.md` only imports this file —
> edit here, not there.

## What this repo is

Public learning notes on long-term index investing, published on GitHub and GitHub Pages.
It is written so **anyone** can reuse the reasoning. It is not a personal financial plan,
even where a document is phrased in the first person.

## Scope: investing only — these are NOT gaps, do not raise them

The owner has decided the following are out of scope and are planned separately, outside
this repo. A review that flags any of them as "missing" is wrong for this repo:

- insurance of any kind (life, disability, health, long-term care)
- buying a home or car, down-payment savings
- children's education funds
- any other household spending, or "medium-term goal" buckets for those expenses

In scope: what to hold and why, vehicle and tax choices, allocation, rebalancing,
withdrawal / decumulation rules, behavioural discipline, and the evidence behind them.

## Numbers must carry their sources

`資料來源紀錄.md` records, for every verified figure in the repo, the source URL (or paper page),
the data date, the access date and the source type. Keep it in sync:

- **When you add or change a number in any document, update its row in `資料來源紀錄.md` in the
  same commit** — new URL, new data date, access date = the day you actually opened the page.
  A changed number with a stale source row is a defect.
- Record only pages you actually opened. If you only saw a search-engine snippet, mark it
  "🔎 僅搜尋摘要"; if nothing could be verified, say so in the row and in the record's
  "已知缺口" section. Never invent or reconstruct a URL.
- Self-calculated numbers point to the script that produces them (`試算腳本/` or
  `8. 槓桿DCA實證_佐證/`). New calculations go into `試算腳本/` with argparse inputs and outputs —
  no hardcoded local paths.
- Paper figures cite the page of the PDF in `paper/` (physical page order, cover = p.1).

## Public repo: no personal information — and do not ask for it

- Do not ask about, suggest documenting, or flag as a risk: the owner's employer, job,
  industry, salary, stock compensation (RSU / ESPP), net worth, account sizes, or family
  details. "Your human capital is concentrated in one industry" or "do you hold employer
  stock?" are **not** valid review points here — the owner chose to keep that out of the
  repo on purpose.
- When an argument needs a person, write a generic investor profile
  (e.g. "a mid-career investor with no workplace pension"), never the owner.
- Never add personal detail to the repo, even if the owner mentions it in conversation.

## Before EVERY push to GitHub: privacy check (mandatory)

**No push until this check passes and the owner explicitly confirms the push.**
Public history is effectively permanent — removing something later needs a history
rewrite and force-push, and forks / caches may already hold it. Never "push now, fix later".

Check the **whole outgoing range**, not just the last commit:

1. **Content** — `git diff origin/main..HEAD`, plus any uncommitted or untracked files
   that are about to be committed. Look for:
   - real people's names (owner, family, friends, colleagues), emails, phone numbers,
     addresses, account or ID numbers
   - employer, job title, industry, team or project names
   - absolute amounts tied to the owner (portfolio size, salary, holdings in units / NT$ / US$)
   - family facts (ages, marital status, children, parents' circumstances)
   - local machine paths containing a username, hostnames, internal / intranet URLs
   - binary files (PDF, images, CSV, xlsx): open and check them — do not judge by filename
2. **Commit metadata** — `git log origin/main..HEAD --format="%an <%ae> | %cn <%ce>"`.
   Author and committer emails must not be a work address. If they are, stop and tell the
   owner before pushing (fixing it means rewriting those unpushed commits).

Report the result to the owner (clean, or each finding with file:line). Push only after a
clean result **and** an explicit go-ahead.

### Mechanical safety net: `.githooks/pre-push`

A pre-push hook runs `.githooks/privacy_check.py` on every push (by anyone, not just AI):
it blocks on non-personal commit emails, email addresses, user-profile paths, and any
regex in `.privacy-denylist.local` (gitignored — the owner's private keywords; never
commit it, never copy its contents into tracked files).

- Enable once per clone: `git config core.hooksPath .githooks`
- The hook is a net, not a substitute: it cannot judge context or read inside binaries
  reliably, so the manual check above is still required.
- Never bypass it with `--no-verify` on the owner's behalf.
