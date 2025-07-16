# Vitruvius - Testing Strategy & Coverage

## 🎯 Testing Objectives

This document details the testing strategy implemented to ensure quality and reliability of the Vitruvius platform.

## 📊 Code Coverage

### Coverage Target: **80%**

Code coverage is automatically monitored and must reach at least 80% for Pull Request approval.

### Coverage Reports

- **HTML**: `backend/htmlcov/index.html`
- **XML**: `backend/coverage.xml`
- **Terminal**: Direct output during test execution

## 🧪 Test Types

### 1. **Unit Tests** (`backend/tests/unit/`)

**Objective**: Test individual functions and methods in isolation.

#### Main Coverage:
- `test_rules_engine.py`: Tests the prescriptive rules engine
  - Cost and timeline calculations
  - Solution generation for different conflicts
  - Business logic validation

#### Execute:
```bash
cd backend
pytest tests/unit/ -v
```

### 2. **Integration Tests** (`backend/tests/integration/`)

**Objective**: Test interaction between system components.

#### Main Coverage:
- `test_auth_endpoints.py`: Authentication and authorization
- `test_project_endpoints.py`: Project CRUD, IFC upload, feedback

#### Execute:
```bash
cd backend
pytest tests/integration/ -v
```

### 3. **End-to-End Tests** (`e2e-tests/`)

**Objective**: Test complete user flows in the application.

#### Covered Scenarios:
- **Authentication Flow**: Registration, login, logout
- **Project Flow**: Creation, IFC upload, 3D visualization
- **Conflict Flow**: Detection, analysis, feedback
- **Feedback Flow**: Solution selection, custom feedback

#### Execute:
```bash
cd e2e-tests
npm install
npx playwright install
npx playwright test
```

## 🚀 Test Execution

### Local Development

```bash
# Unit and integration tests
cd backend
pytest --cov=app --cov-report=html --cov-report=term-missing

# E2E tests
cd e2e-tests
npx playwright test --headed
```

### CI/CD Pipeline

Tests are automatically executed in GitHub Actions:

1. **Backend Tests**: Unit + Integration
2. **Frontend Tests**: Jest + React Testing Library
3. **E2E Tests**: Playwright (only on main/master)
4. **Coverage Verification**: Will fail if < 80%

## 🎯 Complete User Journey (E2E)

### Main Tested Scenario:

1. **Login** to the platform
2. **Create a new BIM project**
3. **Upload IFC file**
4. **Wait for asynchronous processing**
5. **View processed 3D model**
6. **Click on identified collision issue**
7. **View prescriptive solutions**
8. **Select or describe solution**
9. **Provide feedback** on effectiveness
10. **Mark issue as resolved**

## 📋 Fixtures and Test Data

### Backend Fixtures (`backend/tests/factories.py`)

We use **Factory Boy** to create consistent test data:

- `UserFactory`: Test users
- `ProjectFactory`: Test projects
- `ConflictFactory`: Simulated conflicts
- `SolutionFactory`: Prescriptive solutions
- `SolutionFeedbackFactory`: User feedback

### E2E Fixtures (`e2e-tests/fixtures/`)

- `test-model.ifc`: Valid IFC model for testing
- Standardized user data
- Pre-defined conflict scenarios

## 🔧 Test Environment Configuration

### Backend

- **Database**: In-memory SQLite for speed
- **Authentication**: Mock users and tokens
- **Processing**: Mock Celery tasks
- **Uploads**: Temporary files

### Frontend

- **Local Server**: Started automatically
- **Browsers**: Chrome, Firefox, Safari, Mobile
- **Data**: Reset between tests

## 📊 Quality Metrics

### Coverage by Module:

| Module | Target | Current |
|---------|------|-------|
| `rules_engine.py` | 90% | ✅ |
| `auth.py` | 85% | ✅ |
| `project_endpoints.py` | 80% | ✅ |
| `database.py` | 75% | ✅ |
| `bim_processor.py` | 70% | ✅ |

### Execution Time:

- **Unit Tests**: < 30 seconds
- **Integration Tests**: < 2 minutes
- **E2E Tests**: < 10 minutes

## 🚫 Failure Criteria

### Pull Request will be blocked if:

1. **Coverage < 80%**
2. **Failing tests**
3. **Linting errors**
4. **Unstable E2E tests**

## 🔄 Test Maintenance

### Responsibilities:

- **Developers**: Create tests for new features
- **Code Review**: Verify test quality
- **CI/CD**: Execute tests automatically
- **Monitoring**: Track coverage trends

### Best Practices:

1. **Tests should be independent**
2. **Isolated test data**
3. **Descriptive names**
4. **Automatic cleanup**
5. **Mock external dependencies**

## 📚 Useful Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific tests
pytest tests/unit/test_rules_engine.py::TestRulesEngine::test_specific_function

# Run tests in parallel
pytest -n auto

# Run specific E2E tests
npx playwright test tests/auth.spec.js

# Run E2E tests in debug mode
npx playwright test --debug

# Generate coverage report
pytest --cov=app --cov-report=html && open htmlcov/index.html
```

## 🎯 Next Steps

1. **Implement performance tests**
2. **Add security tests**
3. **Expand coverage to 90%**
4. **Implement load tests**
5. **Add accessibility tests**

---

**Remember**: Tests are an investment in quality and confidence. Every test written today saves hours of debugging tomorrow! 🚀