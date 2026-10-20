import pymupdf
import pytest
from conftest import editar

from pedido_banca.formulario import ErroFormulario, Formulario, preencher
from pedido_banca.modelo import carregar_pedido


def palavras(pdf):
    doc = pymupdf.open(pdf)
    return [(pn, *w[:5]) for pn, pg in enumerate(doc) for w in pg.get_text("words")]


def a_direita_de(ws, rotulo, valor, indice=0):
    """O texto `valor` aparece na mesma linha e à direita do `indice`-ésimo `rotulo`."""
    rots = sorted((w for w in ws if w[5] == rotulo), key=lambda w: (w[0], w[4]))
    pn, _, _, x1, y1, _ = rots[indice]
    primeira = valor.split()[0]
    return any(w[0] == pn and w[5] == primeira and w[1] >= x1 and abs(w[4] - y1) < 4 for w in ws)


@pytest.fixture
def gerar(pasta_modelo, form, tmp_path):
    def _gerar(**mudancas):
        if mudancas:
            editar(pasta_modelo / "banca.json", **mudancas)
        pedido = carregar_pedido(pasta_modelo / "banca.json")
        return preencher(pedido, form, tmp_path / "saida.pdf")

    return _gerar


def test_cabecalho_e_membros(gerar):
    ws = palavras(gerar())
    assert a_direita_de(ws, "Aluno:", "Fulano")
    assert a_direita_de(ws, "Matrícula:", "M000.000.000")
    assert a_direita_de(ws, "Orientador(es):", "Ana")
    assert a_direita_de(ws, "Instituição:", "UFRJ", indice=2)
    assert a_direita_de(ws, "CPF:", "111.444.777", indice=2)
    assert a_direita_de(ws, "Email:", "daniel@exemplo.br", indice=2)
    assert a_direita_de(ws, "CPF:", "222.555.888", indice=6)  # suplente externo
    assert a_direita_de(ws, "interno:", "Carla")
    assert a_direita_de(ws, "Niterói,", "19")
    textos = {w[5] for w in ws}
    assert {"outubro", "26", "35", "46"} <= textos


def test_internos_sem_cpf_nem_email(gerar):
    ws = palavras(gerar())
    assert not a_direita_de(ws, "Email:", "ana@exemplo.br", indice=0)


def test_nome_do_suplente_externo_na_linha_do_cpf(gerar):
    ws = palavras(gerar())
    cpf = sorted((w for w in ws if w[5] == "CPF:"), key=lambda w: (w[0], w[4]))[6]
    elisa = next(w for w in ws if w[5] == "Elisa")
    assert elisa[0] == cpf[0] and abs(elisa[4] - cpf[4]) < 4


def test_titulo_em_duas_linhas(gerar):
    ws = palavras(gerar(titulo=["Primeira linha", "Segunda linha"]))
    y1 = next(w[4] for w in ws if w[5] == "Primeira")
    y2 = next(w[4] for w in ws if w[5] == "Segunda")
    assert y2 > y1 + 8


def _marcas(pdf):
    """Centros dos X desenhados (cada X são duas linhas com o mesmo centro)."""
    doc = pymupdf.open(pdf)
    return sorted(
        {
            (pn, round((d["rect"].x0 + d["rect"].x1) / 2), round((d["rect"].y0 + d["rect"].y1) / 2))
            for pn, pg in enumerate(doc)
            for d in pg.get_drawings()
            if d["rect"].width < 6 and d["rect"].height < 6
        }
    )


@pytest.mark.parametrize("formato, y", [("presencial", 293), ("remoto", 318), ("hibrido", 342)])
def test_marca_formato(gerar, formato, y):
    mud = {"formato": formato}
    if formato != "presencial":
        mud.update(justificativa="Motivo", participantes_online=["Daniel Teste Rocha"])
    pdf = gerar(**mud)
    marcas = [m for m in _marcas(pdf) if m[0] == 0 and m[1] < 85]
    assert len(marcas) == 1 and abs(marcas[0][2] - y) <= 2
    if formato != "presencial":
        assert a_direita_de(palavras(pdf), "Justificativa:", "Motivo", indice=0 if formato == "remoto" else 1)


def test_passagem_sim_e_nao(gerar):
    banca = ["orientadora", "interno1", {"ref": "externo1", "passagem": True}]
    marcas = [m for m in _marcas(gerar(banca=banca)) if m[1] > 150]
    xs = sorted(m[1] for m in marcas)
    assert len(marcas) == 2  # membro 3 (Sim) e suplente externo (Não)
    assert xs[0] < 170 < xs[1]


def test_formulario_errado(tmp_path, pasta_modelo):
    vazio = tmp_path / "vazio.pdf"
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "outro documento")
    doc.save(vazio)
    with pytest.raises(ErroFormulario, match="Aluno:"):
        preencher(carregar_pedido(pasta_modelo / "banca.json"), vazio, tmp_path / "x.pdf")


def test_rotulos_do_formulario_v8(form):
    f = Formulario(form)
    assert len(f.todas("CPF:")) == 7
    assert len(f.todas("hospedagem?")) == 7
