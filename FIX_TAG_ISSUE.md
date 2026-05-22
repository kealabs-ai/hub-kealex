# Problema: Tag Incorreta nas Imagens Docker

## Problema Identificado

O pipeline estava falhando no stage "Test Images" com o seguinte erro:

```
docker run --rm -e DATABASE_URL=sqlite:///./test.db -e SECRET_KEY=test-key kealex/svc-auth:32 python -c import main; print('svc-auth: OK')
Unable to find image 'kealex/svc-auth:32' locally
docker: Error response from daemon: pull access denied for kealex/svc-auth, repository does not exist or may require 'docker login'.
```

## Causa Raiz

O problema ocorreu porque:

1. **Build das Imagens**: No stage "Build Images", as imagens são construídas com duas tags:
   ```groovy
   docker build -t ${IMAGE_PREFIX}/${svc}:${TAG} ./${svc}
   docker tag ${IMAGE_PREFIX}/${svc}:${TAG} ${IMAGE_PREFIX}/${svc}:latest
   ```
   - `${TAG}` = BUILD_NUMBER (ex: 32)
   - `latest` = tag padrão

2. **Pulo do Build**: Como as imagens já existiam, o build foi pulado:
   ```
   Imagem svc-auth já existe, pulando build...
   ```

3. **Teste com Tag Errada**: O teste tentou usar `${TAG}` (32), mas a imagem existente tinha apenas a tag `latest`:
   ```groovy
   docker run --rm ${IMAGE_PREFIX}/svc-auth:${TAG} ...
   ```

## Solução Implementada

Alterado os stages de teste para usar a tag `latest` em vez de `${TAG}`:

### Stage: Test Images

**Antes:**
```groovy
sh """
    docker run --rm \
      -e DATABASE_URL=sqlite:///./test.db \
      -e SECRET_KEY=test-key \
      ${IMAGE_PREFIX}/svc-auth:${TAG} \
      python -c "import main; print('svc-auth: OK')"
"""
```

**Depois:**
```groovy
sh """
    docker run --rm \
      -e DATABASE_URL=sqlite:///./test.db \
      -e SECRET_KEY=test-key \
      ${IMAGE_PREFIX}/svc-auth:latest \
      python -c "import main; print('svc-auth: OK')"
"""
```

### Stage: Test Nginx Config

**Antes:**
```groovy
sh """
    echo "Testando sintaxe da configuração do nginx..."
    docker run --rm ${IMAGE_PREFIX}/api-gateway:${TAG} nginx -t
"""
```

**Depois:**
```groovy
sh """
    echo "Testando sintaxe da configuração do nginx..."
    docker run --rm ${IMAGE_PREFIX}/api-gateway:latest nginx -t
"""
```

## Por Que Isso Funciona

1. **Consistência**: A tag `latest` sempre existe, seja a imagem nova ou reutilizada
2. **Simplicidade**: Não precisa verificar se a tag específica existe
3. **Compatibilidade**: Funciona tanto quando o build é executado quanto quando é pulado

## Alternativa (Não Implementada)

Outra solução seria sempre fazer o build, mesmo que a imagem exista:

```groovy
services.each { svc ->
    echo "Building ${svc}..."
    sh """
        docker build -t ${IMAGE_PREFIX}/${svc}:${TAG} ./${svc}
        docker tag ${IMAGE_PREFIX}/${svc}:${TAG} ${IMAGE_PREFIX}/${svc}:latest
    """
}
```

**Desvantagens:**
- Mais lento (rebuild desnecessário)
- Usa mais recursos
- Aumenta tempo do pipeline

## Lições Aprendidas

1. **Sempre use tags consistentes** nos testes
2. **Tag `latest` é mais confiável** para testes locais
3. **Tag com BUILD_NUMBER** deve ser usada apenas para:
   - Push para registry
   - Deploy em produção
   - Rastreabilidade de versões

## Verificação

Para verificar se as imagens têm as tags corretas:

```bash
docker images | grep kealex
```

Saída esperada:
```
kealex/api-gateway       26        53796694969e   35 minutes ago   73.6MB
kealex/api-gateway       latest    53796694969e   35 minutes ago   73.6MB
kealex/svc-auth          26        e37d33530014   37 minutes ago   328MB
kealex/svc-auth          latest    e37d33530014   37 minutes ago   328MB
```

Observe que cada imagem tem duas tags apontando para o mesmo IMAGE ID.

## Próximos Passos

O pipeline agora deve:

1. ✅ Passar no stage "Test Images"
2. ✅ Passar no stage "Test Nginx Config"
3. ✅ Continuar para os stages de deploy
4. ✅ Testar o nginx em execução
5. ✅ Validar a API completa

## Documentação Relacionada

- [JENKINS_NGINX.md](JENKINS_NGINX.md) - Documentação completa do nginx no Jenkins
- [TROUBLESHOOTING_JENKINS.md](TROUBLESHOOTING_JENKINS.md) - Guia de troubleshooting
- [README.md](README.md) - Documentação principal do projeto
