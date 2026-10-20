"""Sobreposição de texto no formulário de pedido de banca do PGC.

O PDF do PGC não tem campos de formulário. As posições são achadas pelos
rótulos impressos no próprio PDF (CPF:, Email:, hospedagem?...), e não por
coordenadas fixas, para tolerar pequenas mudanças de layout.
"""

from __future__ import annotations

import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from .modelo import Membro, Pedido

FORM_URL = "https://www.ic.uff.br/wp-content/uploads/2025/05/Defesa_de_Dissertacao_de_Mestrado-v8.pdf"
MESES = [
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
]
FONTE = "helv"
TAM = 9.5
TAM_TITULO_LONGO = 8.6
# distância entre o fundo da caixa de um rótulo e a linha de base do texto inserido
ELEVACAO = 3.3
VAGAS = 6


class ErroFormulario(RuntimeError):
    """O formulário não tem os rótulos esperados (provavelmente outra versão)."""


@dataclass
class Palavra:
    pagina: int
    x0: float
    y0: float
    x1: float
    y1: float
    texto: str


def baixar_formulario(destino: Path, url: str = FORM_URL) -> Path:
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, destino)
    return destino


class Formulario:
    def __init__(self, caminho: Path):
        self.doc = pymupdf.open(caminho)
        self.palavras = [
            Palavra(pn, *w[:5])
            for pn, pagina in enumerate(self.doc)
            for w in sorted(pagina.get_text("words"), key=lambda w: (round(w[3]), w[0]))
        ]

    # --- busca de rótulos -------------------------------------------------

    def todas(self, texto: str) -> list[Palavra]:
        return [p for p in self.palavras if p.texto == texto]

    def rotulo(self, texto: str, indice: int = 0) -> Palavra:
        achadas = self.todas(texto)
        if len(achadas) <= indice:
            raise ErroFormulario(f"Rótulo '{texto}' (#{indice + 1}) não encontrado no formulário")
        return achadas[indice]

    def na_linha(self, ref: Palavra, pred, tol: float = 3) -> list[Palavra]:
        return [p for p in self.palavras if p.pagina == ref.pagina and abs(p.y1 - ref.y1) < tol and pred(p)]

    # --- escrita ----------------------------------------------------------

    def escrever(self, pagina: int, x: float, y_fundo: float, texto: str, tam: float = TAM) -> None:
        self.doc[pagina].insert_text((x, y_fundo - ELEVACAO), texto, fontsize=tam, fontname=FONTE)

    def apos(self, ref: Palavra, texto: str, folga: float = 4, tam: float = TAM) -> None:
        self.escrever(ref.pagina, ref.x1 + folga, ref.y1, texto, tam)

    def marcar(self, pagina: int, cx: float, cy: float, meio: float) -> None:
        """Desenha um X centrado em (cx, cy)."""
        pg = self.doc[pagina]
        pg.draw_line((cx - meio, cy - meio), (cx + meio, cy + meio), width=0.9)
        pg.draw_line((cx - meio, cy + meio), (cx + meio, cy - meio), width=0.9)

    def marcar_colchetes(self, rotulo: Palavra) -> None:
        """Marca o "[ ]" que precede o rótulo na mesma linha."""
        abre = self.na_linha(rotulo, lambda p: p.texto == "[" and p.x1 < rotulo.x0)[-1]
        fecha = self.na_linha(rotulo, lambda p: p.texto == "]" and p.x0 > abre.x1)[0]
        base = abre.y1 - 2.5  # Calibri 10: descendente de 2.5 pt
        self.marcar(abre.pagina, (abre.x1 + fecha.x0) / 2, base - 3.4, 1.9)

    def marcar_caixa(self, caixa: Palavra) -> None:
        base = caixa.y1 - 2.9  # glifo □ (NotoSansSymbols 10)
        self.marcar(caixa.pagina, (caixa.x0 + caixa.x1) / 2, base - 3.3, 2.2)

    def salvar(self, saida: Path) -> None:
        self.doc.save(saida, garbage=3, deflate=True)


