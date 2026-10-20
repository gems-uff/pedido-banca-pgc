"""Dados de um pedido de banca: leitura do JSON, cadastro de membros e validação."""

from __future__ import annotations

import datetime
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

FORMATOS = ("presencial", "remoto", "hibrido")
MAX_TITULARES = 6


class ErroPedido(ValueError):
    """Pedido inválido ou incompleto."""


def cpf_valido(cpf: str) -> bool:
    """Confere os dígitos verificadores de um CPF (com ou sem pontuação)."""
    d = re.sub(r"\D", "", cpf)
    if len(d) != 11 or d == d[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(d[i]) * (n + 1 - i) for i in range(n))
        if (soma * 10 % 11) % 10 != int(d[n]):
            return False
    return True


def formatar_cpf(cpf: str) -> str:
    d = re.sub(r"\D", "", cpf)
    return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"


@dataclass
class Membro:
    nome: str
    instituicao: str = ""
    email: str = ""
    cpf: str = ""
    interno: bool = False  # interno ao PGC/UFF: o formulário só pede o nome
    passagem: bool = False
    diarias: str = "Não"

    @classmethod
    def de_dict(cls, d: dict) -> Membro:
        campos = set(cls.__dataclass_fields__)
        desconhecidos = set(d) - campos
        if desconhecidos:
            raise ErroPedido(f"Campos desconhecidos em membro: {sorted(desconhecidos)}")
        if not d.get("nome"):
            raise ErroPedido(f"Membro sem nome: {d}")
        return cls(**d)

    def validar(self, papel: str) -> None:
        if self.interno:
            return
        faltando = [c for c in ("instituicao", "email", "cpf") if not getattr(self, c)]
        if faltando:
            raise ErroPedido(f"{papel} externo {self.nome} sem: {', '.join(faltando)}")
        if not cpf_valido(self.cpf):
            raise ErroPedido(f"CPF inválido para {self.nome}: {self.cpf}")
        self.cpf = formatar_cpf(self.cpf)


@dataclass
class Pedido:
    aluno: str
    matricula: str
    orientadores: list[str]
    linha: str
    titulo: list[str]
    banca: list[Membro]
    suplente_interno: Membro
    suplente_externo: Membro
    formato: str = "presencial"
    justificativa: str = ""
    participantes_online: list[str] = field(default_factory=list)
    data_pedido: datetime.date = field(default_factory=datetime.date.today)

    def validar(self) -> None:
        if self.formato not in FORMATOS:
            raise ErroPedido(f"Formato deve ser um de {FORMATOS}, não '{self.formato}'")
        if self.formato != "presencial" and not self.justificativa:
            raise ErroPedido(f"Formato {self.formato} exige justificativa")
        if self.formato == "hibrido" and not self.participantes_online:
            raise ErroPedido("Formato híbrido exige participantes_online")
        if not 3 <= len(self.banca) <= MAX_TITULARES:
            raise ErroPedido(f"A banca deve ter de 3 a {MAX_TITULARES} membros, tem {len(self.banca)}")
        if all(m.interno for m in self.banca):
            raise ErroPedido("A banca precisa de pelo menos um membro externo")
        for m in self.banca:
            m.validar("Membro")
        self.suplente_externo.validar("Suplente")
        if self.suplente_externo.interno:
            raise ErroPedido("O suplente externo não pode ser interno")


def carregar_membros(caminho: Path | None) -> dict[str, dict]:
    if caminho is None:
        return {}
    try:
        return json.loads(Path(caminho).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ErroPedido(f"Cadastro de membros não encontrado: {caminho}") from None


def _resolver(m: str | dict, cadastro: dict[str, dict]) -> Membro:
    """Um membro pode ser uma chave do cadastro, {"ref": chave, ...extras} ou um dict completo."""
    if isinstance(m, str):
        if m not in cadastro:
            raise ErroPedido(f"Membro '{m}' não está no cadastro de membros")
        return Membro.de_dict(dict(cadastro[m]))
    m = dict(m)
    if "ref" in m:
        ref = m.pop("ref")
        if ref not in cadastro:
            raise ErroPedido(f"Membro '{ref}' não está no cadastro de membros")
        m = {**cadastro[ref], **m}
    return Membro.de_dict(m)


def carregar_pedido(caminho: Path, membros: Path | None = None) -> Pedido:
    """Lê banca.json. O cadastro vem de `membros` ou da chave "membros" do JSON (relativa a ele)."""
    caminho = Path(caminho)
    cfg = json.loads(caminho.read_text(encoding="utf-8"))
    if membros is None and cfg.get("membros"):
        membros = (caminho.parent / cfg["membros"]).expanduser()
    cadastro = carregar_membros(membros)

    obrigatorios = [
        "aluno",
        "matricula",
        "orientadores",
        "linha",
        "titulo",
        "banca",
        "suplente_interno",
        "suplente_externo",
    ]
    faltando = [c for c in obrigatorios if not cfg.get(c)]
    if faltando:
        raise ErroPedido(f"Faltam campos no pedido: {', '.join(faltando)}")

    titulo = cfg["titulo"]
    pedido = Pedido(
        aluno=cfg["aluno"],
        matricula=cfg["matricula"],
        orientadores=list(cfg["orientadores"]),
        linha=cfg["linha"],
        titulo=titulo if isinstance(titulo, list) else [titulo],
        banca=[_resolver(m, cadastro) for m in cfg["banca"]],
        suplente_interno=_resolver(cfg["suplente_interno"], cadastro),
        suplente_externo=_resolver(cfg["suplente_externo"], cadastro),
        formato=cfg.get("formato", "presencial").lower().replace("í", "i"),
        justificativa=cfg.get("justificativa", ""),
        participantes_online=list(cfg.get("participantes_online", [])),
    )
    if cfg.get("data_pedido"):
        pedido.data_pedido = datetime.date.fromisoformat(cfg["data_pedido"])
    pedido.validar()
    return pedido
