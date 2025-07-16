# Vitruvius 🏗️

**Plataforma SaaS de Inteligência Artificial para Compatibilização de Projetos BIM**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![React 18+](https://img.shields.io/badge/react-18.0+-61DAFB.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)

## 🚀 Sobre o Projeto

Vitruvius é uma plataforma revolucionária para a indústria AEC (Arquitetura, Engenharia e Construção) no Brasil que utiliza **Inteligência Artificial** para automatizar a compatibilização de projetos BIM. Nossa solução não apenas **detecta conflitos** entre disciplinas, mas também **prescreve soluções viáveis** com quantificação de impacto em custo e cronograma.

### 🎯 Problema Resolvido

- **Ineficiência na compatibilização**: Reduz drasticamente o tempo gasto na identificação manual de conflitos
- **Retrabalho custoso**: Elimina ciclos de revisão desnecessários através de análise preditiva
- **Falta de padronização**: Oferece soluções baseadas em melhores práticas da indústria
- **Decisões sem dados**: Fornece métricas quantitativas para tomada de decisão

### 🔬 Tecnologia Diferenciada

- **IA Prescritiva**: Além de detectar, nossa IA sugere soluções específicas para cada conflito
- **Análise de Impacto**: Quantifica custos e prazos de cada solução proposta
- **Processamento IFC**: Compatível com padrões internacionais de BIM
- **Visualização 3D**: Interface intuitiva para análise visual de conflitos

## 🏗️ Arquitetura

### Stack Tecnológico

#### Backend
- **FastAPI** - API REST de alta performance
- **Python 3.11** - Linguagem principal
- **SQLAlchemy** - ORM para banco de dados
- **IfcOpenShell** - Processamento de arquivos IFC
- **Celery** - Processamento assíncrono
- **Redis** - Cache e message broker

#### Frontend
- **React 18** - Interface de usuário moderna
- **IFC.js** - Visualização 3D de modelos BIM
- **Three.js** - Renderização 3D avançada

#### Infraestrutura
- **PostgreSQL** - Banco de dados principal
- **Docker** - Containerização
- **GitHub Actions** - CI/CD
- **AWS** - Deploy em nuvem

## 🚀 Começando

### Pré-requisitos

- [Docker](https://www.docker.com/get-started) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)
- [Git](https://git-scm.com/)

### Instalação

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/tjsasakifln/Vitruvius.git
   cd Vitruvius
   ```

2. **Inicie o ambiente de desenvolvimento:**
   ```bash
   docker-compose up --build
   ```

3. **Acesse a aplicação:**
   - 🌐 **Frontend:** http://localhost:3000
   - 🔧 **API Backend:** http://localhost:8000
   - 📊 **Documentação API:** http://localhost:8000/docs
   - 🗄️ **PostgreSQL:** localhost:5432
   - 🔄 **Redis:** localhost:6379

## 📋 Funcionalidades

### 🔍 Detecção de Conflitos
- Análise automática de modelos IFC
- Identificação de colisões entre elementos
- Verificação de clearances e tolerâncias
- Análise de interferências multidisciplinares

### 🤖 IA Prescritiva
- Sugestão de soluções específicas para cada conflito
- Quantificação de impacto em custo e cronograma
- Priorização automática baseada em criticidade
- Recomendações personalizadas por projeto

### 📊 Dashboard Analítico
- Visualização de métricas de projeto
- Relatórios de conflitos por disciplina
- Tracking de progresso de compatibilização
- Histórico de soluções aplicadas

### 🎨 Visualização 3D
- Renderização de modelos IFC em tempo real
- Highlight de conflitos detectados
- Navegação intuitiva em 3D
- Comparação visual de soluções

## 🏃‍♂️ Uso Rápido

### Criar Projeto
```bash
curl -X POST "http://localhost:8000/api/projects" \
  -H "Content-Type: application/json" \
  -d '{"name": "Meu Projeto", "description": "Descrição do projeto"}'
```

### Upload de Modelo IFC
```bash
curl -X POST "http://localhost:8000/api/projects/1/upload-ifc" \
  -F "file=@modelo.ifc"
```

### Consultar Conflitos
```bash
curl -X GET "http://localhost:8000/api/projects/1/conflicts"
```

## 🔧 Desenvolvimento

### Estrutura do Projeto
```
Vitruvius/
├── backend/                 # API FastAPI
│   ├── app/
│   │   ├── api/v1/         # Endpoints da API
│   │   ├── db/models/      # Modelos de dados
│   │   ├── services/       # Lógica de negócio
│   │   └── tasks/          # Tarefas Celery
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # App React
│   ├── src/
│   │   ├── components/     # Componentes React
│   │   └── services/       # Serviços de API
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml      # Orquestração
└── .github/workflows/      # CI/CD
```

### Comandos de Desenvolvimento

**Backend:**
```bash
# Instalar dependências
pip install -r backend/requirements.txt

# Executar testes
pytest backend/tests/

# Executar servidor local
uvicorn backend.app.main:app --reload
```

**Frontend:**
```bash
# Instalar dependências
npm install --prefix frontend

# Executar em modo desenvolvimento
npm start --prefix frontend

# Executar testes
npm test --prefix frontend
```

## 📚 API Documentation

A documentação completa da API está disponível em:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Principais Endpoints

- `GET /api/projects` - Listar projetos
- `POST /api/projects` - Criar projeto
- `POST /api/projects/{id}/upload-ifc` - Upload modelo IFC
- `GET /api/projects/{id}/conflicts` - Obter conflitos
- `POST /api/projects/{id}/analyze` - Executar análise IA

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 🏢 Roadmap

- [ ] **v1.0** - MVP com detecção básica de conflitos
- [ ] **v1.1** - IA prescritiva com sugestões de soluções
- [ ] **v1.2** - Integração com Revit e ArchiCAD
- [ ] **v1.3** - Análise de custos avançada
- [ ] **v2.0** - Multi-tenancy e escalabilidade enterprise

## 📞 Contato

Para suporte ou questões comerciais:
- 📧 Email: contato@vitruvius.com.br
- 💬 Website: https://vitruvius.com.br
- 🐙 GitHub: https://github.com/tjsasakifln/Vitruvius

---

<div align="center">
  <p>Desenvolvido com ❤️ para revolucionar a indústria AEC brasileira</p>
  <p>🏗️ <strong>Vitruvius</strong> - Onde a IA encontra a Engenharia</p>
</div>
