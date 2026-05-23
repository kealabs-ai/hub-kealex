# Configuração de Variáveis de Ambiente - Jenkins VPS

## Variáveis Necessárias

Configure estas variáveis de ambiente no Jenkins da VPS:

### 1. SECRET_KEY
Chave secreta para JWT e criptografia

```bash
SECRET_KEY=sua_chave_secreta_aqui_minimo_32_caracteres
```

**Gerar uma chave segura:**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. DATABASE_URL
URL de conexão com o banco de dados MySQL

```bash
DATABASE_URL=mysql+pymysql://usuario:senha@host:porta/database
```

**Exemplo:**
```bash
DATABASE_URL=mysql+pymysql://u549746795_kealex:Sally2026%40%21%40@srv1078.hstgr.io:3306/u549746795_kealex
```

## Como Configurar no Jenkins

### Opção 1: Via Interface Web (Recomendado)

1. Acesse Jenkins: `http://seu-servidor:8080`
2. Vá em: **Manage Jenkins** → **System**
3. Role até **Global properties**
4. Marque: **Environment variables**
5. Clique em **Add** e adicione:
   - Name: `SECRET_KEY`
   - Value: `sua_chave_secreta`
6. Clique em **Add** novamente:
   - Name: `DATABASE_URL`
   - Value: `mysql+pymysql://...`
7. Clique em **Save**

### Opção 2: Via Arquivo de Configuração

Edite o arquivo de configuração do Jenkins:

```bash
# Acesse o container Jenkins
docker exec -it jenkins bash

# Edite o arquivo de ambiente
vi /var/jenkins_home/jenkins.env
```

Adicione as variáveis:
```bash
SECRET_KEY=sua_chave_secreta_aqui
DATABASE_URL=mysql+pymysql://usuario:senha@host:porta/database
```

Reinicie o Jenkins:
```bash
docker restart jenkins
```

### Opção 3: Via Docker Compose (Melhor para VPS)

Se o Jenkins está rodando via Docker Compose, edite o `docker-compose.yml`:

```yaml
services:
  jenkins:
    image: jenkins/jenkins:lts
    environment:
      - SECRET_KEY=sua_chave_secreta_aqui
      - DATABASE_URL=mysql+pymysql://usuario:senha@host:porta/database
    ports:
      - "8080:8080"
    volumes:
      - jenkins_home:/var/jenkins_home
```

Depois reinicie:
```bash
docker compose restart jenkins
```

### Opção 4: Via Variáveis de Sistema (Linux)

Adicione ao perfil do usuário Jenkins:

```bash
# Edite o arquivo de ambiente
sudo vi /etc/environment
```

Adicione:
```bash
SECRET_KEY="sua_chave_secreta_aqui"
DATABASE_URL="mysql+pymysql://usuario:senha@host:porta/database"
```

Recarregue:
```bash
source /etc/environment
sudo systemctl restart jenkins
```

## Verificar Configuração

Execute no Jenkins (Pipeline Script):

```groovy
pipeline {
    agent any
    stages {
        stage('Test Env') {
            steps {
                sh '''
                    echo "SECRET_KEY: ${SECRET_KEY:0:10}..."
                    echo "DATABASE_URL: ${DATABASE_URL:0:30}..."
                '''
            }
        }
    }
}
```

## Segurança

⚠️ **IMPORTANTE:**
- Nunca commite as variáveis no Git
- Use valores diferentes para dev/prod
- Rotacione a SECRET_KEY periodicamente
- Use senhas fortes no DATABASE_URL

## Troubleshooting

### Variável não encontrada
```bash
# Verifique se a variável está definida
docker exec jenkins env | grep SECRET_KEY
docker exec jenkins env | grep DATABASE_URL
```

### Permissões
```bash
# Garanta que o usuário Jenkins tem acesso
sudo chown -R jenkins:jenkins /var/jenkins_home
```

### Caracteres especiais na senha
Se a senha do banco tem caracteres especiais, encode-os:
- `@` → `%40`
- `!` → `%21`
- `#` → `%23`
- `$` → `%24`
- `%` → `%25`

**Exemplo:**
```
Senha original: Sally2026@!@
Senha encoded:  Sally2026%40%21%40
```

## Valores de Exemplo (NÃO USE EM PRODUÇÃO)

```bash
# Desenvolvimento
SECRET_KEY=dev_secret_key_for_testing_only_32chars
DATABASE_URL=mysql+pymysql://root:root@localhost:3306/kealex_dev

# Produção (use valores reais)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
DATABASE_URL=mysql+pymysql://u549746795_kealex:SuaSenhaSegura@srv1078.hstgr.io:3306/u549746795_kealex
```
