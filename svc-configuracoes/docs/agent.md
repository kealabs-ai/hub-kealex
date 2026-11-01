# Instruções do agente — svc-configuracoes

- Consulte `knowledge.md` e `SERVICE.md` antes de modificar o serviço.
- Investigue somente componentes envolvidos e mantenha a separação entre rotas, schemas, casos de uso, dependências e persistência em `app/`.
- Preserve métodos, caminhos, campos de entrada/saída, isolamento por tenant e permissões atuais.
- Nunca exponha chaves de IA, tokens JWT, credenciais do Drive ou senhas do banco; mantenha as chaves pessoais criptografadas e mascaradas.
- Não altere tabelas compartilhadas sem migração versionada e análise de compatibilidade.
- Mantenha `main.py` na raiz como ponto de entrada `uvicorn main:app`.
- Adicione testes relevantes e atualize a documentação quando mudar contratos, configuração ou comportamento.
