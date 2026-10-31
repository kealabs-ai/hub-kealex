# Instruções para agentes

Leia [`agent.md`](agent.md) e [`knowledge.md`](knowledge.md) antes de alterar este microserviço. A especificação de componentes e responsabilidades está em [`SERVICE.md`](SERVICE.md).

Preserve os contratos HTTP e os dados atuais. Separe responsabilidades nas camadas existentes em `app/`; evite refatorações fora do escopo e não altere schema sem migração versionada. Execute os testes pertinentes em `tests/unit/` e `tests/integration/` quando as dependências do serviço estiverem disponíveis.




