#!/usr/bin/env python3
"""check_ai_tells: finds AI writing tells in English, Portuguese and Spanish text.

Usage:
    python3 scripts/check_ai_tells.py draft.md
    echo "some text" | python3 scripts/check_ai_tells.py -
    python3 scripts/check_ai_tells.py --strict --min 3 post.txt   # exit 1 on strong findings

Standard library only. Skips fenced code, inline code and URLs.
It finds words and shapes. Staging, the wrong reader and invented facts still
need a human (or model) to read the text.
"""

import argparse
import re
import statistics
import sys
import unicodedata

# (category, weight, patterns). weight 3 = strong, 2 = medium, 1 = weak alone.
LISTS = [
    ("chat residue", 3, [
        r"[óo]tima pergunta", r"excelente pergunta", r"que pergunta interessante",
        r"espero (ter ajudado|que (isso )?(ajude|seja [úu]til))", r"fico [àa] disposi[çc][ãa]o",
        r"estou [àa] disposi[çc][ãa]o", r"qualquer d[úu]vida ([ée] s[óo] chamar|estou aqui)",
        r"se precisar de mais alguma coisa", r"posso te ajudar com mais", r"quer que eu",
        r"gostaria que eu", r"deixe-me saber", r"fique [àa] vontade para",
        r"como (uma )?ia\b", r"como (um )?modelo de linguagem", r"voc[êe] est[áa] absolutamente cert",
        r"voc[êe] tem toda raz[ãa]o", r"^\s*(claro|com certeza|certamente|perfeito|entendido)!",
        r"segue abaixo", r"aqui est[áa] (o|a|um|uma)\b",
        r"great question", r"excellent question", r"i hope this helps", r"hope this helps",
        r"let me know if", r"feel free to", r"would you like me to", r"want me to\b",
        r"as an ai\b", r"as a (large )?language model", r"you'?re absolutely right",
        r"^\s*(certainly|of course|absolutely|sure thing)!", r"happy to help",
        # es
        r'[¡]?(excelente|buena|gran) pregunta',
        r'espero (que (esto )?te (sirva|ayude)|haberte ayudado)',
        r'no dudes en (contactar|preguntar|escribir)',
        r'si necesitas algo m[áa]s',
        r'¿(quieres|te gustar[íi]a) que',
        r'como (una )?ia\b',
        r'como (un )?modelo de lenguaje',
        r'tienes toda la raz[óo]n',
        r'aqu[íi] tienes',
        r'a continuaci[óo]n te (presento|dejo|muestro)',
        r'^\s*¡(claro|por supuesto|desde luego|perfecto|entendido)!',
        r'quedo a (tu|su) disposici[óo]n',
    ]),
    ("knowledge-limit disclaimer", 3, [
        r"at[ée] a data do meu treinamento", r"com base nas informa[çc][õo]es dispon[íi]veis",
        r"n[ãa]o h[áa] informa[çc][õo]es p[úu]blicas", r"n[ãa]o foi poss[íi]vel (encontrar|localizar)",
        r"n[ãa]o est[áa] amplamente documentad", r"as of my (last|knowledge) (update|cutoff)",
        r"based on (the )?available information", r"not (widely|publicly) (documented|available)",
        # es
        r'hasta la fecha de mi (entrenamiento|corte)',
        r'seg[úu]n la informaci[óo]n disponible',
        r'no (se encontr[óo]|hay) informaci[óo]n (p[úu]blica|disponible)',
        r'no est[áa] ampliamente documentad',
    ]),
    ("staged contrast (not X, but Y)", 3, [
        r"n[ãa]o [ée] (s[óo]|apenas|somente|sobre)\b[^.!?\n]{1,80}[,.;]\s*[ée]\b",
        r"n[ãa]o se trata de\b[^.!?\n]{1,80}\bmas\b", r"mais do que\b[^.!?\n]{1,60},\s*[ée]\b",
        r"isso n[ãa]o significa\b[^.!?\n]{1,80}[.]\s*significa", r"n[ãa]o [ée] s[óo]\b",
        r"\bnot (just|only|merely)\b[^.!?\n]{1,80}\bbut\b", r"\bit'?s not\b[^.!?\n]{1,60}[,;.]\s*it'?s\b",
        r"this isn'?t about\b", r"\bisn'?t just\b",
        # es
        r'no es (solo|s[óo]lo|solamente|simplemente)\b[^.!?\n]{1,80}[,.;]\s*es\b',
        r'no se trata de\b[^.!?\n]{1,80}\b(sino|se trata)\b',
        r'm[áa]s que\b[^.!?\n]{1,60},\s*es\b',
        r'esto no significa\b[^.!?\n]{1,80}[.]\s*significa',
    ]),
    ("run-up / hook", 3, [
        r"sem mais delongas", r"vamos mergulhar", r"vamos explorar", r"vamos destrinchar",
        r"senta que l[áa] vem", r"vem comigo", r"aqui est[áa] o que voc[êe] precisa saber",
        r"voc[êe] j[áa] parou (pra|para) pensar", r"j[áa] se perguntou", r"imagine um mundo",
        r"e se eu te dissesse", r"ningu[ée]m fala sobre isso", r"sendo bem sincer[oa]\?",
        r"^\s*spoiler:", r"o resultado\?", r"e o melhor\?", r"adivinha\?", r"papo reto:",
        r"let'?s dive in", r"let'?s (explore|break (it|this) down)", r"here'?s the thing",
        r"here'?s what you need to know", r"without further ado", r"imagine a world",
        r"have you ever wondered", r"^\s*honestly\?", r"^\s*real talk", r"picture this",
        r"\bwhether you'?re an? \b",
        # es
        r'sin m[áa]s (pre[áa]mbulos|dilaci[óo]n)',
        r'vamos a (sumergirnos|adentrarnos|explorar|desglosar)',
        r'manos a la obra',
        r'¿alguna vez te has preguntado',
        r'¿te has parado a pensar',
        r'imagina un mundo',
        r'¿y si te dijera',
        r'nadie habla de esto',
        r'¿el resultado\?',
        r'¿lo mejor\?',
        r'¿adivinas qu[ée]\?',
        r'la verdad es que',
        r'lo cierto es que',
        r'seamos honestos',
    ]),
    ("punchline closer", 2, [
        r"e isso muda tudo", r"simples assim\.", r"pensa nisso\.", r"leia de novo",
        r"fica a (reflex[ãa]o|li[çc][ãa]o|dica)", r"moral da hist[óo]ria", r"o futuro [ée] promissor",
        r"o c[ée]u [ée] o limite", r"(isso )?[ée] s[óo] o come[çc]o", r"a jornada continua",
        r"e [ée] a[íi] que (mora|est[áa]) o segredo", r"o recado [ée] claro",
        r"that'?s the real win", r"let that sink in", r"read that again", r"and that changes everything",
        r"the future looks bright", r"exciting times ahead", r"a step in the right direction",
        # es
        r'y eso lo cambia todo',
        r'as[íi] de (simple|f[áa]cil)\.',
        r'pi[ée]nsalo\.',
        r'l[ée]elo otra vez',
        r'ah[íi] est[áa] la clave',
        r'te dejo la reflexi[óo]n',
        r'el futuro es prometedor',
        r'el cielo es el l[íi]mite',
        r'(esto )?es solo el comienzo',
        r'el viaje contin[úu]a',
        r'moraleja:',
    ]),
    ("essay connector / filler opener", 2, [
        r"\bademais\b", r"\boutrossim\b", r"nesse sentido", r"nesse contexto", r"nesse cen[áa]rio",
        r"diante do exposto", r"por conseguinte", r"vale (ressaltar|destacar|lembrar|mencionar)",
        r"[ée] (importante|v[áa]lido|fundamental) (destacar|ressaltar|salientar|mencionar|notar|lembrar)",
        r"cabe (destacar|ressaltar)", r"conv[ée]m lembrar", r"em suma\b", r"em s[íi]ntese",
        r"por fim,? mas n[ãa]o menos importante", r"em [úu]ltima an[áa]lise", r"no final do dia",
        r"quando se trata de", r"no mundo (atual|de hoje|moderno)", r"nos dias de hoje",
        r"na era digital", r"em um mundo cada vez mais", r"no cen[áa]rio atual",
        r"\bfurthermore\b", r"\bmoreover\b", r"\bnotwithstanding\b", r"that being said",
        r"it'?s (important|worth) (to note|noting)", r"it should be noted", r"in today'?s\b",
        r"in the (realm|landscape) of", r"at its core", r"in essence", r"to put it simply",
        r"when it comes to", r"at the end of the day", r"in conclusion", r"all things considered",
        # es
        r'\basimismo\b',
        r'\bpor ende\b',
        r'en este sentido',
        r'en este contexto',
        r'cabe (destacar|se[ñn]alar|mencionar|resaltar)',
        r'es (importante|fundamental|crucial) (destacar|se[ñn]alar|resaltar|mencionar|recordar)',
        r'vale la pena (mencionar|destacar)',
        r'conviene recordar',
        r'en s[íi]ntesis',
        r'en definitiva',
        r'por [úu]ltimo,? pero no menos importante',
        r'en [úu]ltima instancia',
        r'cuando se trata de',
        r'en el mundo (actual|de hoy)',
        r'hoy en d[íi]a',
        r'en la era digital',
        r'en un mundo cada vez m[áa]s',
        r'en el panorama actual',
        r'en un entorno en constante',
    ]),
    ("AI vocabulary", 2, [
        r"\bmergulh(ar|e|amos|ando) (no|na|nos|nas|em)\b", r"\bdesvend", r"\balavanc", r"\bpotencializ",
        r"\bimpulsion", r"\bcatalis", r"\bfoment", r"\botimiz", r"\bdesbloque", r"\brevolucion",
        r"\bressignific", r"\bredefin", r"\bnaveg(ar|ando) (por|pelos|pelas|os|as)\b", r"\bempoder",
        r"\bagregar valor", r"\brobust[oa]s?\b", r"\babrangente", r"\bcrucia(l|is)\b",
        r"\bprimordia", r"\bimprescind[íi]ve", r"\bdisruptiv", r"\bhol[íi]stic", r"\bsin[ée]rgi",
        r"\bmultifacetad", r"\bintr[íi]nsec", r"\bvibrante", r"\bcen[áa]rio\b", r"\bpanorama\b",
        r"\becossistema\b", r"\bjornada\b", r"\btape[çc]aria\b", r"\bmosaico\b", r"\bsinfonia\b",
        r"\bfarol\b", r"\bdivisor de [áa]guas", r"\bvirada de chave", r"\bgame.?changer",
        r"\bresili[êe]ncia\b", r"\bprotagonismo\b", r"\bmindset\b",
        r"\bdelv(e|es|ed|ing)\b", r"\bleverag", r"\butiliz", r"\bfoster", r"\bbolster",
        r"\bunderscor", r"\bunveil", r"\bstreamlin", r"\bharness", r"\bempower", r"\bunlock",
        r"\belevat(e|es|ing)\b", r"\bseamless", r"\bcomprehensive\b", r"\bpivotal\b", r"\bcrucial\b",
        r"\bvibrant\b", r"\bintricat", r"\bnuanced\b", r"\bmultifaceted\b", r"\bholistic\b",
        r"\blandscape\b", r"\brealm\b", r"\btapestry\b", r"\btestament\b", r"\bbeacon\b",
        r"\bmeticulous", r"\bparamount\b", r"\bmyriad\b", r"\bplethora\b", r"\bshed light on",
        r"\bpave the way", r"\bindelible\b", r"\bunwavering\b", r"\bgarner",
        # es
        r'\badentr(arse|arnos|ndonos)\b',
        r'\bsumerg(irse|irnos|ámonos)\b',
        r'\bdesentra[ñn]',
        r'\bpotenci(ar|a|ando)\b',
        r'\bcatapult',
        r'\bapalanc',
        r'\bpropici',
        r'\bdesbloque',
        r'\bempoder',
        r'\baportar valor\b',
        r'\bintegral\b',
        r'\bexhaustiv',
        r'\bimprescindible',
        r'\bvanguardi',
        r'\bmultifac[ée]tic',
        r'\bpolifac[ée]tic',
        r'\bescenario\b',
        r'\bpaisaje\b',
        r'\becosistema\b',
        r'\btraves[íi]a\b',
        r'\btapiz\b',
        r'\bfaro\b',
        r'\bpiedra angular',
        r'\bun antes y un despu[ée]s',
        r'\bpunto de inflexi[óo]n',
        r'\bsinergi',
        r'\bresiliencia\b',
    ]),
    ("inflation / brochure language", 2, [
        r"papel (fundamental|crucial|essencial|importante)", r"marco (importante|hist[óo]rico)",
        r"momento decisivo", r"legado duradouro", r"deixou sua marca", r"abrindo caminho para",
        r"de tirar o f[ôo]lego", r"no cora[çc][ãa]o d[aoe]", r"experi[êe]ncia [úu]nica",
        r"qualidade incompar[áa]vel", r"solu[çc][ãa]o completa", r"de ponta\b", r"compromisso com",
        r"stands as a", r"serves as a testament", r"plays? a (key|crucial|pivotal|vital) role",
        r"enduring legacy", r"setting the stage", r"nestled", r"in the heart of", r"breathtaking",
        r"\bstunning\b", r"must-visit", r"state-of-the-art", r"world-class", r"watershed moment",
        # es
        r'(juega|desempe[ñn]a) un papel (fundamental|crucial|clave|esencial)',
        r'marca un hito',
        r'legado duradero',
        r'dej[óo] (su|una) huella',
        r'allanando el camino',
        r'que te dejar[áa] sin aliento',
        r'en el coraz[óo]n de',
        r'enclavad[oa] en',
        r'experiencia (única|inolvidable)',
        r'soluci[óo]n integral',
        r'de primer nivel',
        r'compromiso con',
        r'se erige como',
        r'se posiciona como',
    ]),
    ("unsourced authority", 2, [
        r"especialistas (afirmam|apontam|dizem|acreditam)", r"estudos (mostram|comprovam|indicam)",
        r"pesquisas (mostram|indicam|apontam)", r"segundo especialistas", r"[ée] amplamente reconhecido",
        r"a ci[êe]ncia comprova", r"experts (say|argue|believe)", r"studies (show|suggest)",
        r"research (shows|suggests)", r"it is widely (acknowledged|recognized)",
        # es
        r'los expertos (afirman|coinciden|dicen|creen)',
        r'(diversos |los )?estudios (demuestran|indican|muestran)',
        r'las investigaciones (indican|muestran)',
        r'seg[úu]n los expertos',
        r'es ampliamente reconocido',
        r'la ciencia lo confirma',
    ]),
    ("intensifier", 1, [
        r"\bextremamente\b", r"\bincrivelmente\b", r"\babsolutamente\b", r"\bverdadeiramente\b",
        r"\bprofundamente\b", r"\bsignificativamente\b", r"\bdrasticamente\b", r"\bextraordinariamente\b",
        r"\bnotavelmente\b", r"\bindiscutivelmente\b", r"\binegavelmente\b",
        r"\bextremely\b", r"\bincredibly\b", r"\btruly\b", r"\bsignificantly\b", r"\bdramatically\b",
        r"\bremarkably\b", r"\bundoubtedly\b", r"\bfundamentally\b",
        # es
        r'\bextremadamente\b',
        r'\bincre[íi]blemente\b',
        r'\bsumamente\b',
        r'\bindudablemente\b',
        r'\binnegablemente\b',
    ]),
    ("stacked hedge", 1, [
        r"pode potencialmente", r"talvez possa", r"poderia potencialmente", r"de certa forma",
        r"at[ée] certo ponto", r"pode ajudar a", r"busca garantir", r"visa (proporcionar|garantir)",
        r"could potentially", r"may potentially", r"might arguably", r"can help (to )?ensure",
        # es
        r'podr[íi]a potencialmente',
        r'de alguna manera',
        r'hasta cierto punto',
        r'busca garantizar',
        r'puede ayudar a',
    ]),
    ("padded verb / bureaucratese", 1, [
        r"\bvou estar \w+ndo\b", r"\bestaremos \w+ndo\b", r"\bvamos estar \w+ndo\b",
        r"\bfoi realizad[ao]\b", r"\b[ée] realizad[ao]\b", r"\ba n[íi]vel de\b", r"\bno que tange\b",
        r"\bse configura como\b", r"\bconta com\b", r"\bdisp[õo]e de\b",
        r"\bserves as\b", r"\bfunctions as\b", r"\bboasts\b",
        # es
        r'se procedi[óo] a',
        r'se llev[óo] a cabo',
        r'\ba nivel de\b',
        r'\ben base a\b',
        r'\ben aras de\b',
        r'\bcuenta con\b',
        r'\bdispone de\b',
        r'\bponer en valor\b',
    ]),
    ("text talking about itself", 1, [
        r"como (mencionado|dito|visto) (acima|anteriormente)", r"como veremos (a seguir|adiante)",
        r"neste (artigo|post|guia|texto) (voc[êe] vai|vamos)", r"este texto tem como objetivo",
        r"as (mentioned|discussed) above", r"in this (article|post|guide),? (we|you)",
        # es
        r'como se (mencion[óo]|dijo) (anteriormente|arriba)',
        r'como veremos (a continuaci[óo]n|m[áa]s adelante)',
        r'en este (art[íi]culo|post|texto) (veremos|vamos)',
    ]),
]

