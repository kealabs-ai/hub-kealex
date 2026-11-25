# Guia de Uso - Modal Padrão Compartilhado

## Visão Geral

O arquivo `shared_modal.py` fornece componentes reutilizáveis de modal para todos os serviços. Ele padroniza a forma como modais são criados e retornados nas respostas da API.

## Instalação

1. Coloque o arquivo `shared_modal.py` na raiz do projeto (onde está o `app/main.py`)
2. Importe no seu serviço:

```python
from shared_modal import (
    Modal, ModalResponse, ModalButton, ModalField,
    criar_modal_confirmacao, criar_modal_sucesso, criar_modal_erro,
    criar_resposta_modal
)
```

## Tipos de Modal Disponíveis

### 1. Modal de Sucesso
```python
from shared_modal import criar_modal_sucesso, criar_resposta_modal

@app.post("/criar-item")
def criar_item(body: dict, db: Session = Depends(get_db)):
    try:
        # ... lógica de criação ...
        modal = criar_modal_sucesso("Item criado com sucesso!")
        return criar_resposta_modal(True, "Item criado", modal, {"id": item.id})
    except Exception as e:
        modal = criar_modal_erro(f"Erro: {str(e)}")
        return criar_resposta_modal(False, "Erro ao criar", modal)
```

### 2. Modal de Erro
```python
from shared_modal import criar_modal_erro, criar_resposta_modal

@app.post("/deletar-item")
def deletar_item(body: dict):
    if not body.get("id"):
        modal = criar_modal_erro("ID é obrigatório")
        return criar_resposta_modal(False, "Validação falhou", modal)
```

### 3. Modal de Confirmação
```python
from shared_modal import criar_modal_confirmacao, criar_resposta_modal

@app.get("/confirmar-acao")
def confirmar_acao():
    modal = criar_modal_confirmacao(
        titulo="Confirmar Ação",
        descricao="Tem certeza que deseja continuar?"
    )
    return criar_resposta_modal(True, "Confirmação necessária", modal)
```

### 4. Modal de Formulário
```python
from shared_modal import criar_modal_formulario, ModalField, criar_resposta_modal

@app.get("/formulario-novo-cliente")
def formulario_novo_cliente():
    campos = [
        ModalField(
            id="nome",
            label="Nome",
            tipo="text",
            placeholder="Digite o nome",
            obrigatorio=True
        ),
        ModalField(
            id="email",
            label="Email",
            tipo="email",
            placeholder="seu@email.com",
            obrigatorio=True
        ),
        ModalField(
            id="telefone",
            label="Telefone",
            tipo="text",
            placeholder="(11) 99999-9999"
        ),
    ]
    modal = criar_modal_formulario("Novo Cliente", campos)
    return criar_resposta_modal(True, "Preencha o formulário", modal)
```

## Estrutura de Resposta

Todas as respostas com modal seguem este padrão:

```json
{
  "sucesso": true,
  "mensagem": "Operação realizada com sucesso",
  "modal": {
    "id": "modal_sucesso",
    "tipo": "sucesso",
    "titulo": "Sucesso!",
    "descricao": "Operação realizada com sucesso",
    "icone": "check-circle",
    "botoes": [
      {
        "id": "fechar",
        "label": "Fechar",
        "tipo": "success",
        "acao": "fechar",
        "disabled": false
      }
    ],
    "config": {
      "tamanho": "md",
      "centralizacao": true,
      "fechar_ao_clicar_fora": false,
      "mostrar_header": true,
      "mostrar_footer": true,
      "animacao": "fade"
    }
  },
  "dados": {
    "id": "123",
    "nome": "Item criado"
  },
  "erro": null
}
```

## Exemplos Práticos por Serviço

### svc-cobrancas

