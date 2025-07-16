# Vitruvius 🏗️

**AI-Powered SaaS Platform for BIM Project Coordination and Conflict Resolution**

[![License: BSL 1.1](https://img.shields.io/badge/License-BSL%201.1-blue.svg)](https://mariadb.com/bsl11/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![React 18+](https://img.shields.io/badge/react-18.0+-61DAFB.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)

## 🚀 About the Project

Vitruvius is a revolutionary platform for the AEC (Architecture, Engineering, and Construction) industry that leverages **Artificial Intelligence** to automate BIM project coordination. Our solution not only **detects conflicts** between disciplines but also **prescribes viable solutions** with quantified impact on cost and schedule.

### 🎯 Problems Solved

- **Coordination Inefficiency**: Dramatically reduces time spent on manual conflict identification
- **Costly Rework**: Eliminates unnecessary revision cycles through predictive analysis
- **Lack of Standardization**: Provides solutions based on industry best practices
- **Data-Driven Decisions**: Delivers quantitative metrics for informed decision-making

### 🔬 Differentiated Technology

- **Prescriptive AI**: Beyond detection, our AI suggests specific solutions for each conflict
- **Impact Analysis**: Quantifies costs and timeline impact of each proposed solution
- **IFC Processing**: Compatible with international BIM standards
- **3D Visualization**: Intuitive interface for visual conflict analysis

## 🏗️ Architecture

### Technology Stack

#### Backend
- **FastAPI** - High-performance REST API
- **Python 3.11** - Core language
- **SQLAlchemy** - Database ORM
- **IfcOpenShell** - IFC file processing
- **Celery** - Asynchronous processing
- **Redis** - Cache and message broker

#### Frontend
- **React 18** - Modern user interface
- **IFC.js** - 3D BIM model visualization
- **Three.js** - Advanced 3D rendering

#### Infrastructure
- **PostgreSQL** - Primary database
- **Docker** - Containerization
- **GitHub Actions** - CI/CD
- **AWS** - Cloud deployment

## 🚀 Getting Started

### Prerequisites

- [Docker](https://www.docker.com/get-started) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+)
- [Git](https://git-scm.com/)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tjsasakifln/Vitruvius.git
   cd Vitruvius
   ```

2. **Start the development environment:**
   ```bash
   docker-compose up --build
   ```

3. **Access the application:**
   - 🌐 **Frontend:** Port 3000
   - 🔧 **API Backend:** Port 8000
   - 📊 **API Documentation:** /docs endpoint
   - 🗄️ **PostgreSQL:** Port 5432
   - 🔄 **Redis:** Port 6379

## 📋 Features

### 🔍 Conflict Detection
- Automatic analysis of IFC models
- Identification of element collisions
- Clearance and tolerance verification
- Multi-disciplinary interference analysis

### 🤖 Prescriptive AI
- Specific solution suggestions for each conflict
- Cost and schedule impact quantification
- Automatic prioritization based on criticality
- Project-personalized recommendations

### 📊 Analytics Dashboard
- Project metrics visualization
- Conflict reports by discipline
- Coordination progress tracking
- Applied solutions history

### 🎨 3D Visualization
- Real-time IFC model rendering
- Conflict highlighting
- Intuitive 3D navigation
- Visual solution comparison

## 🏃‍♂️ Quick Usage

### Create Project
```bash
curl -X POST "/api/projects" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project", "description": "Project description"}'
```

### Upload IFC Model
```bash
curl -X POST "/api/projects/1/upload-ifc" \
  -F "file=@model.ifc"
```

### Query Conflicts
```bash
curl -X GET "/api/projects/1/conflicts"
```

## 🔧 Development

### Project Structure
```
Vitruvius/
├── backend/                 # FastAPI API
│   ├── app/
│   │   ├── api/v1/         # API endpoints
│   │   ├── db/models/      # Data models
│   │   ├── services/       # Business logic
│   │   └── tasks/          # Celery tasks
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # React app
│   ├── src/
│   │   ├── components/     # React components
│   │   └── services/       # API services
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml      # Orchestration
└── .github/workflows/      # CI/CD
```

### Development Commands

**Backend:**
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run tests
pytest backend/tests/

# Run local server
uvicorn backend.app.main:app --reload
```

**Frontend:**
```bash
# Install dependencies
npm install --prefix frontend

# Run in development mode
npm start --prefix frontend

# Run tests
npm test --prefix frontend
```

## 📚 API Documentation

Complete API documentation is available at:
- **Swagger UI:** /docs endpoint on the API server
- **ReDoc:** /redoc endpoint on the API server

### Main Endpoints

- `GET /api/projects` - List projects
- `POST /api/projects` - Create project
- `POST /api/projects/{id}/upload-ifc` - Upload IFC model
- `GET /api/projects/{id}/conflicts` - Get conflicts
- `POST /api/projects/{id}/analyze` - Execute AI analysis

## 🤝 Contributing

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the Business Source License 1.1 (BSL 1.1).

**⚠️ COMMERCIAL USE NOTICE**: Commercial use of this software is strictly prohibited without explicit written authorization. For commercial licensing, please contact Tiago Sasaki at tiago@confenge.com.br.

## 🏢 Roadmap

- [ ] **v1.0** - MVP with basic conflict detection
- [ ] **v1.1** - Prescriptive AI with solution suggestions
- [ ] **v1.2** - Revit and ArchiCAD integration
- [ ] **v1.3** - Advanced cost analysis
- [ ] **v2.0** - Multi-tenancy and enterprise scalability

## 📞 Contact

For support or business inquiries:
- 📧 Email: tiago@confenge.com.br
- 🐙 GitHub: https://github.com/tjsasakifln/Vitruvius

---

<div align="center">
  <p>Built with ❤️ to revolutionize the AEC industry</p>
  <p>🏗️ <strong>Vitruvius</strong> - Where AI meets Engineering</p>
</div>
