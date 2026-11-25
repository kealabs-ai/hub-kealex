"""
Modal Padrão Compartilhado - Reutilizável em todos os serviços
Fornece estruturas genéricas para modais de confirmação, formulário, etc.
"""

from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from enum import Enum


class ModalType(str, Enum):
    """Tipos de modal disponíveis"""
    CONFIRMACAO = "confirmacao"
    FORMULARIO = "formulario"
    ALERTA = "alerta"
    SUCESSO = "sucesso"
    ERRO = "erro"
    INFORMACAO = "informacao"
    CARREGAMENTO = "carregamento"


class ModalButton(BaseModel):
    """Botão do modal"""
    id: str
    label: str
    tipo: str = "default"  # default, primary, danger, success
    acao: str  # callback action
    disabled: bool = False


class ModalField(BaseModel):
    """Campo de formulário dentro do modal"""
    id: str
    label: str
    tipo: str  # text, email, password, number, select, textarea, checkbox, radio, date
    placeholder: Optional[str] = None
    valor: Optional[Any] = None
    obrigatorio: bool = False
    validacao: Optional[str] = None  # regex pattern
    opcoes: Optional[List[Dict[str, str]]] = None  # para select/radio
    disabled: bool = False
    help_text: Optional[str] = None


class ModalConfig(BaseModel):
    """Configuração do modal"""
    tamanho: str = "md"  # sm, md, lg, xl
    centralizacao: bool = True
    fechar_ao_clicar_fora: bool = False
    mostrar_header: bool = True
    mostrar_footer: bool = True
    animacao: str = "fade"  # fade, slide, zoom


class Modal(BaseModel):
    """Modal Padrão - Estrutura principal"""
    id: str
    tipo: ModalType
    titulo: str
    descricao: Optional[str] = None
    conteudo: Optional[str] = None
    icone: Optional[str] = None  # nome do ícone (ex: 'check', 'warning', 'info')
    campos: Optional[List[ModalField]] = None  # para modais de formulário
    botoes: List[ModalButton]
    config: ModalConfig = ModalConfig()
    dados_adicionais: Optional[Dict[str, Any]] = None


class ModalResponse(BaseModel):
    """Resposta padrão de um modal"""
    sucesso: bool
    mensagem: str
    modal: Optional[Modal] = None
    dados: Optional[Dict[str, Any]] = None
    erro: Optional[str] = None


class ModalConfirmacao(Modal):
    """Modal de confirmação pré-configurado"""
    def __init__(self, titulo: str, descricao: str, **kwargs):
        botoes = [
            ModalButton(id="cancelar", label="Cancelar", tipo="default", acao="cancelar"),
            ModalButton(id="confirmar", label="Confirmar", tipo="primary", acao="confirmar"),
        ]
        super().__init__(
            id=kwargs.get("id", "modal_confirmacao"),
            tipo=ModalType.CONFIRMACAO,
            titulo=titulo,
            descricao=descricao,
            botoes=botoes,
            **{k: v for k, v in kwargs.items() if k not in ["id", "tipo", "titulo", "descricao", "botoes"]}
        )


class ModalFormulario(Modal):
    """Modal de formulário pré-configurado"""
    def __init__(self, titulo: str, campos: List[ModalField], **kwargs):
        botoes = [
            ModalButton(id="cancelar", label="Cancelar", tipo="default", acao="cancelar"),
            ModalButton(id="enviar", label="Enviar", tipo="primary", acao="enviar"),
        ]
        super().__init__(
            id=kwargs.get("id", "modal_formulario"),
            tipo=ModalType.FORMULARIO,
            titulo=titulo,
            campos=campos,
            botoes=botoes,
            **{k: v for k, v in kwargs.items() if k not in ["id", "tipo", "titulo", "campos", "botoes"]}
        )


class ModalAlerta(Modal):
    """Modal de alerta pré-configurado"""
    def __init__(self, titulo: str, descricao: str, tipo_alerta: str = "warning", **kwargs):
        icone_map = {
            "warning": "warning",
            "error": "x-circle",
            "success": "check-circle",
            "info": "info"
        }
        botoes = [
            ModalButton(id="fechar", label="Fechar", tipo="primary", acao="fechar"),
        ]
        super().__init__(
            id=kwargs.get("id", f"modal_alerta_{tipo_alerta}"),
            tipo=ModalType.ALERTA,
            titulo=titulo,
            descricao=descricao,
            icone=icone_map.get(tipo_alerta, "info"),
            botoes=botoes,
            **{k: v for k, v in kwargs.items() if k not in ["id", "tipo", "titulo", "descricao", "botoes", "icone"]}
        )


class ModalSucesso(Modal):
    """Modal de sucesso pré-configurado"""
    def __init__(self, titulo: str = "Sucesso!", descricao: str = "", **kwargs):
        botoes = [
            ModalButton(id="fechar", label="Fechar", tipo="success", acao="fechar"),
        ]
        super().__init__(
            id=kwargs.get("id", "modal_sucesso"),
            tipo=ModalType.SUCESSO,
            titulo=titulo,
            descricao=descricao,
            icone="check-circle",
            botoes=botoes,
            **{k: v for k, v in kwargs.items() if k not in ["id", "tipo", "titulo", "descricao", "botoes", "icone"]}
        )


class ModalErro(Modal):
    """Modal de erro pré-configurado"""
    def __init__(self, titulo: str = "Erro!", descricao: str = "", **kwargs):
        botoes = [
            ModalButton(id="fechar", label="Fechar", tipo="danger", acao="fechar"),
        ]
        super().__init__(
            id=kwargs.get("id", "modal_erro"),
            tipo=ModalType.ERRO,
            titulo=titulo,
            descricao=descricao,
            icone="x-circle",
            botoes=botoes,
            **{k: v for k, v in kwargs.items() if k not in ["id", "tipo", "titulo", "descricao", "botoes", "icone"]}
        )


# Funções auxiliares para criar modais comuns

def criar_modal_confirmacao(titulo: str, descricao: str, id_modal: str = "modal_confirmacao") -> ModalConfirmacao:
    """Cria um modal de confirmação padrão"""
    return ModalConfirmacao(id=id_modal, titulo=titulo, descricao=descricao)


def criar_modal_formulario(titulo: str, campos: List[ModalField], id_modal: str = "modal_formulario") -> ModalFormulario:
    """Cria um modal de formulário padrão"""
    return ModalFormulario(id=id_modal, titulo=titulo, campos=campos)


def criar_modal_sucesso(mensagem: str = "Operação realizada com sucesso!", id_modal: str = "modal_sucesso") -> ModalSucesso:
    """Cria um modal de sucesso padrão"""
    return ModalSucesso(id=id_modal, titulo="Sucesso!", descricao=mensagem)


def criar_modal_erro(mensagem: str = "Ocorreu um erro!", id_modal: str = "modal_erro") -> ModalErro:
    """Cria um modal de erro padrão"""
    return ModalErro(id=id_modal, titulo="Erro!", descricao=mensagem)


def criar_resposta_modal(sucesso: bool, mensagem: str, modal: Optional[Modal] = None, dados: Optional[Dict[str, Any]] = None) -> ModalResponse:
    """Cria uma resposta padrão com modal"""
    return ModalResponse(
        sucesso=sucesso,
        mensagem=mensagem,
        modal=modal,
        dados=dados,
        erro=None if sucesso else mensagem
    )
