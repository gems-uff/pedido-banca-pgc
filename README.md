# pedido-banca-pgc

[![CI](https://github.com/gems-uff/pedido-banca-pgc/actions/workflows/ci.yml/badge.svg)](https://github.com/gems-uff/pedido-banca-pgc/actions/workflows/ci.yml)

Preenche o formulário de **pedido de banca de defesa de dissertação de mestrado** do
[PGC/IC-UFF](https://www.ic.uff.br/formularios-e-requerimentos-pos/) a partir de um arquivo JSON.
O resultado é o PDF oficial preenchido, pronto para o orientador assinar.

A ideia é descrever a banca uma vez em `banca.json` e regerar o PDF sempre que algo mudar
(data, formato, um membro). Os membros podem ser escritos por extenso no próprio
`banca.json` ou vir de um cadastro, `membros.json`, reaproveitado entre pedidos.

## Demonstração

A pasta [`exemplo/`](exemplo) tem um pedido completo com dados fictícios:

| Arquivo | Conteúdo |
|---|---|
| [`banca.json`](exemplo/banca.json) | pedido híbrido, com coorientador, título em duas linhas e um membro externo com passagem |
| [`Defesa_de_Dissertacao_de_Mestrado-v8.pdf`](exemplo/Defesa_de_Dissertacao_de_Mestrado-v8.pdf) | formulário em branco do PGC |
| [`Pedido_Banca_exemplo.pdf`](exemplo/Pedido_Banca_exemplo.pdf) | resultado esperado |

Para gerar o PDF você mesmo (requer [uv](https://docs.astral.sh/uv/)):

```bash
git clone https://github.com/gems-uff/pedido-banca-pgc
cd pedido-banca-pgc
uv run pedido-banca preencher exemplo/banca.json \
    -f exemplo/Defesa_de_Dissertacao_de_Mestrado-v8.pdf -o meu_teste.pdf
open meu_teste.pdf      # macOS; no Linux, xdg-open meu_teste.pdf
```

Depois, mude algo em `exemplo/banca.json` (o formato para `presencial`, um nome, um CPF
inválido...) e rode de novo para ver o efeito ou a mensagem de erro.

## Instalação

Requer Python 3.10 ou superior.

```bash
uv tool install git+https://github.com/gems-uff/pedido-banca-pgc
# ou
pipx install git+https://github.com/gems-uff/pedido-banca-pgc
```

## Uso

```bash
pedido-banca modelo minha-banca/        # cria banca.json e membros.json de exemplo
# edite os dois arquivos
pedido-banca preencher minha-banca/banca.json
```

O PDF é gravado ao lado do JSON (`Pedido_Banca_<Aluno>.pdf`). Na primeira execução, o
formulário em branco é baixado do site do PGC e guardado em `~/.cache/pedido-banca/`.

Opções de `preencher`:

| Opção | Efeito |
|---|---|
| `-m, --membros` | cadastro de membros (padrão: a chave `membros` do `banca.json`) |
| `-o, --saida` | PDF de saída |
| `-f, --formulario` | PDF em branco a usar, em vez do baixado |
| `--url` | URL do formulário em branco, se o PGC publicar outra versão |

**Confira sempre o PDF gerado antes de assinar.**

## `membros.json`

Um objeto em que cada chave é um apelido que você escolhe:

```json
{
  "fulana":  {"nome": "Fulana Exemplo da Silva", "instituicao": "UFF", "email": "fulana@exemplo.br", "interno": true},
  "beltrano": {"nome": "Beltrano Teste Rocha", "instituicao": "UFRJ", "email": "beltrano@exemplo.br", "cpf": "111.444.777-35"}
}
```

- `interno: true` marca membros internos ao PGC. Para eles, o formulário pede só o nome.
- Membros externos precisam de `instituicao`, `email` e `cpf`, que é validado pelos dígitos verificadores.
- Campos opcionais: `passagem` (`true`/`false`, padrão `false`) e `diarias` (texto, padrão `"Não"`).

> ⚠️ O cadastro tem CPFs. Guarde-o fora de repositórios públicos. O `.gitignore` deste
> projeto ignora qualquer `membros.json`.

## `banca.json`

```json
{
  "membros": "membros.json",
  "aluno": "Fulano de Tal",
  "matricula": "M000.000.000",
  "orientadores": ["Fulana Exemplo da Silva"],
  "linha": "Engenharia de Sistemas e Informação",
  "titulo": "Título da Dissertação",
  "formato": "presencial",
  "banca": ["fulana", "ciclano", "beltrano"],
  "suplente_interno": "outro",
  "suplente_externo": "mais_um",
  "data_pedido": "2026-10-19"
}
```

- `membros`: caminho do cadastro, relativo ao `banca.json`.
- `titulo`: texto ou lista de linhas. Use uma lista quando o título não couber numa linha;
  nesse caso a fonte fica um pouco menor.
- `formato`: `presencial`, `remoto` (exige `justificativa`) ou `hibrido` (exige
  `justificativa` e `participantes_online`, uma lista de nomes).
- `banca`: de 3 a 6 membros, com pelo menos um externo, na ordem em que devem aparecer.
  O orientador e o coorientador entram aqui como membros comuns.
- `data_pedido`: data no formato `AAAA-MM-DD`. Sem ela, vale a data de hoje.

Cada membro (em `banca` ou nos suplentes) pode ser:

- um apelido do cadastro: `"fulana"`;
- um apelido com campos sobrescritos: `{"ref": "beltrano", "passagem": true, "diarias": "2 diárias"}`;
- um membro completo, sem cadastro: `{"nome": "...", "instituicao": "...", "email": "...", "cpf": "..."}`.

## Como funciona

O PDF do PGC não tem campos de formulário, então o texto é sobreposto às linhas em branco.
As posições são calculadas a partir dos rótulos impressos no próprio PDF (`CPF:`, `Email:`,
`hospedagem?`...), sem coordenadas fixas. Assim, pequenas mudanças de layout em versões
futuras do formulário não devem quebrar o preenchimento. Se o PGC mudar o formulário de
verdade, o programa avisa qual rótulo não encontrou.

Versão do formulário testada: `Defesa_de_Dissertacao_de_Mestrado-v8.pdf` (28/04/2025).

## Desenvolvimento

```bash
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

Os testes usam uma cópia do formulário em branco (`tests/dados/`) e dados fictícios. Se uma
mudança alterar o PDF gerado, regere o exemplo (um teste avisa quando ele fica desatualizado):

```bash
uv run pedido-banca preencher exemplo/banca.json \
    -f exemplo/Defesa_de_Dissertacao_de_Mestrado-v8.pdf -o exemplo/Pedido_Banca_exemplo.pdf
```

 Ideias e
correções são bem-vindas via issues e pull requests. Um próximo passo natural é dar suporte
aos formulários de exame de qualificação e de defesa de tese.

## Licença

[MIT](LICENSE)