INVISIBLE = {
    "​": "ZERO WIDTH SPACE", "‌": "ZERO WIDTH NON-JOINER", "‍": "ZERO WIDTH JOINER",
    "⁠": "WORD JOINER", "﻿": "BOM / ZERO WIDTH NO-BREAK SPACE", " ": "NARROW NO-BREAK SPACE",
    "­": "SOFT HYPHEN", "⁢": "INVISIBLE TIMES", "⁣": "INVISIBLE SEPARATOR",
    "⁤": "INVISIBLE PLUS", "᠎": "MONGOLIAN VOWEL SEPARATOR",
}
ARTIFACTS = [r"oaicite", r"contentReference", r"turn\d+(search|news|view)\d+", r"grok_card",
             r"attributableIndex", r"【[^】]*†[^】]*】", r"utm_source=(chatgpt\.com|openai)"]
PLACEHOLDERS = [r"\[(nome|name|nombre|empresa|company|inserir[^\]]*|insert[^\]]*|insertar[^\]]*|seu nome|your name|tu nombre)\]",
                r"\bXXX+\b", r"lorem ipsum", r"\{\{[^}]+\}\}"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅❌✨]")


def strip_code(text):
    """Blank out code and URLs but keep newlines so line numbers still match."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"```.*?```", blank, text, flags=re.S)
    text = re.sub(r"`[^`\n]*`", blank, text)
    text = re.sub(r"https?://\S+", blank, text)
    return text


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def sentences(prose):
    prose = re.sub(r"^\s*([#>*-]|\d+\.)\s*", "", prose, flags=re.M)
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", prose)
    return [p.strip() for p in parts if re.search(r"\w", p)]


BUDGETS = {  # max words per channel (filter 39)
    "chat": 40, "work": 90, "email": 150, "commit": 120, "post": 150, "review": 80, "doc": None,
}
NUMBER = re.compile(r"(?<![\w.])\d[\d.,/:-]*\d?%?(?![\w])|\b[A-Z]{2,}\d+[A-Z\d]*\b|\b\d+[A-Z]{2,}[A-Z\d]*\b")


def check(raw, channel=None):
    hits = []  # (line, weight, category, snippet)
    text = strip_code(raw)

    for ch, name in INVISIBLE.items():
        for m in re.finditer(re.escape(ch), raw):
            hits.append((line_of(raw, m.start()), 3, "invisible character", name))
    for pat in ARTIFACTS:
        for m in re.finditer(pat, raw):
            hits.append((line_of(raw, m.start()), 3, "chatbot markup artifact", m.group(0)))
    for pat in PLACEHOLDERS:
        for m in re.finditer(pat, text, flags=re.I):
            hits.append((line_of(text, m.start()), 3, "forgotten placeholder", m.group(0)))

    for m in re.finditer(r"[—–]|\s--\s", text):
        hits.append((line_of(text, m.start()), 3, "dash", repr(m.group(0).strip())))
    for m in re.finditer(r"[“”‘’]", text):
        hits.append((line_of(text, m.start()), 1, "curly quote", m.group(0)))
    for m in re.finditer(r"…", text):
        hits.append((line_of(text, m.start()), 1, "unicode ellipsis", "…"))

    for cat, weight, pats in LISTS:
        for pat in pats:
            for m in re.finditer(pat, text, flags=re.I | re.M):
                hits.append((line_of(text, m.start()), weight, cat, m.group(0).strip()))

    for i, line in enumerate(text.split("\n"), 1):
        s = line.strip()
        if re.match(r"^#{1,6}\s", s):
            words = [w for w in re.findall(r"[^\W\d_]+", s.lstrip("# ")) if len(w) >= 2]
            if len(words) >= 3 and all(w[0].isupper() for w in words):
                hits.append((i, 2, "Title Case heading", s))
            if EMOJI.search(s):
                hits.append((i, 2, "emoji in heading", s))
        if re.match(r"^([-*]|\d+\.)\s+\*\*[^*]+:\*\*|^([-*]|\d+\.)\s+\*\*[^*]+\*\*:", s):
            hits.append((i, 2, "bold-label list item", s[:60]))
        if re.match(r"^([-*]|\d+\.)?\s*" + EMOJI.pattern, s):
            hits.append((i, 1, "emoji bullet", s[:60]))

    stats = {}
    prose = re.sub(r"^\s*\|.*$", "", text, flags=re.M)  # drop tables
    lens = [len(s.split()) for s in sentences(prose)]
    words = sum(lens)
    stats["words"] = words
    stats["sentences"] = len(lens)
    if len(lens) >= 6:
        stats["mean words/sentence"] = round(statistics.mean(lens), 1)
        stats["std dev"] = round(statistics.pstdev(lens), 1)
        stats["under 8 words"] = sum(1 for n in lens if n < 8)
        stats["over 25 words"] = sum(1 for n in lens if n > 25)
        if words >= 150 and statistics.pstdev(lens) < 5:
            hits.append((0, 2, "flat rhythm", "sentences are nearly all the same length; mix short and long"))
        if words >= 300 and (stats["under 8 words"] == 0 or stats["over 25 words"] == 0):
            hits.append((0, 1, "low variation", "no very short or no very long sentence"))

    paras = [p for p in re.split(r"\n\s*\n", prose)
             if len(p.split()) >= 15 and not p.lstrip().startswith(("#", "-", "*", ">"))]
    if len(paras) >= 4:
        plen = [len(p.split()) for p in paras]
        mean = statistics.mean(plen)
        if all(abs(n - mean) <= 0.15 * mean for n in plen):
            hits.append((0, 2, "same-size paragraphs", f"{len(paras)} paragraphs of ~{round(mean)} words"))
        firsts = [p.split()[0].lower().strip(",.:") for p in paras]
        for j in range(len(firsts) - 2):
            if firsts[j] == firsts[j + 1] == firsts[j + 2]:
                hits.append((0, 2, "repeated openings", f"3 paragraphs in a row start with '{firsts[j]}'"))
                break

    # length and density (section H)
    budget = BUDGETS.get(channel) if channel else None
    if budget and words > budget:
        w = 3 if words > budget * 1.5 else 2
        hits.append((0, w, "over length budget", f"{words} words for '{channel}' (budget {budget}); compress"))
    for p in re.split(r"\n\s*\n", prose):
        n_words = len(p.split())
        if n_words == 0 or p.lstrip().startswith("#"):
            continue
        first = line_of(prose, prose.find(p.strip()[:40])) if p.strip() else 0
        if n_words > 120:
            hits.append((first, 2, "wall of text", f"paragraph of {n_words} words"))
        elif n_words > 80:
            hits.append((first, 1, "long paragraph", f"paragraph of {n_words} words"))
        nums = len(NUMBER.findall(p))
        if nums >= 8 and nums / max(n_words, 1) > 0.06:
            hits.append((first, 2, "data dump", f"{nums} numbers/codes in {n_words} words; keep one per claim"))
        parens = p.count("(")
        if parens >= 3 and n_words < 150:
            hits.append((first, 1, "parenthesis pile-up", f"{parens} parentheses in one paragraph"))
        if re.search(r"\(\s*[\d.,]+[^)]*\b(e|y|and)\b[^)]*[\d.,]+[^)]*\)", p):
            hits.append((first, 2, "breakdown next to total", "drop the split, keep the total"))
    if channel in ("chat", "work", "email") and re.search(r"^\s*(#+\s*)?(o que fizemos|what we did|lo que hicimos|contexto|context|background|resumo|summary|resumen)\s*:?\s*$", text, flags=re.I | re.M):
        hits.append((0, 2, "heading inside a message", "cut headings from short messages"))
    stats["paragraphs"] = len([p for p in re.split(r"\n\s*\n", prose) if p.strip()])

    excl = text.count("!")
    if len(lens) >= 4 and excl >= 3 and excl / len(lens) > 0.4:
        hits.append((0, 2, "synthetic enthusiasm", f"{excl} exclamation marks in {len(lens)} sentences"))
    bold = len(re.findall(r"\*\*[^*\n]+\*\*", text))
    if words and bold / words * 100 > 2:
        hits.append((0, 1, "too much bold", f"{bold} bold spans in {words} words"))
    emojis = len(EMOJI.findall(text))
    if words and emojis / words * 100 > 1:
        hits.append((0, 1, "too many emoji", f"{emojis} emoji in {words} words"))

    hits.sort(key=lambda h: (h[0], -h[1], -len(h[3])))
    dedup = []
    for h in hits:  # drop a hit that is part of another on the same line and category
        if any(d[0] == h[0] and d[2] == h[2] and h[3].lower() in d[3].lower() for d in dedup):
            continue
        dedup.append(h)
    return dedup, stats


def main():
    ap = argparse.ArgumentParser(description="Find AI writing tells (EN, PT-BR, ES).")
    ap.add_argument("file", help="path to a file, or - to read stdin")
    ap.add_argument("--strict", action="store_true", help="exit with code 1 if there is a strong finding")
    ap.add_argument("--channel", choices=sorted(BUDGETS), help="check length against the channel budget")
    ap.add_argument("--min", type=int, default=1, choices=[1, 2, 3], help="minimum weight to show")
    a = ap.parse_args()

    raw = sys.stdin.read() if a.file == "-" else open(a.file, encoding="utf-8").read()
    raw = unicodedata.normalize("NFC", raw)
    hits, stats = check(raw, a.channel)
    label = {3: "STRONG", 2: "medium", 1: "weak"}

    shown = [h for h in hits if h[1] >= a.min]
    for line, w, cat, snip in shown:
        where = f"L{line}" if line else "text"
        print(f"[{label[w]:6}] {where:>5}  {cat}: {snip}")
    if not shown:
        print("Nothing found. Now read it out loud.")
    print()
    print("  ".join(f"{k}: {v}" for k, v in stats.items()))
    strong = sum(1 for h in hits if h[1] == 3)
    print(f"findings: {len(hits)} (strong: {strong})")
    if a.strict and strong:
        sys.exit(1)


if __name__ == "__main__":
    main()
