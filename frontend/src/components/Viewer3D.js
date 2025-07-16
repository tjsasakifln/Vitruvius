import React, { useEffect, useRef } from 'react';
import { IfcViewerAPI } from 'web-ifc-viewer';
import { Color } from 'three';

function Viewer3D() {
  const viewerContainerRef = useRef(null);

  useEffect(() => {
    if (viewerContainerRef.current) {
      const container = viewerContainerRef.current;
      const viewer = new IfcViewerAPI({ container, backgroundColor: new Color(0xffffff) });
      viewer.grid.setGrid();
      viewer.axes.setAxes();

      async function loadIfc() {
        // This is a placeholder. In a real app, you would load a file
        // selected by the user, perhaps from the UploadForm component.
        // await viewer.IFC.loadIfcUrl('/path/to/your/model.ifc');
        console.log('IFC Viewer initialized. Ready to load models.');
      }

      loadIfc();
    }
  }, []);

  return <div ref={viewerContainerRef} style={{ width: '100%', height: '600px', position: 'relative' }} />;
}

export default Viewer3D;
