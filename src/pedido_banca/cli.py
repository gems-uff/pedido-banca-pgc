"""Linha de comando: pedido-banca."""

from __future__ import annotations

import argparse
import shutil
import sys
from importlib import resources
from pathlib import Path

from . import __version__
from .formulario import FORM_URL, ErroFormulario, baixar_formulario, preencher
from .modelo import ErroPedido, carregar_pedido

CACHE = Path.home() / ".cache" / "pedido-banca" / "Defesa_de_Dissertacao_de_Mestrado.pdf"


def _formulario(caminho: str | None, url: str) -> Path:
    if caminho:
        return Path(caminho)
    if not CACHE.exists():
        print(f"Baixando o formulário de {url}", file=sys.stderr)
        baixar_formulario(CACHE, url)
    return CACHE


def cmd_preencher(a: argparse.Namespace) -> None:
    json_path = Path(a.pedido)
    pedido = carregar_pedido(json_path, Path(a.membros) if a.membros else None)
    saida = (
        Path(a.saida)
        if a.saida
        else json_path.with_name(f"Pedido_Banca_{pedido.aluno.replace(' ', '_')}.pdf")
    )
    print(preencher(pedido, _formulario(a.formulario, a.url), saida))


def cmd_baixar(a: argparse.Namespace) -> None:
    print(baixar_formulario(Path(a.destino), a.url))


def cmd_modelo(a: argparse.Namespace) -> None:
    destino = Path(a.pasta)
    destino.mkdir(parents=True, exist_ok=True)
    for nome in ("banca.json", "membros.json"):
        alvo = destino / nome
        if alvo.exists():
            print(f"{alvo} já existe; mantido", file=sys.stderr)
            continue
        with resources.as_file(resources.files("pedido_banca") / "modelos" / nome) as src:
            shutil.copy(src, alvo)
        print(alvo)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="pedido-banca",
        description="Preenche o pedido de banca de mestrado do PGC/IC-UFF a partir de um JSON.",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("preencher", help="gera o PDF preenchido")
    p.add_argument("pedido", help="arquivo banca.json")
    p.add_argument("-m", "--membros", help="cadastro de membros (padrão: chave 'membros' do JSON)")
    p.add_argument("-o", "--saida", help="PDF de saída (padrão: ao lado do JSON)")
    p.add_argument("-f", "--formulario", help="PDF em branco (padrão: baixado do site do PGC)")
    p.add_argument("--url", default=FORM_URL, help="URL do formulário em branco")
    p.set_defaults(func=cmd_preencher)

    b = sub.add_parser("baixar-formulario", help="baixa o formulário em branco")
    b.add_argument("destino", nargs="?", default="Defesa_de_Dissertacao_de_Mestrado.pdf")
    b.add_argument("--url", default=FORM_URL)
    b.set_defaults(func=cmd_baixar)

    m = sub.add_parser("modelo", help="cria banca.json e membros.json de exemplo")
    m.add_argument("pasta", nargs="?", default=".")
    m.set_defaults(func=cmd_modelo)

    a = ap.parse_args(argv)
    try:
        a.func(a)
    except (ErroPedido, ErroFormulario) as e:
        print(f"erro: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
