/* eslint-disable no-restricted-globals */
import { IfcAPI } from 'web-ifc/web-ifc-api';

class IFCLoaderWorker {
  constructor() {
    this.ifcAPI = new IfcAPI();
    this.ifcAPI.SetWasmPath('/wasm/');
    this.models = new Map();
  }

  async init() {
    try {
      await this.ifcAPI.Init();
      self.postMessage({ type: 'INIT_SUCCESS' });
    } catch (error) {
      self.postMessage({ 
        type: 'ERROR', 
        message: `Failed to initialize IFC API: ${error.message}` 
      });
    }
  }

  async loadModel(modelData, modelId) {
    try {
      self.postMessage({ type: 'LOADING_STARTED', modelId });

      // Open IFC model
      const model = await this.ifcAPI.OpenModel(modelData);
      this.models.set(modelId, model);

      // Get model info
      const modelInfo = {
        modelID: model,
        name: await this.getModelName(model),
        schema: await this.getModelSchema(model),
        units: await this.getModelUnits(model)
      };

      self.postMessage({ 
        type: 'MODEL_LOADED', 
        modelId,
        modelInfo 
      });

      // Extract geometry progressively
      await this.extractGeometry(model, modelId);

    } catch (error) {
      self.postMessage({ 
        type: 'ERROR', 
        modelId,
        message: `Failed to load model: ${error.message}` 
      });
    }
  }

  async getModelName(modelID) {
    try {
      const projects = await this.ifcAPI.GetLineIDsWithType(modelID, this.ifcAPI.IFCPROJECT);
      if (projects.size() > 0) {
        const projectID = projects.get(0);
        const project = await this.ifcAPI.GetLine(modelID, projectID);
        return project.Name?.value || 'Unnamed Project';
      }
      return 'Unknown Project';
    } catch (error) {
      return 'Unknown Project';
    }
  }

  async getModelSchema(modelID) {
    try {
      const header = await this.ifcAPI.GetHeaderLine(modelID, 0);
      return header.schema || 'IFC4';
    } catch (error) {
      return 'IFC4';
    }
  }

  async getModelUnits(modelID) {
    try {
      const units = await this.ifcAPI.GetLineIDsWithType(modelID, this.ifcAPI.IFCUNITASSIGNMENT);
      if (units.size() > 0) {
        const unitID = units.get(0);
        const unit = await this.ifcAPI.GetLine(modelID, unitID);
        return unit.Units?.[0]?.Name?.value || 'METRE';
      }
      return 'METRE';
    } catch (error) {
      return 'METRE';
    }
  }

  async extractGeometry(modelID, modelId) {
    try {
      const allElements = await this.ifcAPI.GetAllLines(modelID);
      const totalElements = allElements.size();
      let processedElements = 0;

      const geometryData = {
        vertices: [],
        indices: [],
        normals: [],
        colors: [],
        materials: [],
        objects: []
      };

      // Process elements in batches to prevent blocking
      const batchSize = 100;
      for (let i = 0; i < totalElements; i += batchSize) {
        const batch = [];
        
        for (let j = i; j < Math.min(i + batchSize, totalElements); j++) {
          const elementID = allElements.get(j);
          
          try {
            const element = await this.ifcAPI.GetLine(modelID, elementID);
            
            if (this.hasGeometry(element)) {
              const geometry = await this.ifcAPI.GetGeometry(modelID, elementID);
              
              if (geometry && geometry.GetVertexDataSize() > 0) {
                const vertexData = this.ifcAPI.GetVertexArray(
                  geometry.GetVertexData(),
                  geometry.GetVertexDataSize()
                );
                
                const indexData = this.ifcAPI.GetIndexArray(
                  geometry.GetIndexData(),
                  geometry.GetIndexDataSize()
                );

                batch.push({
                  id: elementID,
                  type: element.constructor.name,
                  globalId: element.GlobalId?.value,
                  name: element.Name?.value,
                  vertices: Array.from(vertexData),
                  indices: Array.from(indexData),
                  color: this.getElementColor(element),
                  material: this.getElementMaterial(element)
                });
              }
            }
          } catch (elementError) {
            // Skip problematic elements
            continue;
          }
        }

        if (batch.length > 0) {
          geometryData.objects.push(...batch);
        }

        processedElements += batchSize;
        
        // Report progress
        self.postMessage({
          type: 'GEOMETRY_PROGRESS',
          modelId,
          progress: Math.min(processedElements / totalElements, 1),
          processed: processedElements,
          total: totalElements
        });

        // Yield control to prevent blocking
        await new Promise(resolve => setTimeout(resolve, 0));
      }

      self.postMessage({
        type: 'GEOMETRY_EXTRACTED',
        modelId,
        geometryData
      });

    } catch (error) {
      self.postMessage({
        type: 'ERROR',
        modelId,
        message: `Failed to extract geometry: ${error.message}`
      });
    }
  }

