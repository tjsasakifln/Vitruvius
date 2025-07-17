/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

import React, { useState, useEffect } from 'react';
import SolutionFeedback from './SolutionFeedback';
import ConflictDetails from './ConflictDetails';
import ActivityTimeline from './ActivityTimeline';
import { SafeText, sanitizeObject } from '../utils/xssSanitizer';

function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [selectedConflict, setSelectedConflict] = useState(null);
  const [currentView, setCurrentView] = useState('overview'); // 'overview', 'conflict_details', 'activity'
  const [loading, setLoading] = useState(true);
  
  // Mock current user (in real app, get from auth context)
  const currentUser = { id: 1, full_name: 'Demo User', email: 'demo@example.com' };

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
      // Sanitize project data before setting state
      const sanitizedProjects = data.map(project => 
        sanitizeObject(project, ['name', 'description', 'status'], [])
      );
      setProjects(sanitizedProjects);
      
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

  const fetchConflicts = async (projectId = null, forceRefresh = false) => {
    try {
      const targetProjectId = projectId || (projects.length > 0 ? projects[0].id : 1);
      
      // Add cache-busting parameter when forcing refresh
      const url = forceRefresh 
        ? `/api/projects/${targetProjectId}/conflicts?_t=${Date.now()}`
        : `/api/projects/${targetProjectId}/conflicts`;
      
      const response = await fetch(url, {
        headers: forceRefresh ? { 'Cache-Control': 'no-cache' } : {}
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      // Sanitize conflict data before setting state
      const sanitizedConflicts = (data.conflicts || []).map(conflict => 
        sanitizeObject(conflict, ['type', 'description', 'severity', 'status'], [])
      );
      setConflicts(sanitizedConflicts);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching conflicts:', error);
      setConflicts([]);
      setLoading(false);
    }
  };

  const handleConflictSelect = (conflict) => {
    setSelectedConflict(conflict);
    setCurrentView('conflict_details');
  };

  const handleBackToOverview = () => {
    setSelectedConflict(null);
    setCurrentView('overview');
  };

  if (loading) {
    return <div>Loading dashboard...</div>;
  }

  // Render conflict details view
  if (currentView === 'conflict_details' && selectedConflict) {
    return (
      <div>
        <div style={{ padding: '20px', borderBottom: '1px solid #ddd', backgroundColor: '#f8f9fa' }}>
          <button 
            onClick={handleBackToOverview}
            style={{ 
              padding: '8px 16px', 
              backgroundColor: '#6c757d', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px',
              cursor: 'pointer',
              marginRight: '20px'
            }}
          >
            ← Back to Dashboard
          </button>
          <span style={{ fontSize: '18px', fontWeight: 'bold' }}>
            Conflict #{selectedConflict.id} - <SafeText text={selectedConflict.type} />
          </span>
        </div>
        <ConflictDetails 
          conflictId={selectedConflict.id}
          projectId={selectedProject}
          currentUser={currentUser}
        />
      </div>
    );
  }

  // Render activity timeline view
  if (currentView === 'activity') {
    return (
      <div>
        <div style={{ padding: '20px', borderBottom: '1px solid #ddd', backgroundColor: '#f8f9fa' }}>
          <button 
            onClick={() => setCurrentView('overview')}
            style={{ 
              padding: '8px 16px', 
              backgroundColor: '#6c757d', 
              color: 'white', 
              border: 'none', 
              borderRadius: '4px',
              cursor: 'pointer',
              marginRight: '20px'
            }}
          >
            ← Back to Dashboard
          </button>
          <span style={{ fontSize: '18px', fontWeight: 'bold' }}>Project Activity Timeline</span>
        </div>
        <ActivityTimeline projectId={selectedProject} />
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Vitruvius Dashboard</h1>
        
        {/* View Toggle */}
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={() => setCurrentView('overview')}
            style={{
              padding: '8px 16px',
              backgroundColor: currentView === 'overview' ? '#007bff' : '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Overview
          </button>
          <button
            onClick={() => setCurrentView('activity')}
            style={{
              padding: '8px 16px',
              backgroundColor: currentView === 'activity' ? '#007bff' : '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Activity Timeline
          </button>
        </div>
      </div>
      
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
                <h3><SafeText text={project.name} /></h3>
                <p><strong>Status:</strong> <SafeText text={project.status} /></p>
                {project.created_at && (
                  <p><strong>Created:</strong> {new Date(project.created_at).toLocaleDateString()}</p>
                )}
                <div style={{ display: 'flex', gap: '10px' }}>
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
                  <button 
                    onClick={() => {
                      setSelectedProject(project.id);
                      setCurrentView('activity');
                    }}
                    style={{
                      padding: '5px 10px',
                      backgroundColor: '#28a745',
                      color: 'white',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: 'pointer'
                    }}
                  >
                    View Activity
                  </button>
                </div>
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
                <h3><SafeText text={conflict.type ? conflict.type.charAt(0).toUpperCase() + conflict.type.slice(1) : 'Unknown'} /> Conflict</h3>
                <p><strong>Description:</strong> <SafeText text={conflict.description} /></p>
                <p><strong>Severity:</strong> <SafeText text={conflict.severity} /></p>
                <p><strong>Status:</strong> <SafeText text={conflict.status} /></p>
                <p><strong>Elements:</strong> <SafeText text={Array.isArray(conflict.elements) ? conflict.elements.join(', ') : conflict.elements || 'N/A'} /></p>
                {conflict.created_at && (
                  <p><strong>Detected:</strong> {new Date(conflict.created_at).toLocaleDateString()}</p>
                )}
                
                <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                  <button
                    onClick={() => handleConflictSelect(conflict)}
                    style={{
                      padding: '5px 10px',
                      backgroundColor: '#17a2b8',
                      color: 'white',
                      border: 'none',
                      borderRadius: '3px',
                      cursor: 'pointer'
                    }}
                  >
                    View Details & Collaborate
                  </button>
                  <SolutionFeedback 
                    projectId={selectedProject} 
                    conflictId={conflict.id} 
                  />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p>No conflicts detected. Your project is looking good!</p>
        )}
      </div>

      <div>
        <h2>Prescriptive Analysis Engine Recommendations</h2>
        <p>Prescriptive solutions from the Analysis Engine will appear here when conflicts are detected.</p>
        <p><strong>Importante:</strong> Após revisar as soluções sugeridas, por favor forneça feedback sobre qual solução você implementou. Isso nos ajuda a melhorar nosso sistema!</p>
      </div>
    </div>
  );
}

export default Dashboard;