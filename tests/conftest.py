import json
import shutil
from importlib import resources
from pathlib import Path

import pytest

DADOS = Path(__file__).parent / "dados"
FORM = DADOS / "Defesa_de_Dissertacao_de_Mestrado-v8.pdf"


@pytest.fixture
def form() -> Path:
    return FORM


@pytest.fixture
def pasta_modelo(tmp_path) -> Path:
    """Cópia dos JSONs de exemplo distribuídos com o pacote."""
    for nome in ("banca.json", "membros.json"):
        with resources.as_file(resources.files("pedido_banca") / "modelos" / nome) as src:
            shutil.copy(src, tmp_path / nome)
    return tmp_path


def editar(caminho: Path, **mudancas) -> Path:
    cfg = json.loads(caminho.read_text(encoding="utf-8"))
    cfg.update(mudancas)
    caminho.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    return caminho
