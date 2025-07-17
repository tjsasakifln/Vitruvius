# Production use requires a separate commercial license from the Licensor.
# For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

import os
import tempfile
import shutil
import resource
import signal
import multiprocessing
from contextlib import contextmanager
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ProcessingTimeoutError(Exception):
    """Raised when processing exceeds timeout limit"""
    pass


class SandboxProcessor:
    """
    Secure sandbox processor for IFC files with resource limits and isolation
    """
    
    def __init__(self, 
                 max_memory_mb: int = 512,
                 max_cpu_time_seconds: int = 300,
                 max_file_size_mb: int = 50,
                 temp_dir: Optional[str] = None):
        """
        Initialize sandbox processor with resource limits
        
        Args:
            max_memory_mb: Maximum memory usage in MB
            max_cpu_time_seconds: Maximum CPU time in seconds
            max_file_size_mb: Maximum file size in MB
            temp_dir: Custom temporary directory
        """
        self.max_memory_mb = max_memory_mb
        self.max_cpu_time_seconds = max_cpu_time_seconds
        self.max_file_size_mb = max_file_size_mb
        self.temp_dir = temp_dir or tempfile.gettempdir()
        
    def set_resource_limits(self):
        """Set resource limits for the current process"""
        try:
            # Set memory limit (in bytes)
            memory_limit = self.max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
            
            # Set CPU time limit (in seconds)
            resource.setrlimit(resource.RLIMIT_CPU, (self.max_cpu_time_seconds, self.max_cpu_time_seconds))
            
            # Set file size limit (in bytes)
            file_size_limit = self.max_file_size_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_FSIZE, (file_size_limit, file_size_limit))
            
            # Disable core dumps
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            
        except Exception as e:
            logger.warning(f"Failed to set resource limits: {e}")
    
    @contextmanager
    def isolated_temp_directory(self):
        """Create an isolated temporary directory for processing"""
        temp_dir = tempfile.mkdtemp(prefix="vitruvius_sandbox_", dir=self.temp_dir)
        try:
            # Set restrictive permissions
            os.chmod(temp_dir, 0o700)
            yield temp_dir
        finally:
            # Clean up temporary directory
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
    
    def timeout_handler(self, signum, frame):
        """Handle timeout signal"""
        raise ProcessingTimeoutError("Processing timeout exceeded")
    
    def process_ifc_file_sandboxed(self, file_path: str, output_path: str) -> Dict[str, Any]:
        """
        Process IFC file in a sandboxed environment with resource limits
        
        Args:
            file_path: Path to the input IFC file
            output_path: Path for output files
            
        Returns:
            Processing results or error information
        """
        def worker_process(file_path: str, output_path: str, result_queue: multiprocessing.Queue):
            """Worker process that runs with resource limits"""
            try:
                # Set resource limits
                self.set_resource_limits()
                
                # Set up timeout handler
                signal.signal(signal.SIGALRM, self.timeout_handler)
                signal.alarm(self.max_cpu_time_seconds)
                
                # Import ifcopenshell here to avoid loading it in main process
                import ifcopenshell
                import ifcopenshell.geom
                
                # Validate file exists and is readable
                if not os.path.exists(file_path) or not os.access(file_path, os.R_OK):
                    result_queue.put({"error": "File not accessible"})
                    return
                
                # Check file size
                file_size = os.path.getsize(file_path)
                if file_size > self.max_file_size_mb * 1024 * 1024:
                    result_queue.put({"error": f"File too large: {file_size} bytes"})
                    return
                
                # Process the IFC file
                try:
                    ifc_file = ifcopenshell.open(file_path)
                    
                    # Basic validation
                    if not ifc_file:
                        result_queue.put({"error": "Failed to open IFC file"})
                        return
                    
                    # Get basic model info
                    model_info = {
                        "schema": ifc_file.schema,
                        "total_elements": len(list(ifc_file.by_type("IfcRoot"))),
                        "file_size": file_size
                    }
                    
                    # Limit the number of elements processed
                    MAX_ELEMENTS = 50000
                    if model_info["total_elements"] > MAX_ELEMENTS:
                        result_queue.put({"error": f"Too many elements: {model_info['total_elements']} (max: {MAX_ELEMENTS})"})
                        return
                    
                    # Process elements with geometry
                    settings = ifcopenshell.geom.settings()
                    settings.set(settings.USE_WORLD_COORDS, True)
                    
                    elements = []
                    iterator = ifcopenshell.geom.iterator(settings, ifc_file)
                    
                    element_count = 0
                    if iterator.initialize():
                        while True:
                            try:
                                shape = iterator.get()
                                element = ifc_file.by_id(shape.id)
                                
                                elements.append({
                                    "global_id": element.GlobalId,
                                    "type": element.is_a(),
                                    "name": getattr(element, 'Name', '') or '',
                                    "has_geometry": True
                                })
                                
                                element_count += 1
                                if element_count >= MAX_ELEMENTS:
                                    break
                                    
                                if not iterator.next():
                                    break
                                    
                            except Exception as e:
                                logger.warning(f"Error processing element: {e}")
                                continue
                    
                    result = {
                        "processed": True,
                        "model_info": model_info,
                        "elements": elements,
                        "elements_with_geometry": len(elements)
                    }
                    
                    result_queue.put(result)
                    
                except Exception as e:
                    result_queue.put({"error": f"IFC processing error: {str(e)}"})
                    
            except ProcessingTimeoutError:
                result_queue.put({"error": "Processing timeout exceeded"})
            except MemoryError:
                result_queue.put({"error": "Memory limit exceeded"})
            except Exception as e:
                result_queue.put({"error": f"Unexpected error: {str(e)}"})
        
        # Create a queue for results
        result_queue = multiprocessing.Queue()
        
        # Start worker process
        worker = multiprocessing.Process(
            target=worker_process,
            args=(file_path, output_path, result_queue)
        )
        
        try:
            worker.start()
            
            # Wait for completion with timeout
            worker.join(timeout=self.max_cpu_time_seconds + 30)  # Extra time for cleanup
            
            if worker.is_alive():
                # Force terminate if still running
                worker.terminate()
                worker.join(timeout=5)
                if worker.is_alive():
                    worker.kill()
                    worker.join()
                return {"error": "Processing forcibly terminated due to timeout"}
            
            # Get result from queue
            if not result_queue.empty():
                return result_queue.get()
            else:
                return {"error": "No result returned from worker process"}
                
        except Exception as e:
            if worker.is_alive():
                worker.terminate()
                worker.join()
            return {"error": f"Sandbox processing error: {str(e)}"}


def create_sandbox_processor() -> SandboxProcessor:
    """
    Create a configured sandbox processor with default security settings
    
    Returns:
        Configured SandboxProcessor instance
    """
    return SandboxProcessor(
        max_memory_mb=512,      # 512MB memory limit
        max_cpu_time_seconds=300,  # 5 minutes CPU time limit
        max_file_size_mb=50     # 50MB file size limit
    )