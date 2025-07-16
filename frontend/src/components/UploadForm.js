/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

import React, { useState } from 'react';

function UploadForm({ projectId, onUploadSuccess }) {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
    setMessage('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!file) {
      setMessage('Please select an IFC file to upload.');
      return;
    }

    if (!projectId) {
      setMessage('Please select a project first.');
      return;
    }

    setUploading(true);
    setMessage('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`/api/projects/${projectId}/upload-ifc`, {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (response.ok) {
        setMessage('File uploaded successfully! Processing started...');
        setFile(null);
        if (onUploadSuccess) {
          onUploadSuccess(result);
        }
      } else {
        setMessage(`Upload failed: ${result.detail || 'Unknown error'}`);
      }
    } catch (error) {
      setMessage(`Upload failed: ${error.message}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ padding: '20px', border: '1px solid #ddd', borderRadius: '8px', margin: '20px 0' }}>
      <h2>Upload IFC Model</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '15px' }}>
          <input 
            type="file" 
            accept=".ifc" 
            onChange={handleFileChange}
            disabled={uploading}
            style={{ marginRight: '10px' }}
          />
          <button 
            type="submit" 
            disabled={uploading || !file}
            style={{
              padding: '8px 16px',
              backgroundColor: uploading ? '#ccc' : '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: uploading ? 'not-allowed' : 'pointer'
            }}
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
        {message && (
          <div style={{ 
            padding: '10px', 
            backgroundColor: message.includes('successfully') ? '#d4edda' : '#f8d7da',
            color: message.includes('successfully') ? '#155724' : '#721c24',
            borderRadius: '4px',
            fontSize: '14px'
          }}>
            {message}
          </div>
        )}
      </form>
    </div>
  );
}

export default UploadForm;