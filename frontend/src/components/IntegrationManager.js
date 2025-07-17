/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

import React, { useState, useEffect } from 'react';

function IntegrationManager({ projectId }) {
  const [integrationConfig, setIntegrationConfig] = useState(null);
  const [availableIntegrations, setAvailableIntegrations] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [configureMode, setConfigureMode] = useState({ type: null, tool: null });
  const [formData, setFormData] = useState({});

  useEffect(() => {
    if (projectId) {
      fetchIntegrationData();
    }
  }, [projectId]);

  const fetchIntegrationData = async () => {
    try {
      setLoading(true);
      
      const [configResponse, availableResponse] = await Promise.all([
        fetch(`/api/integrations/projects/${projectId}/config`),
        fetch('/api/integrations/available')
      ]);

      if (!configResponse.ok || !availableResponse.ok) {
        throw new Error('Failed to fetch integration data');
      }

      const [config, available] = await Promise.all([
        configResponse.json(),
        availableResponse.json()
      ]);

      setIntegrationConfig(config);
      setAvailableIntegrations(available);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfigure = (type, toolKey) => {
    setConfigureMode({ type, tool: toolKey });
    setFormData({
      integration_type: toolKey,
      api_key: '',
      project_id: '',
      base_url: '',
      config: {}
    });
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const endpoint = `/api/integrations/projects/${projectId}/${configureMode.type}/configure`;
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Configuration failed');
      }

      const result = await response.json();
      alert(result.message);
      
      // Refresh data and close form
      await fetchIntegrationData();
      setConfigureMode({ type: null, tool: null });
      setFormData({});
      
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  };

  const handleTest = async () => {
    try {
      const response = await fetch(`/api/integrations/projects/${projectId}/test`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('Test failed');
      }
      
      const result = await response.json();
      alert(result.message);
      
    } catch (err) {
      alert(`Test error: ${err.message}`);
    }
  };

  const handleRemove = async (type) => {
    if (!confirm(`Are you sure you want to remove the ${type} integration?`)) {
      return;
    }
    
    try {
      const response = await fetch(`/api/integrations/projects/${projectId}/${type}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        throw new Error('Remove failed');
      }
      
      const result = await response.json();
      alert(result.message);
      await fetchIntegrationData();
      
    } catch (err) {
      alert(`Remove error: ${err.message}`);
    }
  };

  if (loading) {
    return <div style={{ padding: '20px' }}>Loading integration settings...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: 'red' }}>
        <h3>Error loading integrations: {error}</h3>
        <button onClick={fetchIntegrationData}>Retry</button>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <h2>Integration Manager</h2>
      
      {/* Current Status */}
      <div style={{ marginBottom: '30px', padding: '15px', backgroundColor: '#f8f9fa', borderRadius: '5px' }}>
        <h3>Current Status</h3>
        <p><strong>Sync Status:</strong> {integrationConfig?.sync_status || 'Not configured'}</p>
        {integrationConfig?.last_sync_at && (
          <p><strong>Last Sync:</strong> {new Date(integrationConfig.last_sync_at).toLocaleString()}</p>
        )}
        {integrationConfig?.sync_error_message && (
          <p style={{ color: 'red' }}><strong>Error:</strong> {integrationConfig.sync_error_message}</p>
        )}
      </div>

      {/* Planning Tools */}
      <div style={{ marginBottom: '30px' }}>
        <h3>Planning Tools</h3>
        
        {integrationConfig?.planning_tool?.connected ? (
          <div style={{ padding: '15px', border: '1px solid #ddd', borderRadius: '5px', backgroundColor: '#d4edda' }}>
            <h4>{integrationConfig.planning_tool.connected.charAt(0).toUpperCase() + integrationConfig.planning_tool.connected.slice(1)} - Connected</h4>
            <p><strong>Project ID:</strong> {integrationConfig.planning_tool.project_id}</p>
            <p><strong>Base URL:</strong> {integrationConfig.planning_tool.base_url}</p>
            <div style={{ marginTop: '10px' }}>
              <button 
                onClick={handleTest}
                style={{ marginRight: '10px', padding: '5px 10px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '3px' }}
              >
                Test Connection
              </button>
              <button 
                onClick={() => handleRemove('planning')}
                style={{ padding: '5px 10px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '3px' }}
              >
                Remove
              </button>
            </div>
          </div>
        ) : (
          <div>
            <p>No planning tool connected.</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px' }}>
              {availableIntegrations?.planning_tools && Object.entries(availableIntegrations.planning_tools).map(([key, tool]) => (
                <div key={key} style={{ padding: '15px', border: '1px solid #ddd', borderRadius: '5px' }}>
                  <h4>{tool.name}</h4>
                  <p>{tool.description}</p>
                  <button 
                    onClick={() => handleConfigure('planning', key)}
                    style={{ padding: '5px 10px', backgroundColor: '#28a745', color: 'white', border: 'none', borderRadius: '3px' }}
                  >
                    Configure
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Budget Tools */}
      <div style={{ marginBottom: '30px' }}>
        <h3>Budget Tools</h3>
        
        {integrationConfig?.budget_tool?.connected ? (
          <div style={{ padding: '15px', border: '1px solid #ddd', borderRadius: '5px', backgroundColor: '#d4edda' }}>
            <h4>{integrationConfig.budget_tool.connected.charAt(0).toUpperCase() + integrationConfig.budget_tool.connected.slice(1)} - Connected</h4>
            <p><strong>Project ID:</strong> {integrationConfig.budget_tool.project_id}</p>
            <p><strong>Base URL:</strong> {integrationConfig.budget_tool.base_url}</p>
            <button 
              onClick={() => handleRemove('budget')}
              style={{ padding: '5px 10px', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '3px' }}
            >
              Remove
            </button>
          </div>
        ) : (
          <div>
            <p>No budget tool connected.</p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px' }}>
              {availableIntegrations?.budget_tools && Object.entries(availableIntegrations.budget_tools).map(([key, tool]) => (
                <div key={key} style={{ padding: '15px', border: '1px solid #ddd', borderRadius: '5px' }}>
                  <h4>{tool.name}</h4>
                  <p>{tool.description}</p>
                  <p><em>Status: {tool.status || 'Available'}</em></p>
                  <button 
                    onClick={() => handleConfigure('budget', key)}
                    disabled={tool.status === 'planned'}
                    style={{ 
                      padding: '5px 10px', 
                      backgroundColor: tool.status === 'planned' ? '#6c757d' : '#28a745', 
                      color: 'white', 
                      border: 'none', 
                      borderRadius: '3px',
                      cursor: tool.status === 'planned' ? 'not-allowed' : 'pointer'
                    }}
                  >
                    {tool.status === 'planned' ? 'Coming Soon' : 'Configure'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Configuration Form */}
      {configureMode.type && (
        <div style={{ 
          position: 'fixed', 
          top: 0, 
          left: 0, 
          right: 0, 
          bottom: 0, 
          backgroundColor: 'rgba(0,0,0,0.5)', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{ 
            backgroundColor: 'white', 
            padding: '30px', 
            borderRadius: '8px', 
            maxWidth: '500px', 
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto'
          }}>
            <h3>Configure {configureMode.tool} Integration</h3>
            
            <form onSubmit={handleFormSubmit}>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>API Key:</label>
                <input
                  type="password"
                  value={formData.api_key}
                  onChange={(e) => setFormData({...formData, api_key: e.target.value})}
                  required
                  style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '3px' }}
                />
              </div>
              
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>External Project ID:</label>
                <input
                  type="text"
                  value={formData.project_id}
                  onChange={(e) => setFormData({...formData, project_id: e.target.value})}
                  required
                  style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '3px' }}
                />
              </div>
              
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>Base URL:</label>
                <input
                  type="url"
                  value={formData.base_url}
                  onChange={(e) => setFormData({...formData, base_url: e.target.value})}
                  placeholder="https://api.example.com"
                  style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '3px' }}
                />
              </div>

              {/* Tool-specific configuration fields */}
              {configureMode.tool === 'primavera' && (
                <>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px' }}>Database Instance:</label>
                    <input
                      type="number"
                      value={formData.config?.database_instance || 1}
                      onChange={(e) => setFormData({
                        ...formData, 
                        config: {...formData.config, database_instance: parseInt(e.target.value)}
                      })}
                      style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '3px' }}
                    />
                  </div>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px' }}>Username:</label>
                    <input
                      type="text"
                      value={formData.config?.user_name || 'admin'}
                      onChange={(e) => setFormData({
                        ...formData, 
                        config: {...formData.config, user_name: e.target.value}
                      })}
                      style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '3px' }}
                    />
                  </div>
                </>
              )}

              {configureMode.tool === 'msproject' && (
                <div style={{ marginBottom: '15px' }}>
                  <label style={{ display: 'block', marginBottom: '5px' }}>Tenant ID:</label>
                  <input
                    type="text"
                    value={formData.config?.tenant_id || ''}
                    onChange={(e) => setFormData({
                      ...formData, 
                      config: {...formData.config, tenant_id: e.target.value}
                    })}
                    required
                    style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '3px' }}
                  />
                </div>
              )}
              
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                <button 
                  type="button"
                  onClick={() => setConfigureMode({ type: null, tool: null })}
                  style={{ padding: '8px 15px', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '3px' }}
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  style={{ padding: '8px 15px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '3px' }}
                >
                  Save Configuration
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default IntegrationManager;