```python
from shared_modal import criar_modal_sucesso, criar_modal_erro, criar_resposta_modal

@app.post("/v1/lex/cobrancas")
def criar_cobranca(body: CobrancaIn, db: Session = Depends(get_db)):
    try:
        cobranca = Cobranca(...)
        db.add(cobranca)
        db.commit()
        
        modal = criar_modal_sucesso(f"Cobrança criada: {cobranca.id}")
        return criar_resposta_modal(
            True, 
            "Cobrança criada com sucesso", 
            modal, 
            _cobranca_to_dict(cobranca)
        )
    except Exception as e:
        modal = criar_modal_erro(f"Erro: {str(e)}")
        return criar_resposta_modal(False, "Erro ao criar cobrança", modal)
```

### svc-processos

```python
from shared_modal import criar_modal_sucesso, criar_resposta_modal

@app.post("/v1/lex/processos")
def criar_processo(body: ProcessoIn, db: Session = Depends(get_db)):
    try:
        processo = Processo(...)
        db.add(processo)
        db.commit()
        
        modal = criar_modal_sucesso("Processo criado com sucesso!")
        return criar_resposta_modal(
            True,
            "Processo criado",
            modal,
            _processo_to_dict(processo)
        )
    except Exception as e:
        modal = criar_modal_erro(f"Erro: {str(e)}")
        return criar_resposta_modal(False, "Erro ao criar processo", modal)
```

### svc-clientes

```python
from shared_modal import criar_modal_confirmacao, criar_resposta_modal

@app.post("/v1/lex/clientes/deletar")
def deletar_cliente(body: dict):
    cliente_id = body.get("id")
    
    # Primeiro retorna modal de confirmação
    modal = criar_modal_confirmacao(
        titulo="Deletar Cliente",
        descricao=f"Tem certeza que deseja deletar o cliente {cliente_id}?"
    )
    return criar_resposta_modal(True, "Confirmação necessária", modal)
```

## Customização

### Criar Modal Customizado

```python
from shared_modal import Modal, ModalButton, ModalConfig, ModalType

modal_custom = Modal(
    id="modal_custom",
    tipo=ModalType.INFORMACAO,
    titulo="Informação Importante",
    descricao="Esta é uma informação customizada",
    icone="info",
    botoes=[
        ModalButton(id="ok", label="OK", tipo="primary", acao="fechar"),
        ModalButton(id="cancelar", label="Cancelar", tipo="default", acao="cancelar"),
    ],
    config=ModalConfig(
        tamanho="lg",
        centralizacao=True,
        fechar_ao_clicar_fora=False,
        animacao="slide"
    )
)

return criar_resposta_modal(True, "Informação", modal_custom)
```

### Adicionar Dados Adicionais

```python
modal = criar_modal_sucesso("Operação concluída!")
return criar_resposta_modal(
    True,
    "Sucesso",
    modal,
    dados={
        "id": "123",
        "nome": "Item",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {"chave": "valor"}
    }
)
```

## Integração no Frontend

O frontend pode processar a resposta assim:

```javascript
// Exemplo em React/Vue
const response = await fetch('/api/endpoint', { method: 'POST' });
const data = await response.json();

if (data.modal) {
  // Mostrar modal
  showModal({
    title: data.modal.titulo,
    description: data.modal.descricao,
    icon: data.modal.icone,
    buttons: data.modal.botoes,
    config: data.modal.config
  });
}

if (data.dados) {
  // Processar dados retornados
  console.log(data.dados);
}
```

## Checklist de Implementação

- [ ] Copiar `shared_modal.py` para a raiz do projeto
- [ ] Importar componentes no serviço
- [ ] Atualizar endpoints para retornar `ModalResponse`
- [ ] Testar modais de sucesso e erro
- [ ] Testar modais de confirmação
- [ ] Testar modais de formulário
- [ ] Validar estrutura de resposta no frontend
- [ ] Documentar endpoints customizados

## Notas Importantes

1. O modal é **opcional** - se não importar, o serviço continua funcionando normalmente
2. Use `try/except` para garantir que erros retornem modais apropriados
3. Sempre inclua dados relevantes no campo `dados` da resposta
4. Customize o `tamanho` do modal conforme necessário (sm, md, lg, xl)
5. Use `fechar_ao_clicar_fora: False` para modais críticos (confirmação, erro)
