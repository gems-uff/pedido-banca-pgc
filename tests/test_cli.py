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
