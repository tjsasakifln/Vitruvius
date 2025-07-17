/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

import React, { useState } from 'react';
import Dashboard from './components/Dashboard';
import PortfolioDashboard from './components/PortfolioDashboard';
import UploadForm from './components/UploadForm';
import Viewer3D from './components/Viewer3D';
import IntegrationManager from './components/IntegrationManager';
import './App.css';

function App() {
  const [activeView, setActiveView] = useState('dashboard');

  const renderContent = () => {
    switch (activeView) {
      case 'portfolio':
        return <PortfolioDashboard />;
      case 'integrations':
        return <IntegrationManager projectId={1} />;
      case 'upload':
        return <UploadForm projectId={1} />;
      case 'viewer':
        return <Viewer3D />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Vitruvius</h1>
        <p>BIM Project Coordination Platform with Prescriptive Analysis Engine</p>
        
        {/* Navigation */}
        <nav style={{ marginTop: '20px' }}>
          <button 
            onClick={() => setActiveView('dashboard')}
            style={{ 
              marginRight: '10px',
              padding: '10px 15px',
              backgroundColor: activeView === 'dashboard' ? '#007bff' : '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            Project Dashboard
          </button>
          <button 
            onClick={() => setActiveView('portfolio')}
            style={{ 
              marginRight: '10px',
              padding: '10px 15px',
              backgroundColor: activeView === 'portfolio' ? '#007bff' : '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            Portfolio Analytics
          </button>
          <button 
            onClick={() => setActiveView('integrations')}
            style={{ 
              marginRight: '10px',
              padding: '10px 15px',
              backgroundColor: activeView === 'integrations' ? '#007bff' : '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            Integrations
          </button>
          <button 
            onClick={() => setActiveView('upload')}
            style={{ 
              marginRight: '10px',
              padding: '10px 15px',
              backgroundColor: activeView === 'upload' ? '#007bff' : '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            Upload Files
          </button>
          <button 
            onClick={() => setActiveView('viewer')}
            style={{ 
              padding: '10px 15px',
              backgroundColor: activeView === 'viewer' ? '#007bff' : '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '5px',
              cursor: 'pointer'
            }}
          >
            3D Viewer
          </button>
        </nav>
      </header>
      
      <main>
        {renderContent()}
      </main>
    </div>
  );
}

export default App;
