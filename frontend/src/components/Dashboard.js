/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

import React, { useState, useEffect } from 'react';
import SolutionFeedback from './SolutionFeedback';

function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await fetch('/api/projects');
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setProjects(data);
      
      if (data.length > 0) {
        setSelectedProject(data[0].id);
        await fetchConflicts(data[0].id);
      } else {
        setLoading(false);
      }
    } catch (error) {
      console.error('Error fetching projects:', error);
      setLoading(false);
    }
  };

  const fetchConflicts = async (projectId = null) => {
    try {
      const targetProjectId = projectId || (projects.length > 0 ? projects[0].id : 1);
      
      const response = await fetch(`/api/projects/${targetProjectId}/conflicts`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setConflicts(data.conflicts || []);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching conflicts:', error);
      setConflicts([]);
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading dashboard...</div>;
  }

  return (
    <div style={{ padding: '20px' }}>
      <h1>Vitruvius Dashboard</h1>
      
      <div style={{ marginBottom: '30px' }}>
        <h2>Projects</h2>
        {projects.length > 0 ? (
          <div>
            {projects.map(project => (
              <div key={project.id} style={{ 
                border: '1px solid #ddd', 
                padding: '15px', 
                margin: '10px 0',
                borderRadius: '5px',
                backgroundColor: '#fff'
              }}>
                <h3>{project.name}</h3>
                <p><strong>Status:</strong> {project.status}</p>
                {project.created_at && (
                  <p><strong>Created:</strong> {new Date(project.created_at).toLocaleDateString()}</p>
                )}
                <button 
                  onClick={() => {
                    setSelectedProject(project.id);
                    fetchConflicts(project.id);
                  }}
                  style={{
                    padding: '5px 10px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '3px',
                    cursor: 'pointer'
                  }}
                >
                  View Conflicts
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p>No projects found. Create your first project to get started.</p>
        )}
      </div>

      <div style={{ marginBottom: '30px' }}>
        <h2>Detected Conflicts</h2>
        {conflicts.length > 0 ? (
          <div>
            {conflicts.map(conflict => (
              <div key={conflict.id} style={{ 
                border: '1px solid #ccc', 
                padding: '10px', 
                margin: '10px 0',
                borderRadius: '5px',
                backgroundColor: conflict.severity === 'high' ? '#ffebee' : '#fff3e0'
              }}>
                <h3>{conflict.type ? conflict.type.charAt(0).toUpperCase() + conflict.type.slice(1) : 'Unknown'} Conflict</h3>
                <p><strong>Description:</strong> {conflict.description}</p>
                <p><strong>Severity:</strong> {conflict.severity}</p>
                <p><strong>Status:</strong> {conflict.status}</p>
                <p><strong>Elements:</strong> {Array.isArray(conflict.elements) ? conflict.elements.join(', ') : conflict.elements || 'N/A'}</p>
                {conflict.created_at && (
                  <p><strong>Detected:</strong> {new Date(conflict.created_at).toLocaleDateString()}</p>
                )}
                
                <SolutionFeedback 
                  projectId={selectedProject} 
                  conflictId={conflict.id} 
                />
              </div>
            ))}
          </div>
        ) : (
          <p>No conflicts detected. Your project is looking good!</p>
        )}
      </div>

      <div>
        <h2>Recomendações do Motor de Análise Prescritiva</h2>
        <p>Soluções prescritivas do Motor de Análise Prescritiva aparecerão aqui quando conflitos forem detectados.</p>
        <p><strong>Importante:</strong> Após revisar as soluções sugeridas, por favor forneça feedback sobre qual solução você implementou. Isso nos ajuda a melhorar nosso sistema!</p>
      </div>
    </div>
  );
}

export default Dashboard;