  hasGeometry(element) {
    return element.Representation && 
           element.Representation.Representations &&
           element.Representation.Representations.length > 0;
  }

  getElementColor(element) {
    // Default colors based on element type
    const typeColors = {
      'IfcWall': [0.8, 0.8, 0.8],
      'IfcSlab': [0.7, 0.7, 0.7],
      'IfcBeam': [0.8, 0.4, 0.2],
      'IfcColumn': [0.6, 0.6, 0.8],
      'IfcDoor': [0.8, 0.6, 0.4],
      'IfcWindow': [0.4, 0.6, 0.8],
      'IfcRoof': [0.6, 0.3, 0.2],
      'IfcStair': [0.7, 0.7, 0.5]
    };

    const elementType = element.constructor.name;
    return typeColors[elementType] || [0.5, 0.5, 0.5];
  }

  getElementMaterial(element) {
    return {
      ambient: [0.2, 0.2, 0.2],
      diffuse: this.getElementColor(element),
      specular: [0.1, 0.1, 0.1],
      shininess: 30
    };
  }

  async getElementProperties(modelID, elementID) {
    try {
      const element = await this.ifcAPI.GetLine(modelID, elementID);
      const properties = {
        globalId: element.GlobalId?.value,
        name: element.Name?.value,
        description: element.Description?.value,
        type: element.constructor.name,
        properties: {}
      };

      // Extract property sets
      if (element.IsDefinedBy) {
        for (const rel of element.IsDefinedBy) {
          if (rel.constructor.name === 'IfcRelDefinesByProperties') {
            const propSet = rel.RelatingPropertyDefinition;
            if (propSet && propSet.HasProperties) {
              properties.properties[propSet.Name?.value || 'Properties'] = {};
              
              for (const prop of propSet.HasProperties) {
                if (prop.NominalValue) {
                  properties.properties[propSet.Name?.value || 'Properties'][prop.Name?.value] = 
                    prop.NominalValue.value;
                }
              }
            }
          }
        }
      }

      return properties;
    } catch (error) {
      return {
        globalId: null,
        name: 'Unknown',
        description: null,
        type: 'Unknown',
        properties: {}
      };
    }
  }

  async closeModel(modelId) {
    try {
      const modelID = this.models.get(modelId);
      if (modelID !== undefined) {
        await this.ifcAPI.CloseModel(modelID);
        this.models.delete(modelId);
        
        self.postMessage({
          type: 'MODEL_CLOSED',
          modelId
        });
      }
    } catch (error) {
      self.postMessage({
        type: 'ERROR',
        modelId,
        message: `Failed to close model: ${error.message}`
      });
    }
  }
}

// Worker message handler
const worker = new IFCLoaderWorker();

self.onmessage = async function(e) {
  const { type, data } = e.data;

  switch (type) {
    case 'INIT':
      await worker.init();
      break;
      
    case 'LOAD_MODEL':
      await worker.loadModel(data.modelData, data.modelId);
      break;
      
    case 'GET_ELEMENT_PROPERTIES':
      const properties = await worker.getElementProperties(data.modelID, data.elementID);
      self.postMessage({
        type: 'ELEMENT_PROPERTIES',
        modelId: data.modelId,
        elementID: data.elementID,
        properties
      });
      break;
      
    case 'CLOSE_MODEL':
      await worker.closeModel(data.modelId);
      break;
      
    default:
      self.postMessage({
        type: 'ERROR',
        message: `Unknown message type: ${type}`
      });
  }
};