# Vitruvius - Security Configuration

## 🔐 Required GitHub Secrets

Para configurar adequadamente o pipeline de CI/CD e a segurança da aplicação, você deve adicionar os seguintes secrets no GitHub:

### AWS Secrets
- `AWS_ACCESS_KEY_ID` - Chave de acesso AWS para deployment
- `AWS_SECRET_ACCESS_KEY` - Chave secreta AWS para deployment

### Application Secrets
- `SECRET_KEY` - Chave secreta para JWT (mínimo 32 caracteres aleatórios)
- `DATABASE_URL` - URL da conexão com o banco de dados de produção
- `CELERY_BROKER_URL` - URL do broker Redis para Celery
- `CELERY_RESULT_BACKEND` - URL do backend Redis para resultados Celery

## 🛡️ Gerando uma SECRET_KEY Segura

Use um dos métodos abaixo para gerar uma chave secreta segura:

### Python
```python
import secrets
print(secrets.token_urlsafe(32))
```

### OpenSSL
```bash
openssl rand -base64 32
```

### Online (use com cuidado)
Apenas para desenvolvimento: https://keygen.io/

## 📋 Como Configurar os Secrets no GitHub

1. Vá para o repositório no GitHub
2. Clique em **Settings** > **Secrets and variables** > **Actions**
3. Clique em **New repository secret**
4. Adicione cada secret listado acima

## 🔒 Valores de Exemplo (NÃO USE EM PRODUÇÃO)

```bash
# Exemplo de valores para desenvolvimento local (.env)
SECRET_KEY=supersecretkey123456789abcdefghijklmnopqrstuvwxyz
DATABASE_URL=postgresql://user:password@localhost:5432/vitruvius_db
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## ⚠️ Importante

1. **NUNCA** comite arquivos `.env` com valores reais
2. **SEMPRE** use valores diferentes para desenvolvimento e produção
3. **ROTACIONE** as chaves regularmente
4. **MONITORE** os logs por tentativas de acesso não autorizadas

## 🔄 Rotação de Chaves

Para rotacionar a SECRET_KEY:

1. Gere uma nova chave segura
2. Atualize o secret no GitHub
3. Faça o redeploy da aplicação
4. Todos os tokens JWT existentes serão invalidados

## 🚨 Em Caso de Comprometimento

Se suspeitar que uma chave foi comprometida:

1. **Imediatamente** rotacione todas as chaves
2. Revise os logs de acesso
3. Notifique a equipe de segurança
4. Considere implementar autenticação multi-fator