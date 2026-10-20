import datetime

import pytest
from conftest import editar

from pedido_banca.modelo import ErroPedido, carregar_pedido, cpf_valido, formatar_cpf


@pytest.mark.parametrize("cpf", ["111.444.777-35", "11144477735", "333.666.999-57"])
def test_cpf_valido(cpf):
    assert cpf_valido(cpf)


@pytest.mark.parametrize("cpf", ["111.444.777-36", "111.111.111-11", "123", ""])
def test_cpf_invalido(cpf):
    assert not cpf_valido(cpf)


def test_formatar_cpf():
    assert formatar_cpf("11144477735") == "111.444.777-35"


def test_carrega_exemplo(pasta_modelo):
    p = carregar_pedido(pasta_modelo / "banca.json")
    assert p.aluno == "Fulano de Tal"
    assert p.titulo == ["Um Título de Dissertação de Exemplo"]
    assert [m.nome for m in p.banca][-1] == "Daniel Teste Rocha"
    assert p.suplente_externo.cpf == "222.555.888-46"
    assert p.data_pedido == datetime.date(2026, 10, 19)


def test_ref_com_campos_extras(pasta_modelo):
    banca = ["orientadora", "interno1", {"ref": "externo1", "passagem": True, "diarias": "2 diárias"}]
    p = carregar_pedido(editar(pasta_modelo / "banca.json", banca=banca))
    assert p.banca[2].passagem and p.banca[2].diarias == "2 diárias"
    assert p.banca[2].nome == "Daniel Teste Rocha"


def test_membro_por_extenso_sem_cadastro(pasta_modelo):
    banca = [
        {"nome": "A", "interno": True},
        {"nome": "B", "interno": True},
        {"nome": "C", "instituicao": "X", "email": "c@x", "cpf": "11144477735"},
    ]
    p = carregar_pedido(editar(pasta_modelo / "banca.json", banca=banca))
    assert p.banca[2].cpf == "111.444.777-35"  # normalizado


def test_data_padrao_e_hoje(pasta_modelo):
    p = carregar_pedido(editar(pasta_modelo / "banca.json", data_pedido=""))
    assert p.data_pedido == datetime.date.today()


@pytest.mark.parametrize(
    "mudancas, mensagem",
    [
        ({"banca": ["orientadora", "interno1", "interno2"]}, "externo"),
        ({"banca": ["orientadora", "externo1"]}, "de 3 a 6"),
        ({"banca": ["orientadora", "interno1", "inexistente"]}, "não está no cadastro"),
        ({"formato": "hibrido", "justificativa": "x"}, "participantes_online"),
        ({"formato": "remoto"}, "justificativa"),
        ({"formato": "online"}, "Formato deve ser"),
        ({"suplente_externo": "interno2"}, "não pode ser interno"),
        ({"aluno": ""}, "aluno"),
        (
            {"banca": ["orientadora", "interno1", {"ref": "externo1", "cpf": "111.444.777-00"}]},
            "CPF inválido",
        ),
        ({"banca": ["orientadora", "interno1", {"ref": "externo1", "email": ""}]}, "sem: email"),
        ({"banca": ["orientadora", "interno1", {"ref": "externo1", "papel": "x"}]}, "desconhecidos"),
    ],
)
def test_erros(pasta_modelo, mudancas, mensagem):
    with pytest.raises(ErroPedido, match=mensagem):
        carregar_pedido(editar(pasta_modelo / "banca.json", **mudancas))


def test_cadastro_ausente(pasta_modelo):
    (pasta_modelo / "membros.json").unlink()
    with pytest.raises(ErroPedido, match="Cadastro de membros"):
        carregar_pedido(pasta_modelo / "banca.json")
