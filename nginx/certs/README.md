# Certificados SSL

Para usar HTTPS, coloque os certificados SSL neste diretório:

## Arquivos necessários:
- `fullchain.pem` - Certificado completo (certificado + cadeia)
- `privkey.pem` - Chave privada

## Como obter certificados:

### 1. Let's Encrypt (Gratuito)
```bash
# Instalar certbot
sudo apt-get install certbot

# Gerar certificado
sudo certbot certonly --standalone -d kealex.com.br -d www.kealex.com.br

# Copiar certificados
sudo cp /etc/letsencrypt/live/kealex.com.br/fullchain.pem ./nginx/certs/
sudo cp /etc/letsencrypt/live/kealex.com.br/privkey.pem ./nginx/certs/
```

### 2. Certificado auto-assinado (Desenvolvimento)
```bash
# Gerar certificado auto-assinado
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./nginx/certs/privkey.pem \
  -out ./nginx/certs/fullchain.pem \
  -subj "/C=BR/ST=SP/L=SaoPaulo/O=Kealex/CN=kealex.com.br"
```

### 3. Certificado do provedor de hospedagem
- Baixe os certificados do painel de controle
- Renomeie para `fullchain.pem` e `privkey.pem`
- Coloque neste diretório

## Permissões:
```bash
chmod 644 fullchain.pem
chmod 600 privkey.pem
```

## Teste:
Após configurar os certificados, teste com:
```bash
curl -k https://srv1023256.hstgr.cloud/health
```