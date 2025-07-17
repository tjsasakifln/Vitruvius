/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

import React, { useState, useRef, useEffect } from 'react';

function AnnotationEditor({ conflictId, onAnnotationAdded, existingAnnotations, currentUser }) {
  const [isCreating, setIsCreating] = useState(false);
  const [annotations, setAnnotations] = useState(existingAnnotations || []);
  const [selectedTool, setSelectedTool] = useState('point');
  const [newAnnotation, setNewAnnotation] = useState({
    title: '',
    description: '',
    priority: 'medium',
    annotation_type: 'point',
    position_data: {},
    visual_data: {}
  });

  const canvasRef = useRef(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [currentPosition, setCurrentPosition] = useState(null);

  useEffect(() => {
    setAnnotations(existingAnnotations || []);
  }, [existingAnnotations]);

  const annotationTools = [
    { id: 'point', name: 'Point', icon: '📍', description: 'Mark a specific location' },
    { id: 'area', name: 'Area', icon: '🔲', description: 'Highlight an area' },
    { id: 'measurement', name: 'Measure', icon: '📏', description: 'Measure distance/area' },
    { id: 'highlight', name: 'Highlight', icon: '🖍️', description: 'Highlight text/objects' }
  ];

  const priorityOptions = [
    { value: 'low', color: '#28a745', label: 'Low' },
    { value: 'medium', color: '#ffc107', label: 'Medium' },
    { value: 'high', color: '#fd7e14', label: 'High' },
    { value: 'critical', color: '#dc3545', label: 'Critical' }
  ];

  const handleCanvasClick = (event) => {
    if (!isCreating) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const position = {
      x: x / rect.width,  // Normalize to 0-1
      y: y / rect.height,
      timestamp: new Date().toISOString()
    };

    setCurrentPosition(position);
    
    if (selectedTool === 'point') {
      // For point annotations, immediately show the form
      setNewAnnotation(prev => ({
        ...prev,
        annotation_type: selectedTool,
        position_data: {
          type: 'point',
          coordinates: { x: position.x, y: position.y }
        }
      }));
    } else if (selectedTool === 'area' && !isDrawing) {
      // Start area selection
      setIsDrawing(true);
      setNewAnnotation(prev => ({
        ...prev,
        annotation_type: selectedTool,
        position_data: {
          type: 'area',
          start: { x: position.x, y: position.y }
        }
      }));
    } else if (selectedTool === 'area' && isDrawing) {
      // Complete area selection
      setIsDrawing(false);
      setNewAnnotation(prev => ({
        ...prev,
        position_data: {
          ...prev.position_data,
          end: { x: position.x, y: position.y }
        }
      }));
    }
  };

  const handleCanvasMouseMove = (event) => {
    if (!isDrawing) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const position = {
      x: x / rect.width,
      y: y / rect.height
    };

    // Update temporary end position for area selection
    setCurrentPosition(position);
  };

  const renderAnnotations = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const rect = canvas.getBoundingClientRect();
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Render existing annotations
    annotations.forEach((annotation, index) => {
      if (!annotation.position_data) return;

      const { position_data, visual_data, priority } = annotation;
      const priorityColor = priorityOptions.find(p => p.value === priority)?.color || '#6c757d';

      ctx.strokeStyle = priorityColor;
      ctx.fillStyle = priorityColor + '40'; // Add transparency
      ctx.lineWidth = 2;

      if (position_data.type === 'point') {
        const x = position_data.coordinates.x * canvas.width;
        const y = position_data.coordinates.y * canvas.height;
        
        // Draw point marker
        ctx.beginPath();
        ctx.arc(x, y, 8, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();
        
        // Draw annotation number
        ctx.fillStyle = 'white';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText((index + 1).toString(), x, y);
      } else if (position_data.type === 'area' && position_data.start && position_data.end) {
        const startX = position_data.start.x * canvas.width;
        const startY = position_data.start.y * canvas.height;
        const endX = position_data.end.x * canvas.width;
        const endY = position_data.end.y * canvas.height;
        
        const width = endX - startX;
        const height = endY - startY;
        
        // Draw rectangle
        ctx.beginPath();
        ctx.rect(startX, startY, width, height);
        ctx.fill();
        ctx.stroke();
      }
    });

    // Render current drawing
    if (isDrawing && newAnnotation.position_data.start && currentPosition) {
      ctx.strokeStyle = '#007bff';
      ctx.fillStyle = '#007bff40';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);

      const startX = newAnnotation.position_data.start.x * canvas.width;
      const startY = newAnnotation.position_data.start.y * canvas.height;
      const endX = currentPosition.x * canvas.width;
      const endY = currentPosition.y * canvas.height;
      
      const width = endX - startX;
      const height = endY - startY;
      
      ctx.beginPath();
      ctx.rect(startX, startY, width, height);
      ctx.fill();
      ctx.stroke();
      
      ctx.setLineDash([]);
    }
  };

  useEffect(() => {
    renderAnnotations();
  }, [annotations, isDrawing, currentPosition, newAnnotation]);

  const handleCreateAnnotation = async () => {
    if (!newAnnotation.title.trim()) {
      alert('Please enter a title for the annotation');
      return;
    }

    try {
      const response = await fetch(`/api/collaboration/conflicts/${conflictId}/annotations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...newAnnotation,
          visual_data: {
            color: priorityOptions.find(p => p.value === newAnnotation.priority)?.color || '#6c757d',
            created_by: currentUser?.full_name
          }
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create annotation');
      }

      const result = await response.json();
      
      // Add to local annotations list
      setAnnotations(prev => [result, ...prev]);
      
      // Reset form
      setNewAnnotation({
        title: '',
        description: '',
        priority: 'medium',
        annotation_type: 'point',
        position_data: {},
        visual_data: {}
      });
      setIsCreating(false);
      setIsDrawing(false);
      setCurrentPosition(null);

      // Notify parent component
      if (onAnnotationAdded) {
        onAnnotationAdded(result);
      }

    } catch (err) {
      alert(`Error creating annotation: ${err.message}`);
    }
  };

  const cancelAnnotation = () => {
    setNewAnnotation({
      title: '',
      description: '',
      priority: 'medium',
      annotation_type: 'point',
      position_data: {},
      visual_data: {}
    });
    setIsCreating(false);
    setIsDrawing(false);
    setCurrentPosition(null);
  };

  return (
    <div style={{ border: '1px solid #ddd', borderRadius: '8px', overflow: 'hidden' }}>
      {/* Toolbar */}
      <div style={{ 
        backgroundColor: '#f8f9fa', 
        padding: '15px', 
        borderBottom: '1px solid #ddd',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h4 style={{ margin: '0 0 10px 0' }}>Annotations ({annotations.length})</h4>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            {annotationTools.map(tool => (
              <button
                key={tool.id}
                onClick={() => setSelectedTool(tool.id)}
                style={{
                  padding: '8px 12px',
                  border: `2px solid ${selectedTool === tool.id ? '#007bff' : '#ddd'}`,
                  borderRadius: '4px',
                  backgroundColor: selectedTool === tool.id ? '#e3f2fd' : 'white',
                  cursor: 'pointer',
                  fontSize: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px'
                }}
                title={tool.description}
              >
                <span>{tool.icon}</span>
                <span>{tool.name}</span>
              </button>
            ))}
          </div>
        </div>
        
        <button
          onClick={() => setIsCreating(!isCreating)}
          style={{
            padding: '10px 20px',
            backgroundColor: isCreating ? '#dc3545' : '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          {isCreating ? 'Cancel' : 'Add Annotation'}
        </button>
      </div>

      {/* Canvas Area */}
      <div style={{ position: 'relative', backgroundColor: '#f0f0f0', minHeight: '400px' }}>
        <canvas
          ref={canvasRef}
          width={800}
          height={400}
          onClick={handleCanvasClick}
          onMouseMove={handleCanvasMouseMove}
          style={{
            width: '100%',
            height: '400px',
            cursor: isCreating ? 'crosshair' : 'default',
            display: 'block'
          }}
        />
        
        {/* Instructions */}
        <div style={{
          position: 'absolute',
          top: '10px',
          left: '10px',
          backgroundColor: 'rgba(0,0,0,0.7)',
          color: 'white',
          padding: '5px 10px',
          borderRadius: '4px',
          fontSize: '12px'
        }}>
          {isCreating ? (
            selectedTool === 'point' ? 'Click to place annotation' :
            selectedTool === 'area' ? (
              isDrawing ? 'Click to complete area selection' : 'Click and drag to select area'
            ) : `Click to use ${selectedTool} tool`
          ) : 'Click "Add Annotation" to start'}
        </div>
      </div>

      {/* Annotation Form */}
      {isCreating && (newAnnotation.position_data.coordinates || newAnnotation.position_data.end) && (
        <div style={{ 
          padding: '20px', 
          backgroundColor: '#f8f9fa', 
          borderTop: '1px solid #ddd' 
        }}>
          <h5>Create Annotation</h5>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px', marginBottom: '15px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Title:</label>
              <input
                type="text"
                value={newAnnotation.title}
                onChange={(e) => setNewAnnotation(prev => ({ ...prev, title: e.target.value }))}
                placeholder="Annotation title..."
                style={{ 
                  width: '100%', 
                  padding: '8px', 
                  border: '1px solid #ddd', 
                  borderRadius: '4px' 
                }}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Priority:</label>
              <select
                value={newAnnotation.priority}
                onChange={(e) => setNewAnnotation(prev => ({ ...prev, priority: e.target.value }))}
                style={{ 
                  width: '100%', 
                  padding: '8px', 
                  border: '1px solid #ddd', 
                  borderRadius: '4px' 
                }}
              >
                {priorityOptions.map(option => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          
          <div style={{ marginBottom: '15px' }}>
            <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Description:</label>
            <textarea
              value={newAnnotation.description}
              onChange={(e) => setNewAnnotation(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Describe the issue or observation..."
              style={{ 
                width: '100%', 
                minHeight: '80px', 
                padding: '8px', 
                border: '1px solid #ddd', 
                borderRadius: '4px',
                resize: 'vertical'
              }}
            />
          </div>
          
          <div style={{ display: 'flex', gap: '10px' }}>
            <button
              onClick={handleCreateAnnotation}
              style={{
                padding: '10px 20px',
                backgroundColor: '#28a745',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Save Annotation
            </button>
            <button
              onClick={cancelAnnotation}
              style={{
                padding: '10px 20px',
                backgroundColor: '#6c757d',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Annotations List */}
      {annotations.length > 0 && (
        <div style={{ 
          maxHeight: '300px', 
          overflowY: 'auto', 
          borderTop: '1px solid #ddd' 
        }}>
          {annotations.map((annotation, index) => (
            <div key={annotation.id} style={{ 
              padding: '15px', 
              borderBottom: '1px solid #eee',
              backgroundColor: annotation.is_resolved ? '#d4edda' : 'white'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ 
                    display: 'inline-block',
                    width: '20px',
                    height: '20px',
                    borderRadius: '50%',
                    backgroundColor: priorityOptions.find(p => p.value === annotation.priority)?.color || '#6c757d',
                    color: 'white',
                    textAlign: 'center',
                    lineHeight: '20px',
                    fontSize: '12px',
                    fontWeight: 'bold'
                  }}>
                    {index + 1}
                  </span>
                  <strong>{annotation.title}</strong>
                  <span style={{ 
                    padding: '2px 6px', 
                    backgroundColor: '#e9ecef', 
                    borderRadius: '10px', 
                    fontSize: '10px' 
                  }}>
                    {annotation.annotation_type}
                  </span>
                </div>
                <span style={{ 
                  padding: '4px 8px', 
                  borderRadius: '4px', 
                  backgroundColor: annotation.is_resolved ? '#28a745' : '#ffc107',
                  color: 'white',
                  fontSize: '12px'
                }}>
                  {annotation.is_resolved ? 'Resolved' : 'Open'}
                </span>
              </div>
              {annotation.description && (
                <p style={{ margin: '5px 0', fontSize: '14px', color: '#6c757d' }}>
                  {annotation.description}
                </p>
              )}
              <small style={{ color: '#6c757d' }}>
                By {annotation.user?.full_name} • {new Date(annotation.created_at).toLocaleString()}
              </small>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default AnnotationEditor;