def _escrever_membro(f: Formulario, i: int, m: Membro, x_nome: float | None = None) -> None:
    cpf = f.rotulo("CPF:", i)
    f.escrever(cpf.pagina, x_nome if x_nome is not None else 90, cpf.y1, m.nome)
    f.apos(f.rotulo("Instituição:", i), m.instituicao)
    if m.interno:
        return  # para examinadores internos ao PGC basta o nome
    num, dv = m.cpf.split("-")
    f.apos(cpf, num, folga=6)
    hifens = f.na_linha(cpf, lambda p: p.x0 > cpf.x1 and "-" in p.texto)
    if not hifens:
        raise ErroFormulario(f"Hífen do CPF não encontrado na vaga {i + 1}")
    h = hifens[0]
    # o hífen pode ser uma palavra solta ("-") ou parte de "______-____"
    x_hifen = h.x0 + (h.x1 - h.x0) * (h.texto.index("-") + 1) / len(h.texto.rstrip("​"))
    f.escrever(cpf.pagina, x_hifen + 2, cpf.y1, dv)
    f.apos(f.rotulo("Email:", i), m.email)
    hosp = f.rotulo("hospedagem?", i)
    caixas = f.na_linha(hosp, lambda p: p.texto == "□", tol=4)
    if len(caixas) < 2:
        raise ErroFormulario(f"Caixas Sim/Não não encontradas para a vaga {i + 1}")
    f.marcar_caixa(caixas[0] if m.passagem else caixas[1])
    f.apos(hosp, m.diarias, folga=6)


def preencher(pedido: Pedido, formulario: Path, saida: Path) -> Path:
    f = Formulario(formulario)

    f.apos(f.rotulo("Aluno:"), pedido.aluno)
    f.apos(f.rotulo("Matrícula:"), pedido.matricula)
    f.apos(f.rotulo("Orientador(es):"), " e ".join(pedido.orientadores))
    f.apos(f.rotulo("Pesquisa:"), pedido.linha, folga=12)
    rot_titulo = f.rotulo("Dissertação:")
    tam = TAM if len(pedido.titulo) == 1 else TAM_TITULO_LONGO
    for n, linha in enumerate(pedido.titulo):
        # a 1ª linha fica sobre o sublinhado do campo; as demais, logo abaixo
        f.escrever(rot_titulo.pagina, rot_titulo.x1 + 2, rot_titulo.y1 + n * 11, linha, tam)

    rotulos = {"presencial": "Presencial", "remoto": "Remoto", "hibrido": "Híbrido"}
    f.marcar_colchetes(f.rotulo(rotulos[pedido.formato]))
    if pedido.formato == "remoto":
        f.apos(f.rotulo("Justificativa:", 0), pedido.justificativa, tam=9)
    elif pedido.formato == "hibrido":
        f.apos(f.rotulo("Justificativa:", 1), pedido.justificativa, tam=9)
        f.apos(f.rotulo("online:"), ", ".join(pedido.participantes_online), tam=9)

    for i, m in enumerate(pedido.banca):
        _escrever_membro(f, i, m)
    f.apos(f.rotulo("interno:"), pedido.suplente_interno.nome, folga=8)
    # o suplente externo ocupa a 7ª vaga; o nome vai na linha em branco do CPF
    _escrever_membro(f, VAGAS, pedido.suplente_externo, x_nome=93)

    d = pedido.data_pedido
    niteroi = f.rotulo("Niterói,")
    des = f.na_linha(niteroi, lambda p: p.texto == "de" and p.x0 > niteroi.x1)
    ano = f.na_linha(niteroi, lambda p: p.texto.startswith("20") and p.x0 > niteroi.x1)
    if len(des) < 2 or not ano:
        raise ErroFormulario("Linha da data não encontrada")
    f.apos(niteroi, str(d.day), folga=5)
    f.apos(des[0], MESES[d.month - 1], folga=6)
    f.apos(ano[0], str(d.year)[2:], folga=0)

    f.salvar(saida)
    return Path(saida)
