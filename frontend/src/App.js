import React from 'react';
import Dashboard from './components/Dashboard';
import UploadForm from './components/UploadForm';
import Viewer3D from './components/Viewer3D';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Vitruvius</h1>
        <p>AI-Powered BIM Project Coordination Platform</p>
      </header>
      
      <main>
        <Dashboard />
        <UploadForm projectId={1} />
        <Viewer3D />
      </main>
    </div>
  );
}

export default App;