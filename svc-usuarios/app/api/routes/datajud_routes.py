import json
from urllib.error import HTTPError as UrlHTTPError, URLError
from urllib.request import Request as UrlRequest, urlopen
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import base_guard
from app.api.schemas.user_schema import ConsultaDataJudIn
from app.infrastructure.database.models.user_model import Usuario, UsuarioChavePublica
from app.infrastructure.database.session import get_db

router = APIRouter()

@router.post("/v1/lex/usuarios/consultas/datajud")
def consultar_processo_datajud(
    body: ConsultaDataJudIn,
    db: Session = Depends(get_db),
    payload=Depends(base_guard),
):
    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id") or user_id
    user = db.query(Usuario.id).filter_by(id=user_id, tenant_id=tenant_id).first()
    if not user:
        raise HTTPException(404, "Usuário não encontrado")

    tribunal = body.tribunal.strip().lower()
    aliases_superiores = {"stj": "stj", "tst": "tst", "tse": "tse", "stm": "stm"}
    aliases_estaduais = {
        "tjac": "tjac", "tjal": "tjal", "tjam": "tjam", "tjap": "tjap", "tjba": "tjba",
        "tjce": "tjce", "tjdft": "tjdft", "tjes": "tjes", "tjgo": "tjgo", "tjma": "tjma",
        "tjmg": "tjmg", "tjms": "tjms", "tjmt": "tjmt", "tjpa": "tjpa", "tjpb": "tjpb",
        "tjpe": "tjpe", "tjpi": "tjpi", "tjpr": "tjpr", "tjrj": "tjrj", "tjrn": "tjrn",
        "tjro": "tjro", "tjrr": "tjrr", "tjrs": "tjrs", "tjsc": "tjsc", "tjse": "tjse",
        "tjsp": "tjsp", "tjto": "tjto",
    }
    aliases_federais = {f"trf{region}": f"trf{region}" for region in range(1, 7)}
    aliases_trabalho = {f"trt{region}": f"trt{region}" for region in range(1, 25)}
    ufs = ("ac", "al", "am", "ap", "ba", "ce", "dft", "es", "go", "ma", "mg", "ms", "mt", "pa", "pb", "pe", "pi", "pr", "rj", "rn", "ro", "rr", "rs", "sc", "se", "sp", "to")
    aliases_eleitorais = {f"tre-{uf}": f"tre-{uf}" for uf in ufs}
    aliases_militares = {alias: alias for alias in ("tjmmg", "tjmrs", "tjmsp")}
    aliases = {**aliases_superiores, **aliases_estaduais, **aliases_federais, **aliases_trabalho, **aliases_eleitorais, **aliases_militares}
    justica = "Justi" + chr(231) + "a"
    orgao_por_ramo = {
        **{alias: "Tribunais Superiores" for alias in aliases_superiores},
        **{alias: f"{justica} Federal" for alias in aliases_federais},
        **{alias: f"{justica} do Trabalho" for alias in aliases_trabalho},
        **{alias: f"{justica} Eleitoral" for alias in aliases_eleitorais},
        **{alias: f"{justica} Militar" for alias in aliases_militares},
        **{alias: f"{justica} Estadual" for alias in aliases_estaduais},
    }
    alias = aliases.get(tribunal)
    if not alias:
        raise HTTPException(422, "Tribunal inválido ou não disponível para consulta.")
    key_orgao = orgao_por_ramo[tribunal]
    numero = "".join(char for char in body.numeroProcesso if char in "0123456789")
    if len(numero) != 20:
        raise HTTPException(422, "Informe o número CNJ completo, com 20 dígitos.")

    key_row = db.query(UsuarioChavePublica).filter_by(
        user_id=user_id,
        orgao=key_orgao,
    ).first()
    if not key_row or not key_row.chave_publica.strip():
        raise HTTPException(400, f"Cadastre a chave pública do DataJud para {key_orgao} no Perfil.")

    api_key = key_row.chave_publica.strip()
    if api_key[:7].lower() == "apikey ":
        api_key = api_key[7:].strip()

    # Release the MySQL transaction before waiting on the external DataJud API.
    db.rollback()

    request_body = json.dumps({
        "query": {"match": {"numeroProcesso": numero}},
        "size": 1,
    }).encode("utf-8")
    request = UrlRequest(
        f"https://api-publica.datajud.cnj.jus.br/api_publica_{alias}/_search",
        data=request_body,
        headers={
            "Authorization": f"APIKey {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=25) as response:
            return json.loads(response.read().decode("utf-8"))
    except UrlHTTPError as exc:
        if exc.code in (401, 403):
            raise HTTPException(502, "O DataJud recusou a chave pública. Confira a chave cadastrada no Perfil.") from exc
        if exc.code == 429:
            raise HTTPException(503, "O DataJud está recebendo muitas consultas. Tente novamente em instantes.") from exc
        raise HTTPException(502, f"O DataJud respondeu com erro ({exc.code}).") from exc
    except (URLError, TimeoutError) as exc:
        raise HTTPException(502, "Não foi possível conectar ao DataJud no momento. Tente novamente em instantes.") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(502, "O DataJud retornou uma resposta inválida.") from exc
