/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

import React, { useState, useEffect } from 'react';

const APSIntegration = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [hubs, setHubs] = useState([]);
  const [selectedHub, setSelectedHub] = useState(null);
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectContents, setProjectContents] = useState([]);
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [processingStatus, setProcessingStatus] = useState({});

  // API base URL
  const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

  useEffect(() => {
    // Check if user is authenticated with APS
    checkAPSAuth();
  }, []);

  const checkAPSAuth = async () => {
    try {
      const response = await fetch(`${API_BASE}/aps/hubs`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      
      if (response.ok) {
        setIsAuthenticated(true);
        const data = await response.json();
        setHubs(data.hubs);
      } else {
        // Handle case where token is invalid or expired
        setIsAuthenticated(false);
      }
    } catch (err) {
      console.log('Not authenticated with APS yet');
      setIsAuthenticated(false);
    }
  };

  const authenticateWithAPS = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE}/aps/auth/login`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        window.location.href = data.auth_url;
      } else {
        setError('Failed to initiate APS authentication');
      }
    }
    catch (err) {
      setError('Error connecting to APS: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const loadProjects = async (hubId) => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE}/aps/hubs/${hubId}/projects`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setProjects(data.projects);
        setSelectedHub(hubId);
      } else {
        setError('Failed to load projects');
      }
    } catch (err) {
      setError('Error loading projects: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const loadProjectContents = async (projectId, folderId = null) => {
    try {
      setIsLoading(true);
      const url = folderId 
        ? `${API_BASE}/aps/projects/${projectId}/contents?folder_id=${folderId}`
        : `${API_BASE}/aps/projects/${projectId}/contents`;
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setProjectContents(data.contents);
        setSelectedProject(projectId);
        setSelectedFolder(folderId);
      } else {
        setError('Failed to load project contents');
      }
    } catch (err) {
      setError('Error loading project contents: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const processModel = async (projectId, itemId) => {
    try {
      setIsLoading(true);
      setProcessingStatus({
        ...processingStatus,
        [itemId]: 'processing'
      });
      
      const response = await fetch(`${API_BASE}/aps/projects/${projectId}/items/${itemId}/process`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setProcessingStatus({
          ...processingStatus,
          [itemId]: 'started'
        });
        
        alert(`Model processing started!\nTask ID: ${data.task_id}\nModel ID: ${data.model_id}`);
      } else {
        setError('Failed to process model');
        setProcessingStatus({
          ...processingStatus,
          [itemId]: 'failed'
        });
      }
    } catch (err) {
      setError('Error processing model: ' + err.message);
      setProcessingStatus({
        ...processingStatus,
        [itemId]: 'failed'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const renderHubsList = () => (
    <div>
      <h3>Select a Hub</h3>
      <div style={{ display: 'grid', gap: '10px' }}>
        {hubs.map(hub => (
          <div 
            key={hub.id} 
            onClick={() => loadProjects(hub.id)}
            style={{
              padding: '15px',
              border: '1px solid #ddd',
              borderRadius: '8px',
              cursor: 'pointer',
              backgroundColor: selectedHub === hub.id ? '#e3f2fd' : '#f9f9f9'
            }}
          >
            <h4>{hub.name}</h4>
            <p>Type: {hub.type}</p>
            <p>Region: {hub.region}</p>
          </div>
        ))}
      </div>
    </div>
  );

  const renderProjectsList = () => (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
        <button onClick={() => setSelectedHub(null)}>← Back to Hubs</button>
        <h3>Select a Project</h3>
      </div>
      
      <div style={{ display: 'grid', gap: '10px' }}>
        {projects.map(project => (
          <div 
            key={project.id} 
            onClick={() => loadProjectContents(project.id)}
            style={{
              padding: '15px',
              border: '1px solid #ddd',
              borderRadius: '8px',
              cursor: 'pointer',
              backgroundColor: selectedProject === project.id ? '#e3f2fd' : '#f9f9f9'
            }}
          >
            <h4>{project.name}</h4>
            <p>Status: {project.status}</p>
            <p>Created: {new Date(project.created_at).toLocaleDateString()}</p>
          </div>
        ))}
      </div>
    </div>
  );

  const renderProjectContents = () => (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '20px' }}>
        <button onClick={() => setSelectedProject(null)}>← Back to Projects</button>
        <h3>Project Contents</h3>
      </div>
      
      <div style={{ display: 'grid', gap: '10px' }}>
        {projectContents.map(item => (
          <div 
            key={item.id} 
            style={{
              padding: '15px',
              border: '1px solid #ddd',
              borderRadius: '8px',
              backgroundColor: '#f9f9f9',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <div>
              <h4>{item.name}</h4>
              <p>Type: {item.is_folder ? 'Folder' : 'File'}</p>
              {!item.is_folder && (
                <>
                  <p>Extension: {item.extension}</p>
                  <p>Size: {(item.size / 1024 / 1024).toFixed(2)} MB</p>
                </>
              )}
              <p>Updated: {new Date(item.updated_at).toLocaleDateString()}</p>
            </div>
            
            <div style={{ display: 'flex', gap: '10px' }}>
              {item.is_folder ? (
                <button 
                  onClick={() => loadProjectContents(selectedProject, item.id)}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: '#2196F3',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer'
                  }}
                >
                  Open Folder
                </button>
              ) : (
                <button 
                  onClick={() => processModel(selectedProject, item.id)}
                  disabled={processingStatus[item.id] === 'processing'}
                  style={{
                    padding: '8px 16px',
                    backgroundColor: processingStatus[item.id] === 'processing' ? '#ccc' : '#4CAF50',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: processingStatus[item.id] === 'processing' ? 'not-allowed' : 'pointer'
                  }}
                >
                  {processingStatus[item.id] === 'processing' ? 'Processing...' : 'Process in Vitruvius'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Autodesk Platform Services Integration</h1>
      
      {error && (
        <div style={{
          padding: '10px',
          backgroundColor: '#ffebee',
          border: '1px solid #f44336',
          borderRadius: '4px',
          color: '#c62828',
          marginBottom: '20px'
        }}>
          {error}
        </div>
      )}
      
      {isLoading && (
        <div style={{
          padding: '10px',
          backgroundColor: '#e3f2fd',
          border: '1px solid #2196F3',
          borderRadius: '4px',
          color: '#1976d2',
          marginBottom: '20px'
        }}>
          Loading...
        </div>
      )}
      
      {!isAuthenticated ? (
        <div style={{ textAlign: 'center', marginTop: '50px' }}>
          <h2>Connect to Autodesk Platform Services</h2>
          <p>Access your BIM 360 and Autodesk Construction Cloud projects directly from Vitruvius.</p>
          
          <button 
            onClick={authenticateWithAPS}
            disabled={isLoading}
            style={{
              padding: '12px 24px',
              backgroundColor: '#FF6B00',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '16px',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              marginTop: '20px'
            }}
          >
            {isLoading ? 'Connecting...' : 'Connect to APS'}
          </button>
        </div>
      ) : (
        <div>
          {!selectedHub && renderHubsList()}
          {selectedHub && !selectedProject && renderProjectsList()}
          {selectedProject && renderProjectContents()}
        </div>
      )}
    </div>
  );
};

export default APSIntegration;
