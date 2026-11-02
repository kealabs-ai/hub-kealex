# Logs do svc-activities

O middleware registra método, caminho e status HTTP. Não armazena corpos de requisição/resposta nem query strings. O conteúdo de atividades pode conter dados pessoais ou confidenciais; não adicione esses campos a logs. Exceções são registradas pelo tipo, sem a mensagem que pode conter valores enviados pelo cliente.
