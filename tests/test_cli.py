from pathlib import Path

import pymupdf

from pedido_banca.cli import main


def test_modelo_e_preencher(tmp_path, form, capsys):
    assert main(["modelo", str(tmp_path)]) == 0
    assert (tmp_path / "banca.json").exists() and (tmp_path / "membros.json").exists()
    saida = tmp_path / "out.pdf"
    assert main(["preencher", str(tmp_path / "banca.json"), "-f", str(form), "-o", str(saida)]) == 0
    assert "Fulano" in pymupdf.open(saida)[0].get_text()


def test_saida_padrao(tmp_path, form):
    main(["modelo", str(tmp_path)])
    assert main(["preencher", str(tmp_path / "banca.json"), "-f", str(form)]) == 0
    assert (tmp_path / "Pedido_Banca_Fulano_de_Tal.pdf").exists()


def test_modelo_nao_sobrescreve(tmp_path):
    (tmp_path / "banca.json").write_text("{}")
    main(["modelo", str(tmp_path)])
    assert (tmp_path / "banca.json").read_text() == "{}"


def test_erro_vira_mensagem(tmp_path, form, capsys):
    main(["modelo", str(tmp_path)])
    (tmp_path / "membros.json").unlink()
    assert main(["preencher", str(tmp_path / "banca.json"), "-f", str(form)]) == 1
    assert "Cadastro de membros" in capsys.readouterr().err


def test_exemplo_do_readme_esta_atualizado(tmp_path):
    """O PDF em exemplo/ corresponde ao que a versão atual gera a partir de exemplo/banca.json."""
    ex = Path(__file__).parents[1] / "exemplo"
    saida = tmp_path / "ex.pdf"
    args = ["preencher", str(ex / "banca.json"), "-o", str(saida)]
    assert main([*args, "-f", str(ex / "Defesa_de_Dissertacao_de_Mestrado-v8.pdf")]) == 0
    gerado = [pg.get_text("words") for pg in pymupdf.open(saida)]
    publicado = [pg.get_text("words") for pg in pymupdf.open(ex / "Pedido_Banca_exemplo.pdf")]
    assert gerado == publicado, "regere exemplo/Pedido_Banca_exemplo.pdf (ver README)"
