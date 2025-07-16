import React, { useState, useEffect } from 'react';

function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProjects();
    fetchConflicts();
  }, []);

  const fetchProjects = async () => {
    try {
      const response = await fetch('/api/projects');
      const data = await response.json();
      setProjects(data);
    } catch (error) {
      console.error('Error fetching projects:', error);
    }
  };

  const fetchConflicts = async () => {
    try {
      // Mock conflicts data for demonstration
      const mockConflicts = [
        {
          id: 1,
          type: 'collision',
          description: 'Beam conflicts with column',
          severity: 'high',
          elements: ['beam_123', 'column_456'],
          project_id: 1
        },
        {
          id: 2,
          type: 'clearance',
          description: 'Insufficient clearance for maintenance',
          severity: 'medium',
          elements: ['pipe_789', 'wall_101'],
          project_id: 1
        }
      ];
      setConflicts(mockConflicts);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching conflicts:', error);
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
          <ul>
            {projects.map(project => (
              <li key={project.id}>
                <strong>{project.name}</strong> - Status: {project.status}
              </li>
            ))}
          </ul>
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
                <h3>{conflict.type.charAt(0).toUpperCase() + conflict.type.slice(1)} Conflict</h3>
                <p><strong>Description:</strong> {conflict.description}</p>
                <p><strong>Severity:</strong> {conflict.severity}</p>
                <p><strong>Elements:</strong> {conflict.elements.join(', ')}</p>
              </div>
            ))}
          </div>
        ) : (
          <p>No conflicts detected. Your project is looking good!</p>
        )}
      </div>

      <div>
        <h2>AI Recommendations</h2>
        <p>AI-powered prescriptive solutions will appear here when conflicts are detected.</p>
      </div>
    </div>
  );
}

export default Dashboard;
