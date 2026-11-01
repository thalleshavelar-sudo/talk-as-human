# talk-as-human

Skill pra Claude (Claude Code, Claude.ai e qualquer agente que lê `SKILL.md`) que escreve e reescreve texto pra soar como gente. Funciona em português e inglês e vem com o jeito de falar do Thalles embutido.

Junta duas skills conhecidas, o [humanizer](https://github.com/blader/humanizer) e o [no-ai-slop](https://github.com/realrossmanngroup/no_ai_slop_writing_rules), e acrescenta o que faltava nelas: filtros pros vícios de IA em português brasileiro, um perfil de voz pessoal e um script que acha os vícios automaticamente.

## O que ela faz

Você manda um texto (ou pede pra ela escrever um) e ela:

1. descobre o canal e o leitor (WhatsApp, e-mail, post, README, commit);
2. marca os vícios de IA com 32 filtros, do mais forte pro mais fraco;
3. roda o `slop_check.py` quando tem terminal;
4. reescreve sem inventar fato, número, nome ou citação;
5. confere de novo os vícios que mais sobrevivem e entrega a versão final.

Os filtros cobrem:

| Grupo | Exemplos |
|---|---|
| Encenação | "não é X, é Y", fecho de efeito ("E isso muda tudo."), "a verdade é que", pergunta-isca ("Você já parou pra pensar?"), discutir com objeção que ninguém fez |
| Ritmo de fábrica | trio forçado, frases e parágrafos do mesmo tamanho, travessão, ressalva empilhada, "além disso / nesse sentido / vale ressaltar", gerundismo |
| Inflação | mergulhar, alavancar, potencializar, robusto, crucial, jornada, cenário, intensificador sem número, "papel fundamental", linguagem de folder, "especialistas afirmam" sem fonte, "conta com" no lugar de "tem" |
| Formatação | negrito de enfeite, lista com **Rótulo:**, Título Em Title Case, emoji em título, aspas curvas, exclamação em tudo |
| Sobras de chat | "Ótima pergunta!", "Espero ter ajudado", "Quer que eu...?", "até a data do meu treinamento", `oaicite`, `turn0search0`, caractere invisível, `[Nome]` esquecido |
| Leitor errado | reexplicar o que a pessoa já sabe, resposta na última linha, registro errado pro canal |

## Instalação

Claude Code, pra todos os projetos:

```bash
git clone https://github.com/thalleshavelar-sudo/talk-as-human.git ~/.claude/skills/talk-as-human
```

Só num projeto:

```bash
git clone https://github.com/thalleshavelar-sudo/talk-as-human.git .claude/skills/talk-as-human
```

Claude.ai: compacte a pasta em `.zip` e envie na área de Skills das configurações.

Outros agentes (Cursor, Codex, etc.): aponte o arquivo de regras deles pro `SKILL.md`.

## Uso

```
/talk-as-human reescreve isso: <texto>
```

Ou só peça: "humaniza esse texto", "tira a cara de IA", "escreve essa mensagem do meu jeito". Se mandar uma amostra do seu texto junto, ela segue a amostra.

O checador roda sozinho, sem dependência:

```bash
python3 scripts/slop_check.py rascunho.md
echo "Ótima pergunta! Vale ressaltar que..." | python3 scripts/slop_check.py -
python3 scripts/slop_check.py --strict --min 3 post.txt   # código 1 se achar algo forte, bom pra CI
```

Saída de exemplo:

```
[FORTE]     L3  contraste encenado (não é X, é Y): Não é só um app, é
[FORTE]     L3  resíduo de chat: Ótima pergunta
[FORTE]     L3  travessão: '—'
[médio]     L3  conectivo de redação: Vale ressaltar
[médio]     L3  palavra de IA: robusta
```

O script acha palavra e forma. Encenação, fato inventado e leitor errado continuam sendo trabalho de leitura, e é isso que o `SKILL.md` ensina.

## Estrutura

```
SKILL.md                     regras, filtros e processo
references/filtros-pt-br.md  listas de palavras e expressões em português, com troca
references/filters-en.md     o mesmo em inglês
references/voz-thalles.md    perfil de voz do Thalles por canal (casual, profissional, público)
scripts/slop_check.py        checador automático
```

## Ensinando sua voz

Abra `references/voz-thalles.md` e cole mensagens reais suas no fim, dizendo o canal de cada uma. Quanto mais amostra, melhor ela acerta. Se quiser usar a skill com a voz de outra pessoa, copie o arquivo e troque as amostras.

## Créditos

- [blader/humanizer](https://github.com/blader/humanizer), de Siqi Chen, licença MIT. Base dos filtros de encenação, ritmo, inflação e sobras de chat.
- [Wikipedia: Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), do WikiProject AI Cleanup.
- [realrossmanngroup/no_ai_slop_writing_rules](https://github.com/realrossmanngroup/no_ai_slop_writing_rules). Ideias de títulos dramáticos, palavras-escudo, artefatos de marcação, métricas de variação de frase e parágrafo. O texto aqui foi reescrito, não copiado.

## Licença

MIT. Veja [LICENSE](LICENSE) e [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
