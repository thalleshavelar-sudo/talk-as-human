# talk-as-human

A skill for Claude that writes and rewrites text so it sounds like a person wrote it. It works in English, Portuguese and Spanish, and it runs anywhere that reads a `SKILL.md`: Claude Code, Claude.ai, or another agent you point at the file.

You give it a draft, or ask it to write something, and it strips out the habits that make text read as generated: the "it's not X, it's Y" contrasts, the punchline after every paragraph, dashes everywhere, "delve" and "leverage", "Great question!", bold labels on every bullet, and the 250-word status update that should have been 80. It won't invent facts to fill the gaps. If a sentence needs a number it doesn't have, it asks.

## What's inside

```
SKILL.md                           the process and the 42 filters
references/filters-en.md           English word and phrase lists, with plain replacements
references/filters-pt-br.md        same for Brazilian Portuguese
references/filters-es.md           same for Spanish
references/natural-voice-filter.md voice profile to imitate, per channel
scripts/check_ai_tells.py          automatic checker, no dependencies
bin/cli.js                         npx installer
```

The filters come in eight groups:

| Group | Examples |
|---|---|
| Staging | "not X, but Y", punchline closers, "here's the thing", bait questions, arguing with an objection nobody made |
| Rhythm | forced triads, same-length sentences and paragraphs, dashes, stacked hedges, "furthermore / moreover / it's worth noting" |
| Inflation | AI vocabulary, intensifiers with no number behind them, "plays a pivotal role", brochure language, "experts say" with no source |
| Formatting | decorative bold, **Label:** bullets, Title Case Headings, emoji in headings, curly quotes, exclamation marks everywhere |
| Leftovers | "I hope this helps", "Want me to...?", knowledge-cutoff disclaimers, `oaicite`, `turn0search0`, zero-width characters, `[Name]` placeholders |
| Wrong reader | re-explaining what the reader already knows, the answer buried in the last line, the wrong register for the channel |
| Overcorrection | cutting real warmth, flattening the genre, fake-casual punctuation, restating numbers, evenly balanced shapes, planted details |
| Length and density | a word budget per channel, data-dump paragraphs, breakdowns next to totals, narrating the process, status buried at the end |

Each language file has its own local habits, like "vale ressaltar" and "vou estar enviando" in Portuguese or "cabe destacar" in Spanish.

The overcorrection group is there because rewrites that only delete things come out cold and suspiciously tidy, which gives them away too. It checks that real courtesy survived, that the genre still sounds like itself (a bakery's birthday post can have an exclamation mark) and that a WhatsApp message wasn't polished into perfect punctuation.

## Install

With npx (Node 16.7 or newer):

```bash
npx talk-as-human              # every project: ~/.claude/skills/talk-as-human
npx talk-as-human --project    # this project only: ./.claude/skills/talk-as-human
npx talk-as-human --dir <path> # another agent's skills folder
npx talk-as-human uninstall    # add --project or --dir to match how you installed
```

With the skills CLI, which also targets Cursor, Copilot and other agents:

```bash
npx skills add thalleshavelar-sudo/talk-as-human
```

With git:

```bash
git clone https://github.com/thalleshavelar-sudo/talk-as-human.git ~/.claude/skills/talk-as-human
```

Claude.ai: zip the folder and upload it in the Skills section of your settings.

Other agents (Cursor, Codex and so on): point their rules file at `SKILL.md`.

## Use

```
/talk-as-human rewrite this: <text>
```

Or just ask: "make this sound natural", "humaniza esse texto", "que no suene a IA". If you paste a sample of your own writing, it follows the sample over its own defaults, dashes included.

The checker also works by itself:

```bash
python3 scripts/check_ai_tells.py draft.md
echo "Great question! It's worth noting that..." | python3 scripts/check_ai_tells.py -
python3 scripts/check_ai_tells.py --strict --min 3 post.txt   # exits 1 on strong findings, handy in CI
python3 scripts/check_ai_tells.py --channel work update.txt    # also checks the length budget
npx talk-as-human check --channel email reply.txt             # same checker through npx (needs Python 3)
```

Channels and their word budgets: `chat` 40, `work` 90, `email` 150, `commit` 120, `post` 150, `review` 80, `doc` (paragraph length only).

Sample output:

```
[STRONG]    L1  chat residue: ¡Excelente pregunta
[STRONG]    L1  staged contrast (not X, but Y): No es solo una herramienta, es
[STRONG]    L1  dash: '—'
[medium]    L1  inflation / brochure language: juega un papel fundamental
[medium]    L1  essay connector / filler opener: Cabe destacar
```

The script catches words and shapes. It can't tell when a paragraph is staging a point or answering a question nobody asked; that's what `SKILL.md` is for.

One limit worth knowing: the skill won't invent details, so a draft with only generic facts comes back clean but a bit thin. Give it the messy specific (what actually broke, which cake, why the meeting moved) and the result reads much more like you.

## Teach it your voice

`references/natural-voice-filter.md` ships with the author's own voice: casual Brazilian Portuguese, requests chained with "e", "pra" and "n", no emoji, no exclamation marks. Swap in your own messages, a few per channel (chat, email, public post), and say where each one came from. With only two or three samples it gets the vocabulary right but still guesses at punctuation and rhythm.

## License

MIT. See [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
