---
name: findcoworkskills
version: 2.0.0
description: Find skills you can install and use in Claude Cowork for a given topic. Use this skill whenever the user wants to discover existing skills before building their own — triggers include "find cowork skills for X", "what skills exist for X", "is there already a skill for X", "search for skills about X", "find me a skill that does X", or "before I build a skill, what's out there for X". Searches the open skill catalog, reads each result's actual SKILL.md to see which ones declare Cowork / Claude Desktop support, ranks everything by GitHub stars, and writes a single branded HTML report. No account or token needed.
---

# findcoworkskills

Searches the open skill ecosystem for a topic and produces one ranked HTML report, so
you can see what already exists before building a skill of your own.

## When to use

The user is thinking about a skill for some task and wants to know what's already
available: "find cowork skills for equity research", "is there already a DCF skill",
"what's out there for SEO", "before I build this, search what exists".

## What it does

1. Searches the **skillsmp.com** catalog (2.2M+ skills) for the topic.
2. Removes duplicate copies/forks, keeping the most-starred version of each.
3. Reads each result's **actual SKILL.md** (and README) to see which ones declare
   Cowork / Claude Desktop support.
4. Ranks by GitHub stars, cowork-ready first, and writes a branded HTML report.

Every skill in the report installs in Cowork the same way: **Customize > Skills >
upload**, or open the source link. The report just helps you find and compare them.

## How to run

```bash
python3 findcoworkskills.py "your topic here"
```

The report is written to `findcoworkskills_report.html` (or set `FCS_OUT` to choose the
path). Open it in a browser.

```bash
FCS_OUT=~/Desktop/skills.html python3 findcoworkskills.py "discounted cash flow"
```

## Reading the report

- **cowork-ready tag** — the skill's docs mention Cowork / Claude Desktop directly.
- **green "official vendor" box** — published by a known business (Anthropic, etc.).
- **Stars** — the skill's GitHub repository stars (the one signal every skill shares).
  Note a big number can be the *repo's* stars when a skill lives inside a large repo.
- **Divider** — separates the cowork-ready skills from the rest. Skills below the
  divider don't mention Cowork, but they still install; they're worth a look.
- **Show more** — the report shows 25 skills at a time.

## Notes

- No account, login, or token is required. It uses public data over plain HTTP.
- A run reads each result's SKILL.md, so expect roughly 20–40 seconds for ~50 skills.
- Always review any third-party skill before enabling it, as you would any code.
- The "official vendor" list is curated in the script (a `BUSINESS` set near the top);
  add names to it as you like.

## Companion

For a skill that turns out to need changes for Cowork (it relies on Claude Code-only
features like hooks), paste its URL into Cowork and ask Claude how to adapt it — see the
`adapt-for-cowork` skill.
