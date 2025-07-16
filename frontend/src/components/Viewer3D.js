import React, { useEffect, useRef, useState, useCallback } from 'react';
import { IfcViewerAPI } from 'web-ifc-viewer';
import { Color } from 'three';

function Viewer3D({ modelUrl, onModelLoaded, onLoadingProgress, onError }) {
  const viewerContainerRef = useRef(null);
  const [viewer, setViewer] = useState(null);
  const [worker, setWorker] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState('idle');
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [selectedElement, setSelectedElement] = useState(null);

  // Initialize viewer and worker
  useEffect(() => {
    if (viewerContainerRef.current && !viewer) {
      const container = viewerContainerRef.current;
      const newViewer = new IfcViewerAPI({ 
        container, 
        backgroundColor: new Color(0xf0f0f0) 
      });
      
      // Setup viewer
      newViewer.grid.setGrid();
      newViewer.axes.setAxes();
      newViewer.context.renderer.postProduction.active = true;
      
      // Setup lighting
      newViewer.context.ifcCamera.cameraControls.setLookAt(10, 10, 10, 0, 0, 0);
      
      setViewer(newViewer);

      // Initialize Web Worker
      const ifcWorker = new Worker('/workers/ifcLoader.worker.js');
      setWorker(ifcWorker);

      // Setup worker message handler
      ifcWorker.onmessage = (e) => {
        handleWorkerMessage(e, newViewer);
      };

      // Initialize worker
      ifcWorker.postMessage({ type: 'INIT' });

      // Cleanup function
      return () => {
        if (ifcWorker) {
          ifcWorker.terminate();
        }
      };
    }
  }, [viewerContainerRef.current]);

  // Handle worker messages
  const handleWorkerMessage = useCallback((e, viewerInstance) => {
    const { type, data, modelId, progress, geometryData, modelInfo, message } = e.data;

    switch (type) {
      case 'INIT_SUCCESS':
        setLoadingStatus('ready');
        break;

      case 'LOADING_STARTED':
        setLoadingStatus('loading');
        setLoadingProgress(0);
        if (onLoadingProgress) onLoadingProgress(0);
        break;

      case 'MODEL_LOADED':
        setLoadingStatus('processing');
        if (onModelLoaded) onModelLoaded(modelInfo);
        break;

      case 'GEOMETRY_PROGRESS':
        setLoadingProgress(progress);
        if (onLoadingProgress) onLoadingProgress(progress);
        break;

      case 'GEOMETRY_EXTRACTED':
        renderGeometry(geometryData, viewerInstance);
        setLoadingStatus('complete');
        setLoadingProgress(1);
        if (onLoadingProgress) onLoadingProgress(1);
        break;

      case 'ELEMENT_PROPERTIES':
        setSelectedElement(data.properties);
        break;

      case 'ERROR':
        setLoadingStatus('error');
        console.error('IFC Worker Error:', message);
        if (onError) onError(message);
        break;

      default:
        console.warn('Unknown worker message type:', type);
    }
  }, [onModelLoaded, onLoadingProgress, onError]);

  // Render geometry from worker
  const renderGeometry = useCallback((geometryData, viewerInstance) => {
    try {
      // Clear existing geometry
      viewerInstance.context.scene.remove(...viewerInstance.context.scene.children);

      // Create meshes from geometry data
      geometryData.objects.forEach((obj, index) => {
        if (obj.vertices.length > 0 && obj.indices.length > 0) {
          const geometry = new THREE.BufferGeometry();
          
          // Set vertices
          const vertices = new Float32Array(obj.vertices);
          geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
          
          // Set indices
          geometry.setIndex(obj.indices);
          
          // Compute normals
          geometry.computeVertexNormals();
          
          // Create material
          const material = new THREE.MeshLambertMaterial({
            color: new THREE.Color(obj.color[0], obj.color[1], obj.color[2]),
            transparent: true,
            opacity: 0.8
          });
          
          // Create mesh
          const mesh = new THREE.Mesh(geometry, material);
          mesh.userData = {
            id: obj.id,
            type: obj.type,
            globalId: obj.globalId,
            name: obj.name
          };
          
          // Add click handler
          mesh.addEventListener('click', () => {
            handleElementClick(obj.id, obj.globalId);
          });
          
          viewerInstance.context.scene.add(mesh);
        }
      });

      // Fit camera to model
      viewerInstance.context.ifcCamera.cameraControls.fitToBox(
        viewerInstance.context.scene, 
        true
      );

    } catch (error) {
      console.error('Error rendering geometry:', error);
      if (onError) onError(`Rendering error: ${error.message}`);
    }
  }, [onError]);

  // Handle element click
  const handleElementClick = useCallback((elementId, globalId) => {
    if (worker) {
      worker.postMessage({
        type: 'GET_ELEMENT_PROPERTIES',
        data: {
          modelID: 0, // Assuming single model for now
          elementID: elementId,
          modelId: 'current'
        }
      });
    }
  }, [worker]);

  // Load model when URL changes
  useEffect(() => {
    if (modelUrl && worker && loadingStatus === 'ready') {
      loadModel(modelUrl);
    }
  }, [modelUrl, worker, loadingStatus]);

  const loadModel = async (url) => {
    try {
      setLoadingStatus('fetching');
      
      // Fetch model data
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to fetch model: ${response.statusText}`);
      }
      
      const arrayBuffer = await response.arrayBuffer();
      const uint8Array = new Uint8Array(arrayBuffer);
      
      // Send to worker
      worker.postMessage({
        type: 'LOAD_MODEL',
        data: {
          modelData: uint8Array,
          modelId: 'current'
        }
      });
      
    } catch (error) {
      console.error('Error loading model:', error);
      setLoadingStatus('error');
      if (onError) onError(`Loading error: ${error.message}`);
    }
  };

  // Render loading indicator
  const renderLoadingIndicator = () => {
    if (loadingStatus === 'idle' || loadingStatus === 'ready') return null;

    const statusMessages = {
      fetching: 'Fetching model...',
      loading: 'Loading IFC model...',
      processing: 'Processing model data...',
      error: 'Error loading model'
    };

    return (
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        padding: '20px',
        borderRadius: '8px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        textAlign: 'center',
        zIndex: 1000
      }}>
        <div style={{ marginBottom: '10px' }}>
          {statusMessages[loadingStatus]}
        </div>
        
        {loadingStatus !== 'error' && (
          <div style={{
            width: '200px',
            height: '4px',
            backgroundColor: '#e0e0e0',
            borderRadius: '2px',
            overflow: 'hidden'
          }}>
            <div style={{
              width: `${loadingProgress * 100}%`,
              height: '100%',
              backgroundColor: '#007bff',
              transition: 'width 0.3s ease'
            }} />
          </div>
        )}
        
        {loadingStatus !== 'error' && (
          <div style={{ marginTop: '10px', fontSize: '12px', color: '#666' }}>
            {Math.round(loadingProgress * 100)}%
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={{ width: '100%', height: '600px', position: 'relative' }}>
      <div 
        ref={viewerContainerRef} 
        style={{ width: '100%', height: '100%' }}
      />
      
      {renderLoadingIndicator()}
      
      {/* Element properties panel */}
      {selectedElement && (
        <div style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          width: '300px',
          backgroundColor: 'white',
          padding: '15px',
          borderRadius: '8px',
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
          maxHeight: '400px',
          overflowY: 'auto',
          zIndex: 1000
        }}>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: '10px'
          }}>
            <h3 style={{ margin: 0 }}>Element Properties</h3>
            <button 
              onClick={() => setSelectedElement(null)}
              style={{ 
                background: 'none', 
                border: 'none', 
                fontSize: '20px',
                cursor: 'pointer'
              }}
            >
              ×
            </button>
          </div>
          
          <div><strong>Name:</strong> {selectedElement.name || 'N/A'}</div>
          <div><strong>Type:</strong> {selectedElement.type || 'N/A'}</div>
          <div><strong>Global ID:</strong> {selectedElement.globalId || 'N/A'}</div>
          
          {selectedElement.description && (
            <div><strong>Description:</strong> {selectedElement.description}</div>
          )}
          
          {Object.keys(selectedElement.properties).length > 0 && (
            <div style={{ marginTop: '15px' }}>
              <strong>Properties:</strong>
              {Object.entries(selectedElement.properties).map(([setName, props]) => (
                <div key={setName} style={{ marginTop: '10px' }}>
                  <div style={{ fontWeight: 'bold', fontSize: '14px' }}>{setName}:</div>
                  {Object.entries(props).map(([propName, propValue]) => (
                    <div key={propName} style={{ marginLeft: '10px', fontSize: '12px' }}>
                      {propName}: {propValue}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Viewer3D;
