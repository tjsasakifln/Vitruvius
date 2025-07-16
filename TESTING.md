# Vitruvius - Testing Strategy & Coverage

## 🎯 Testing Objectives

Este documento detalha a estratégia de testes implementada para garantir a qualidade e confiabilidade da plataforma Vitruvius.

## 📊 Cobertura de Código

### Meta de Cobertura: **80%**

A cobertura de código é monitorada automaticamente e deve atingir no mínimo 80% para aprovação em Pull Requests.

### Relatórios de Cobertura

- **HTML**: `backend/htmlcov/index.html`
- **XML**: `backend/coverage.xml`
- **Terminal**: Output direto durante execução dos testes

## 🧪 Tipos de Testes

### 1. **Testes Unitários** (`backend/tests/unit/`)

**Objetivo**: Testar funções e métodos individuais isoladamente.

#### Cobertura Principal:
- `test_rules_engine.py`: Testa o motor de regras prescritivas
  - Cálculo de custos e prazos
  - Geração de soluções para diferentes conflitos
  - Validação de lógica de negócio

#### Executar:
```bash
cd backend
pytest tests/unit/ -v
```

### 2. **Testes de Integração** (`backend/tests/integration/`)

**Objetivo**: Testar a interação entre componentes do sistema.

#### Cobertura Principal:
- `test_auth_endpoints.py`: Autenticação e autorização
- `test_project_endpoints.py`: CRUD de projetos, upload IFC, feedback

#### Executar:
```bash
cd backend
pytest tests/integration/ -v
```

### 3. **Testes End-to-End** (`e2e-tests/`)

**Objetivo**: Testar fluxos completos do usuário na aplicação.

#### Cenários Cobertos:
- **Fluxo de Autenticação**: Registro, login, logout
- **Fluxo de Projeto**: Criação, upload IFC, visualização 3D
- **Fluxo de Conflitos**: Detecção, análise, feedback
- **Fluxo de Feedback**: Seleção de soluções, feedback customizado

#### Executar:
```bash
cd e2e-tests
npm install
npx playwright install
npx playwright test
```

## 🚀 Execução dos Testes

### Desenvolvimento Local

```bash
# Testes unitários e integração
cd backend
pytest --cov=app --cov-report=html --cov-report=term-missing

# Testes E2E
cd e2e-tests
npx playwright test --headed
```

### CI/CD Pipeline

Os testes são executados automaticamente no GitHub Actions:

1. **Testes Backend**: Unitários + Integração
2. **Testes Frontend**: Jest + React Testing Library
3. **Testes E2E**: Playwright (apenas em main/master)
4. **Verificação de Cobertura**: Falhará se < 80%

## 🎯 Jornada Completa do Usuário (E2E)

### Cenário Principal Testado:

1. **Fazer login** na plataforma
2. **Criar um novo projeto** BIM
3. **Fazer upload de arquivo IFC**
4. **Aguardar processamento** assíncrono
5. **Visualizar modelo 3D** processado
6. **Clicar em issue de colisão** identificada
7. **Visualizar soluções prescritivas**
8. **Selecionar ou descrever solução**
9. **Fornecer feedback** sobre eficácia
10. **Marcar issue como resolvida**

## 📋 Fixtures e Dados de Teste

### Backend Fixtures (`backend/tests/factories.py`)

Utilizamos **Factory Boy** para criar dados de teste consistentes:

- `UserFactory`: Usuários de teste
- `ProjectFactory`: Projetos de teste
- `ConflictFactory`: Conflitos simulados
- `SolutionFactory`: Soluções prescritivas
- `SolutionFeedbackFactory`: Feedback de usuários

### E2E Fixtures (`e2e-tests/fixtures/`)

- `test-model.ifc`: Modelo IFC válido para testes
- Dados de usuário padronizados
- Cenários de conflitos pré-definidos

## 🔧 Configuração do Ambiente de Testes

### Backend

- **Banco de Dados**: SQLite em memória para velocidade
- **Autenticação**: Mock de usuários e tokens
- **Processamento**: Mock de tarefas Celery
- **Uploads**: Arquivos temporários

### Frontend

- **Servidor Local**: Iniciado automaticamente
- **Navegadores**: Chrome, Firefox, Safari, Mobile
- **Dados**: Reset entre testes

## 📊 Métricas de Qualidade

### Cobertura por Módulo:

| Módulo | Meta | Atual |
|---------|------|-------|
| `rules_engine.py` | 90% | ✅ |
| `auth.py` | 85% | ✅ |
| `project_endpoints.py` | 80% | ✅ |
| `database.py` | 75% | ✅ |
| `bim_processor.py` | 70% | ✅ |

### Tempo de Execução:

- **Testes Unitários**: < 30 segundos
- **Testes Integração**: < 2 minutos
- **Testes E2E**: < 10 minutos

## 🚫 Critérios de Falha

### Pull Request será bloqueado se:

1. **Cobertura < 80%**
2. **Testes falhando**
3. **Linting errors**
4. **Testes E2E instáveis**

## 🔄 Manutenção dos Testes

### Responsabilidades:

- **Desenvolvedores**: Criar testes para novas funcionalidades
- **Code Review**: Verificar qualidade dos testes
- **CI/CD**: Executar testes automaticamente
- **Monitoramento**: Acompanhar tendências de cobertura

### Boas Práticas:

1. **Testes devem ser independentes**
2. **Dados de teste isolados**
3. **Nomes descritivos**
4. **Cleanup automático**
5. **Mock de dependências externas**

## 📚 Comandos Úteis

```bash
# Executar todos os testes
pytest

# Executar com cobertura
pytest --cov=app --cov-report=html

# Executar testes específicos
pytest tests/unit/test_rules_engine.py::TestRulesEngine::test_specific_function

# Executar testes em paralelo
pytest -n auto

# Executar testes E2E específicos
npx playwright test tests/auth.spec.js

# Executar testes E2E em modo debug
npx playwright test --debug

# Gerar relatório de cobertura
pytest --cov=app --cov-report=html && open htmlcov/index.html
```

## 🎯 Próximos Passos

1. **Implementar testes de performance**
2. **Adicionar testes de segurança**
3. **Expandir cobertura para 90%**
4. **Implementar testes de carga**
5. **Adicionar testes de acessibilidade**

---

**Lembre-se**: Testes são investimento em qualidade e confiança. Cada teste escrito hoje economiza horas de debug amanhã! 🚀