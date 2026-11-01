#!/usr/bin/env python3
"""slop_check: acha vícios de texto de IA em português e inglês.

Uso:
    python3 scripts/slop_check.py arquivo.md
    echo "texto" | python3 scripts/slop_check.py -
    python3 scripts/slop_check.py --strict arquivo.txt   # sai com código 1 se achar algo forte

Só usa a biblioteca padrão. Ignora blocos de código (```), código inline (`...`) e URLs.
Ele acha palavras e formas. Encenação, leitor errado e fato inventado continuam
sendo trabalho de leitura.
"""

import argparse
import re
import statistics
import sys
import unicodedata

# (categoria, peso, padrões). peso 3 = forte, 2 = médio, 1 = fraco sozinho.
LISTS = [
    ("resíduo de chat", 3, [
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
    ]),
    ("limite de conhecimento", 3, [
        r"at[ée] a data do meu treinamento", r"com base nas informa[çc][õo]es dispon[íi]veis",
        r"n[ãa]o h[áa] informa[çc][õo]es p[úu]blicas", r"n[ãa]o foi poss[íi]vel (encontrar|localizar)",
        r"n[ãa]o est[áa] amplamente documentad", r"as of my (last|knowledge) (update|cutoff)",
        r"based on (the )?available information", r"not (widely|publicly) (documented|available)",
    ]),
    ("contraste encenado (não é X, é Y)", 3, [
        r"n[ãa]o [ée] (s[óo]|apenas|somente|sobre)\b[^.!?\n]{1,80}[,.;]\s*[ée]\b",
        r"n[ãa]o se trata de\b[^.!?\n]{1,80}\bmas\b", r"mais do que\b[^.!?\n]{1,60},\s*[ée]\b",
        r"isso n[ãa]o significa\b[^.!?\n]{1,80}[.]\s*significa", r"n[ãa]o [ée] s[óo]\b",
        r"\bnot (just|only|merely)\b[^.!?\n]{1,80}\bbut\b", r"\bit'?s not\b[^.!?\n]{1,60}[,;.]\s*it'?s\b",
        r"this isn'?t about\b", r"\bisn'?t just\b",
    ]),
    ("aquecimento / gancho", 3, [
        r"sem mais delongas", r"vamos mergulhar", r"vamos explorar", r"vamos destrinchar",
        r"senta que l[áa] vem", r"vem comigo", r"aqui est[áa] o que voc[êe] precisa saber",
        r"voc[êe] j[áa] parou (pra|para) pensar", r"j[áa] se perguntou", r"imagine um mundo",
        r"e se eu te dissesse", r"ningu[ée]m fala sobre isso", r"sendo bem sincer[oa]\?",
        r"^\s*spoiler:", r"o resultado\?", r"e o melhor\?", r"adivinha\?", r"papo reto:",
        r"let'?s dive in", r"let'?s (explore|break (it|this) down)", r"here'?s the thing",
        r"here'?s what you need to know", r"without further ado", r"imagine a world",
        r"have you ever wondered", r"^\s*honestly\?", r"^\s*real talk", r"picture this",
        r"\bwhether you'?re an? \b",
    ]),
    ("fecho de efeito", 2, [
        r"e isso muda tudo", r"simples assim\.", r"pensa nisso\.", r"leia de novo",
        r"fica a (reflex[ãa]o|li[çc][ãa]o|dica)", r"moral da hist[óo]ria", r"o futuro [ée] promissor",
        r"o c[ée]u [ée] o limite", r"(isso )?[ée] s[óo] o come[çc]o", r"a jornada continua",
        r"e [ée] a[íi] que (mora|est[áa]) o segredo", r"o recado [ée] claro",
        r"that'?s the real win", r"let that sink in", r"read that again", r"and that changes everything",
        r"the future looks bright", r"exciting times ahead", r"a step in the right direction",
    ]),
    ("conectivo de redação", 2, [
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
    ]),
    ("palavra de IA", 2, [
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
    ]),
    ("inflação / folder", 2, [
        r"papel (fundamental|crucial|essencial|importante)", r"marco (importante|hist[óo]rico)",
        r"momento decisivo", r"legado duradouro", r"deixou sua marca", r"abrindo caminho para",
        r"de tirar o f[ôo]lego", r"no cora[çc][ãa]o d[aoe]", r"experi[êe]ncia [úu]nica",
        r"qualidade incompar[áa]vel", r"solu[çc][ãa]o completa", r"de ponta\b", r"compromisso com",
        r"stands as a", r"serves as a testament", r"plays? a (key|crucial|pivotal|vital) role",
        r"enduring legacy", r"setting the stage", r"nestled", r"in the heart of", r"breathtaking",
        r"\bstunning\b", r"must-visit", r"state-of-the-art", r"world-class", r"watershed moment",
    ]),
    ("autoridade sem fonte", 2, [
        r"especialistas (afirmam|apontam|dizem|acreditam)", r"estudos (mostram|comprovam|indicam)",
        r"pesquisas (mostram|indicam|apontam)", r"segundo especialistas", r"[ée] amplamente reconhecido",
        r"a ci[êe]ncia comprova", r"experts (say|argue|believe)", r"studies (show|suggest)",
        r"research (shows|suggests)", r"it is widely (acknowledged|recognized)",
    ]),
    ("intensificador", 1, [
        r"\bextremamente\b", r"\bincrivelmente\b", r"\babsolutamente\b", r"\bverdadeiramente\b",
        r"\bprofundamente\b", r"\bsignificativamente\b", r"\bdrasticamente\b", r"\bextraordinariamente\b",
        r"\bnotavelmente\b", r"\bindiscutivelmente\b", r"\binegavelmente\b",
        r"\bextremely\b", r"\bincredibly\b", r"\btruly\b", r"\bsignificantly\b", r"\bdramatically\b",
        r"\bremarkably\b", r"\bundoubtedly\b", r"\bfundamentally\b",
    ]),
    ("ressalva empilhada", 1, [
        r"pode potencialmente", r"talvez possa", r"poderia potencialmente", r"de certa forma",
        r"at[ée] certo ponto", r"pode ajudar a", r"busca garantir", r"visa (proporcionar|garantir)",
        r"could potentially", r"may potentially", r"might arguably", r"can help (to )?ensure",
    ]),
    ("gerundismo / burocratês", 1, [
        r"\bvou estar \w+ndo\b", r"\bestaremos \w+ndo\b", r"\bvamos estar \w+ndo\b",
        r"\bfoi realizad[ao]\b", r"\b[ée] realizad[ao]\b", r"\ba n[íi]vel de\b", r"\bno que tange\b",
        r"\bse configura como\b", r"\bconta com\b", r"\bdisp[õo]e de\b",
        r"\bserves as\b", r"\bfunctions as\b", r"\bboasts\b",
    ]),
    ("texto falando de si", 1, [
        r"como (mencionado|dito|visto) (acima|anteriormente)", r"como veremos (a seguir|adiante)",
        r"neste (artigo|post|guia|texto) (voc[êe] vai|vamos)", r"este texto tem como objetivo",
        r"as (mentioned|discussed) above", r"in this (article|post|guide),? (we|you)",
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
PLACEHOLDERS = [r"\[(nome|name|empresa|company|inserir[^\]]*|insert[^\]]*|seu nome|your name)\]",
                r"\bXXX+\b", r"lorem ipsum", r"\{\{[^}]+\}\}"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐✅❌✨]")


def strip_code(text):
    """Troca código e URLs por espaços, mantendo as quebras de linha (pra numeração bater)."""
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
    return [p.strip() for p in parts if len(p.split()) >= 1 and re.search(r"\w", p)]


def check(raw):
    hits = []  # (linha, peso, categoria, trecho)
    text = strip_code(raw)

    for ch, name in INVISIBLE.items():
        for m in re.finditer(re.escape(ch), raw):
            hits.append((line_of(raw, m.start()), 3, "caractere invisível", name))
    for pat in ARTIFACTS:
        for m in re.finditer(pat, raw):
            hits.append((line_of(raw, m.start()), 3, "artefato de IA", m.group(0)))
    for pat in PLACEHOLDERS:
        for m in re.finditer(pat, text, flags=re.I):
            hits.append((line_of(text, m.start()), 3, "placeholder esquecido", m.group(0)))

    for m in re.finditer(r"[—–]|\s--\s", text):
        hits.append((line_of(text, m.start()), 3, "travessão", repr(m.group(0).strip())))
    for m in re.finditer(r"[“”‘’]", text):
        hits.append((line_of(text, m.start()), 1, "aspas curvas", m.group(0)))
    for m in re.finditer(r"…", text):
        hits.append((line_of(text, m.start()), 1, "reticências unicode", "…"))

    for cat, weight, pats in LISTS:
        for pat in pats:
            for m in re.finditer(pat, text, flags=re.I | re.M):
                hits.append((line_of(text, m.start()), weight, cat, m.group(0).strip()))

    for i, line in enumerate(text.split("\n"), 1):
        s = line.strip()
        if re.match(r"^#{1,6}\s", s):
            words = [w for w in re.findall(r"[^\W\d_]+", s[1:].lstrip("# ")) if len(w) >= 2]
            if len(words) >= 3 and all(w[0].isupper() for w in words):
                hits.append((i, 2, "título em Title Case", s))
            if EMOJI.search(s):
                hits.append((i, 2, "emoji em título", s))
        if re.match(r"^([-*]|\d+\.)\s+\*\*[^*]+:\*\*|^([-*]|\d+\.)\s+\*\*[^*]+\*\*:", s):
            hits.append((i, 2, "lista com rótulo em negrito", s[:60]))
        if re.match(r"^([-*]|\d+\.)?\s*" + EMOJI.pattern, s):
            hits.append((i, 1, "emoji como marcador", s[:60]))

    stats = {}
    prose = re.sub(r"^\s*\|.*$", "", text, flags=re.M)  # tira tabelas
    sents = sentences(prose)
    lens = [len(s.split()) for s in sents]
    words = sum(lens)
    stats["palavras"] = words
    stats["frases"] = len(lens)
    if len(lens) >= 6:
        stats["média de palavras por frase"] = round(statistics.mean(lens), 1)
        stats["desvio padrão"] = round(statistics.pstdev(lens), 1)
        stats["frases < 8 palavras"] = sum(1 for n in lens if n < 8)
        stats["frases > 25 palavras"] = sum(1 for n in lens if n > 25)
        if words >= 150 and statistics.pstdev(lens) < 5:
            hits.append((0, 2, "ritmo uniforme", "frases quase todas do mesmo tamanho; misture curtas e longas"))
        if words >= 300 and (stats["frases < 8 palavras"] == 0 or stats["frases > 25 palavras"] == 0):
            hits.append((0, 1, "pouca variação", "falta frase bem curta ou bem longa"))

    paras = [p for p in re.split(r"\n\s*\n", prose) if len(p.split()) >= 15 and not p.lstrip().startswith(("#", "-", "*", ">"))]
    if len(paras) >= 4:
        plen = [len(p.split()) for p in paras]
        mean = statistics.mean(plen)
        if all(abs(n - mean) <= 0.15 * mean for n in plen):
            hits.append((0, 2, "parágrafos do mesmo tamanho", f"{len(paras)} parágrafos com ~{round(mean)} palavras"))
        firsts = [p.split()[0].lower().strip(",.:") for p in paras]
        for j in range(len(firsts) - 2):
            if firsts[j] == firsts[j + 1] == firsts[j + 2]:
                hits.append((0, 2, "aberturas repetidas", f"3 parágrafos seguidos começam com '{firsts[j]}'"))
                break

    excl = text.count("!")
    if len(lens) >= 4 and excl / max(len(lens), 1) > 0.3:
        hits.append((0, 2, "entusiasmo sintético", f"{excl} exclamações em {len(lens)} frases"))
    bold = len(re.findall(r"\*\*[^*\n]+\*\*", text))
    if words and bold / max(words, 1) * 100 > 2:
        hits.append((0, 1, "negrito demais", f"{bold} trechos em negrito em {words} palavras"))
    emojis = len(EMOJI.findall(text))
    if words and emojis / max(words, 1) * 100 > 1:
        hits.append((0, 1, "emoji demais", f"{emojis} emojis em {words} palavras"))

    hits.sort(key=lambda h: (h[0], -h[1], -len(h[3])))
    dedup = []
    for h in hits:  # tira achado que é pedaço de outro na mesma linha e categoria
        if any(d[0] == h[0] and d[2] == h[2] and h[3].lower() in d[3].lower() for d in dedup):
            continue
        dedup.append(h)
    return dedup, stats


def main():
    ap = argparse.ArgumentParser(description="Acha vícios de texto de IA (PT-BR e EN).")
    ap.add_argument("arquivo", help="caminho do arquivo, ou - pra ler da entrada padrão")
    ap.add_argument("--strict", action="store_true", help="sai com código 1 se houver achado forte")
    ap.add_argument("--min", type=int, default=1, choices=[1, 2, 3], help="peso mínimo pra mostrar")
    a = ap.parse_args()

    raw = sys.stdin.read() if a.arquivo == "-" else open(a.arquivo, encoding="utf-8").read()
    raw = unicodedata.normalize("NFC", raw)
    hits, stats = check(raw)
    label = {3: "FORTE", 2: "médio", 1: "fraco"}

    shown = [h for h in hits if h[1] >= a.min]
    for line, w, cat, snip in shown:
        where = f"L{line}" if line else "texto"
        print(f"[{label[w]:5}] {where:>6}  {cat}: {snip}")
    if not shown:
        print("Nada encontrado. Agora leia em voz alta.")
    print()
    print("  ".join(f"{k}: {v}" for k, v in stats.items()))
    strong = sum(1 for h in hits if h[1] == 3)
    print(f"achados: {len(hits)} (fortes: {strong})")
    if a.strict and strong:
        sys.exit(1)


if __name__ == "__main__":
    main()
