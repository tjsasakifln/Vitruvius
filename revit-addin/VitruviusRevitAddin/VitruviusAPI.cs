// Production use requires a separate commercial license from the Licensor.
// For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

using System;
using System.IO;
using System.Net.Http;
using System.Threading.Tasks;
using System.Configuration;
using Newtonsoft.Json;
using System.Text;

namespace VitruviusRevitAddin
{
    /// <summary>
    /// API client for communicating with Vitruvius backend
    /// </summary>
    public class VitruviusAPI
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;
        private readonly string _apiKey;

        public VitruviusAPI()
        {
            _httpClient = new HttpClient();
            _httpClient.Timeout = TimeSpan.FromMinutes(10); // Allow for large file uploads
            
            // Get configuration from settings (you can also use config file or registry)
            _baseUrl = GetSetting("VitruviusApiUrl", "https://localhost:8000/api/v1");
            _apiKey = GetSetting("VitruviusApiKey", "");
            
            // Set default headers
            _httpClient.DefaultRequestHeaders.Add("User-Agent", "VitruviusRevitAddin/1.0");
            if (!string.IsNullOrEmpty(_apiKey))
            {
                _httpClient.DefaultRequestHeaders.Add("Authorization", $"Bearer {_apiKey}");
            }
        }

        /// <summary>
        /// Upload a model to Vitruvius
        /// </summary>
        public async Task<UploadResult> UploadModelAsync(string ifcPath, ProjectInfo projectInfo, Action<double> progressCallback = null)
        {
            try
            {
                // First, create or get the project
                var project = await CreateOrGetProjectAsync(projectInfo);
                if (project == null)
                {
                    return new UploadResult
                    {
                        Success = false,
                        ErrorMessage = "Failed to create or get project"
                    };
                }

                // Upload the IFC file
                using (var formData = new MultipartFormDataContent())
                {
                    // Add file content
                    var fileContent = new ByteArrayContent(File.ReadAllBytes(ifcPath));
                    fileContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/octet-stream");
                    formData.Add(fileContent, "file", Path.GetFileName(ifcPath));

                    // Add project metadata
                    formData.Add(new StringContent(JsonConvert.SerializeObject(new
                    {
                        project_name = projectInfo.ProjectName,
                        project_number = projectInfo.ProjectNumber,
                        document_name = projectInfo.DocumentName,
                        revit_version = projectInfo.RevitVersion,
                        total_elements = projectInfo.TotalElements,
                        level_count = projectInfo.LevelCount,
                        view_count = projectInfo.ViewCount
                    })), "metadata");

                    // Upload with progress tracking
                    var response = await UploadWithProgressAsync(
                        $"{_baseUrl}/projects/{project.Id}/upload-ifc",
                        formData,
                        progressCallback);

                    if (response.IsSuccessStatusCode)
                    {
                        var responseContent = await response.Content.ReadAsStringAsync();
                        var uploadResponse = JsonConvert.DeserializeObject<UploadResponse>(responseContent);
                        
                        return new UploadResult
                        {
                            Success = true,
                            UploadId = uploadResponse.TaskId,
                            ProjectId = project.Id
                        };
                    }
                    else
                    {
                        var errorContent = await response.Content.ReadAsStringAsync();
                        return new UploadResult
                        {
                            Success = false,
                            ErrorMessage = $"HTTP {response.StatusCode}: {errorContent}"
                        };
                    }
                }
            }
            catch (Exception ex)
            {
                return new UploadResult
                {
                    Success = false,
                    ErrorMessage = ex.Message
                };
            }
        }

        /// <summary>
        /// Create or get a project
        /// </summary>
        private async Task<ProjectResponse> CreateOrGetProjectAsync(ProjectInfo projectInfo)
        {
            try
            {
                // First, try to get existing project by name
                var getResponse = await _httpClient.GetAsync($"_baseUrl}/projects?name={Uri.EscapeDataString(projectInfo.ProjectName)}");
                
                if (getResponse.IsSuccessStatusCode)
                {
                    var getContent = await getResponse.Content.ReadAsStringAsync();
                    var existingProjects = JsonConvert.DeserializeObject<ProjectResponse[]>(getContent);
                    
                    if (existingProjects != null && existingProjects.Length > 0)
                    {
                        return existingProjects[0];
                    }
                }

                // Create new project
                var createData = new
                {
                    name = projectInfo.ProjectName,
                    description = $"Project imported from Revit: {projectInfo.DocumentName}",
                    project_number = projectInfo.ProjectNumber,
                    client_name = projectInfo.ClientName,
                    project_address = projectInfo.ProjectAddress,
                    project_status = projectInfo.ProjectStatus
                };

                var json = JsonConvert.SerializeObject(createData);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                
                var createResponse = await _httpClient.PostAsync($"_baseUrl}/projects/", content);
                
                if (createResponse.IsSuccessStatusCode)
                {
                    var createContent = await createResponse.Content.ReadAsStringAsync();
                    return JsonConvert.DeserializeObject<ProjectResponse>(createContent);
                }
                
                return null;
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Error creating/getting project: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Upload with progress tracking
        /// </summary>
        private async Task<HttpResponseMessage> UploadWithProgressAsync(string url, MultipartFormDataContent content, Action<double> progressCallback)
        {
            // For simplicity, we'll use a basic approach here
            // In a production environment, you might want to implement more sophisticated progress tracking
            progressCallback?.Invoke(0.0);
            
            var response = await _httpClient.PostAsync(url, content);
            
            progressCallback?.Invoke(1.0);
            
            return response;
        }

        /// <summary>
        /// Get the URL for viewing a project in the web interface
        /// </summary>
        public string GetProjectUrl(int projectId)
        {
            string webUrl = GetSetting("VitruviusWebUrl", "https://localhost:3000");
            return $"{webUrl}/projects/{projectId}";
        }

        /// <summary>
        /// Get a setting value
        /// </summary>
        private string GetSetting(string key, string defaultValue)
        {
            try
            {
                // Try to get from app.config or user settings
                // For now, we'll use hardcoded values, but in production you'd want to use
                // ConfigurationManager.AppSettings or similar
                return defaultValue;
            }
            catch
            {
                return defaultValue;
            }
        }

        /// <summary>
        /// Dispose of resources
        /// </summary>
        public void Dispose()
        {
            _httpClient?.Dispose();
        }
    }

    /// <summary>
    /// Response from project API
    /// </summary>
    public class ProjectResponse
    {
        public int Id { get; set; }
        public string Name { get; set; }
        public string Status { get; set; }
    }

    /// <summary>
    /// Response from upload API
    /// </summary>
    public class UploadResponse
    {
        public string Message { get; set; }
        public string TaskId { get; set; }
        public int ModelId { get; set; }
        public string FilePath { get; set; }
    }
}
