/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

import React, { useEffect, useRef, useState, useCallback } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

function Viewer3D({ gltfUrl, onModelLoaded, onLoadingProgress, onError }) {
  const viewerContainerRef = useRef(null);
  const [scene, setScene] = useState(null);
  const [camera, setCamera] = useState(null);
  const [renderer, setRenderer] = useState(null);
  const [controls, setControls] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState('idle');
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [selectedElement, setSelectedElement] = useState(null);
  const [models, setModels] = useState([]);

  useEffect(() => {
    if (viewerContainerRef.current && !scene) {
      const container = viewerContainerRef.current;
      const width = container.clientWidth;
      const height = container.clientHeight;

      const newScene = new THREE.Scene();
      newScene.background = new THREE.Color(0xf0f0f0);

      const newCamera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
      newCamera.position.set(10, 10, 10);

      const newRenderer = new THREE.WebGLRenderer({ antialias: true });
      newRenderer.setSize(width, height);
      newRenderer.shadowMap.enabled = true;
      newRenderer.shadowMap.type = THREE.PCFSoftShadowMap;
      newRenderer.toneMapping = THREE.ACESFilmicToneMapping;
      newRenderer.toneMappingExposure = 1;
      container.appendChild(newRenderer.domElement);

      const newControls = new OrbitControls(newCamera, newRenderer.domElement);
      newControls.enableDamping = true;
      newControls.dampingFactor = 0.05;
      newControls.screenSpacePanning = false;
      newControls.maxPolarAngle = Math.PI / 2;

      const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
      newScene.add(ambientLight);

      const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
      directionalLight.position.set(10, 10, 5);
      directionalLight.castShadow = true;
      directionalLight.shadow.mapSize.width = 2048;
      directionalLight.shadow.mapSize.height = 2048;
      newScene.add(directionalLight);

      const gridHelper = new THREE.GridHelper(20, 20);
      newScene.add(gridHelper);

      const axesHelper = new THREE.AxesHelper(5);
      newScene.add(axesHelper);

      const raycaster = new THREE.Raycaster();
      const mouse = new THREE.Vector2();

      const handleClick = (event) => {
        const rect = container.getBoundingClientRect();
        mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

        raycaster.setFromCamera(mouse, newCamera);
        const intersects = raycaster.intersectObjects(newScene.children, true);

        if (intersects.length > 0) {
          const clickedObject = intersects[0].object;
          if (clickedObject.userData && clickedObject.userData.elementData) {
            setSelectedElement(clickedObject.userData.elementData);
          }
        } else {
          setSelectedElement(null);
        }
      };

      container.addEventListener('click', handleClick);

      const animate = () => {
        requestAnimationFrame(animate);
        newControls.update();
        newRenderer.render(newScene, newCamera);
      };
      animate();

      const handleResize = () => {
        const width = container.clientWidth;
        const height = container.clientHeight;
        newCamera.aspect = width / height;
        newCamera.updateProjectionMatrix();
        newRenderer.setSize(width, height);
      };
      window.addEventListener('resize', handleResize);

      setScene(newScene);
      setCamera(newCamera);
      setRenderer(newRenderer);
      setControls(newControls);

      return () => {
        container.removeEventListener('click', handleClick);
        window.removeEventListener('resize', handleResize);
        if (newRenderer) {
          container.removeChild(newRenderer.domElement);
          newRenderer.dispose();
        }
      };
    }
  }, [viewerContainerRef.current]);

  const loadGLTFModel = useCallback((url) => {
    if (!scene) return;

    setLoadingStatus('loading');
    setLoadingProgress(0);

    const loader = new GLTFLoader();
    
    loader.load(
      url,
      (gltf) => {
        models.forEach(model => {
          scene.remove(model);
        });
        setModels([]);

        const model = gltf.scene;
        
        model.traverse((child) => {
          if (child.isMesh) {
            child.castShadow = true;
            child.receiveShadow = true;
            
            child.userData.elementData = {
              name: child.name || 'Unnamed Element',
              type: child.material ? child.material.name : 'Unknown',
              id: child.id,
              uuid: child.uuid
            };
            
            if (child.material) {
              child.material.needsUpdate = true;
            }
          }
        });

        scene.add(model);
        setModels([model]);

        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        
        const maxDim = Math.max(size.x, size.y, size.z);
        const fov = camera.fov * (Math.PI / 180);
        let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
        cameraZ *= 1.5;
        
        camera.position.set(center.x, center.y, center.z + cameraZ);
        camera.lookAt(center);
        
        if (controls) {
          controls.target.copy(center);
          controls.update();
        }

        setLoadingStatus('complete');
        setLoadingProgress(100);
        
        if (onModelLoaded) {
          onModelLoaded({
            elementsCount: model.children.length,
            boundingBox: box,
            center: center,
            size: size
          });
        }
      },
      (progress) => {
        const percentage = (progress.loaded / progress.total) * 100;
        setLoadingProgress(percentage);
        if (onLoadingProgress) {
          onLoadingProgress(percentage);
        }
      },
      (error) => {
        console.error('Error loading glTF model:', error);
        setLoadingStatus('error');
        if (onError) {
          onError(`Failed to load 3D model: ${error.message}`);
        }
      }
    );
  }, [scene, camera, controls, models, onModelLoaded, onLoadingProgress, onError]);

  useEffect(() => {
    if (gltfUrl && scene) {
      loadGLTFModel(gltfUrl);
    }
  }, [gltfUrl, scene, loadGLTFModel]);

  const renderLoadingIndicator = () => {
    if (loadingStatus === 'idle' || loadingStatus === 'complete') return null;

    const statusMessages = {
      loading: 'Loading 3D model...',
      error: 'Error loading model'
    };

    return (
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        backgroundColor: 'rgba(255, 255, 255, 0.95)',
        padding: '24px',
        borderRadius: '12px',
        boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
        textAlign: 'center',
        zIndex: 1000,
        minWidth: '250px'
      }}>
        <div style={{ 
          marginBottom: '16px',
          fontSize: '16px',
          fontWeight: '500',
          color: '#333'
        }}>
          {statusMessages[loadingStatus]}
        </div>
        
        {loadingStatus === 'loading' && (
          <>
            <div style={{
              width: '200px',
              height: '6px',
              backgroundColor: '#e0e0e0',
              borderRadius: '3px',
              overflow: 'hidden',
              margin: '0 auto'
            }}>
              <div style={{
                width: `${loadingProgress}%`,
                height: '100%',
                backgroundColor: '#007bff',
                transition: 'width 0.3s ease',
                borderRadius: '3px'
              }} />
            </div>
            
            <div style={{ 
              marginTop: '12px', 
              fontSize: '14px', 
              color: '#666' 
            }}>
              {Math.round(loadingProgress)}%
            </div>
          </>
        )}
        
        {loadingStatus === 'error' && (
          <div style={{
            color: '#dc3545',
            fontSize: '14px',
            marginTop: '8px'
          }}>
            Please check the model file and try again
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
      
      {selectedElement && (
        <div style={{
          position: 'absolute',
          top: '20px',
          right: '20px',
          width: '320px',
          backgroundColor: 'white',
          padding: '20px',
          borderRadius: '12px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
          maxHeight: '400px',
          overflowY: 'auto',
          zIndex: 1000
        }}>
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            marginBottom: '16px'
          }}>
            <h3 style={{ 
              margin: 0,
              fontSize: '18px',
              fontWeight: '600',
              color: '#333'
            }}>
              Element Properties
            </h3>
            <button 
              onClick={() => setSelectedElement(null)}
              style={{ 
                background: 'none', 
                border: 'none', 
                fontSize: '24px',
                cursor: 'pointer',
                color: '#666',
                padding: '0',
                width: '24px',
                height: '24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              ×
            </button>
          </div>
          
          <div style={{ marginBottom: '12px' }}>
            <strong style={{ color: '#555' }}>Name:</strong> 
            <span style={{ marginLeft: '8px' }}>{selectedElement.name || 'N/A'}</span>
          </div>
          
          <div style={{ marginBottom: '12px' }}>
            <strong style={{ color: '#555' }}>Type:</strong> 
            <span style={{ marginLeft: '8px' }}>{selectedElement.type || 'N/A'}</span>
          </div>
          
          <div style={{ marginBottom: '12px' }}>
            <strong style={{ color: '#555' }}>ID:</strong> 
            <span style={{ marginLeft: '8px', fontFamily: 'monospace', fontSize: '12px' }}>
              {selectedElement.uuid || 'N/A'}
            </span>
          </div>
          
          <div style={{
            marginTop: '16px',
            padding: '12px',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px',
            fontSize: '12px',
            color: '#666'
          }}>
            Click on other elements to inspect their properties
          </div>
        </div>
      )}
    </div>
  );
}

export default Viewer3D;
