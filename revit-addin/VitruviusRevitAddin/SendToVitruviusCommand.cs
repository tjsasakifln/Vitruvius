// Production use requires a separate commercial license from the Licensor.
// For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

using System;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace VitruviusRevitAddin
{
    /// <summary>
    /// Command to send Revit model to Vitruvius for clash detection
    /// </summary>
    [Transaction(TransactionMode.Manual)]
    [Regeneration(RegenerationOption.Manual)]
    public class SendToVitruviusCommand : IExternalCommand
    {
        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            try
            {
                // Get the current document
                Document doc = commandData.Application.ActiveUIDocument.Document;
                
                if (doc == null)
                {
                    TaskDialog.Show("Error", "No active document found.");
                    return Result.Failed;
                }

                // Check if document is saved
                if (!doc.IsWorkshared && string.IsNullOrEmpty(doc.PathName))
                {
                    TaskDialog.Show("Save Required", "Please save the document before sending to Vitruvius.");
                    return Result.Failed;
                }

                // Show progress dialog
                using (var progressForm = new ProgressForm("Sending to Vitruvius"))
                {
                    progressForm.Show();
                    progressForm.UpdateProgress(0, "Preparing model for export...");

                    // Step 1: Export to IFC
                    string ifcPath = null;
                    try
                    {
                        progressForm.UpdateProgress(20, "Exporting to IFC format...");
                        ifcPath = ExportToIFC(doc);
                        
                        if (string.IsNullOrEmpty(ifcPath) || !File.Exists(ifcPath))
                        {
                            throw new Exception("Failed to export IFC file");
                        }
                    }
                    catch (Exception ex)
                    {
                        progressForm.Hide();
                        TaskDialog.Show("Export Error", $"Failed to export model to IFC: {ex.Message}");
                        return Result.Failed;
                    }

                    // Step 2: Get project information
                    progressForm.UpdateProgress(40, "Gathering project information...");
                    var projectInfo = GetProjectInfo(doc);

                    // Step 3: Upload to Vitruvius
                    progressForm.UpdateProgress(60, "Uploading to Vitruvius...");
                    try
                    {
                        var uploadResult = UploadToVitruvius(ifcPath, projectInfo, progressForm);
                        
                        if (uploadResult.Success)
                        {
                            progressForm.UpdateProgress(100, "Upload complete!");
                            progressForm.Hide();
                            
                            // Show success message with option to view results
                            var result = MessageBox.Show(
                                $"Model successfully sent to Vitruvius!\n\n" +
                                $"Project: {projectInfo.ProjectName}\n" +
                                $"Upload ID: {uploadResult.UploadId}\n\n" +
                                $"Would you like to view the results in your browser?",
                                "Success",
                                MessageBoxButtons.YesNo,
                                MessageBoxIcon.Information);

                            if (result == DialogResult.Yes)
                            {
                                OpenVitruviusWebInterface(uploadResult.ProjectId);
                            }
                        }
                        else
                        {
                            progressForm.Hide();
                            TaskDialog.Show("Upload Error", $"Failed to upload model to Vitruvius: {uploadResult.ErrorMessage}");
                            return Result.Failed;
                        }
                    }
                    catch (Exception ex)
                    {
                        progressForm.Hide();
                        TaskDialog.Show("Upload Error", $"Failed to upload model to Vitruvius: {ex.Message}");
                        return Result.Failed;
                    }
                    finally
                    {
                        // Clean up temporary IFC file
                        if (File.Exists(ifcPath))
                        {
                            try
                            {
                                File.Delete(ifcPath);
                            }
                            catch
                            {
                                // Ignore cleanup errors
                            }
                        }
                    }
                }

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                TaskDialog.Show("Error", $"An unexpected error occurred: {ex.Message}");
                return Result.Failed;
            }
        }

        /// <summary>
        /// Export the Revit model to IFC format
        /// </summary>
        private string ExportToIFC(Document doc)
        {
            // Create temporary file path
            string tempDir = Path.GetTempPath();
            string fileName = Path.GetFileNameWithoutExtension(doc.PathName);
            if (string.IsNullOrEmpty(fileName))
            {
                fileName = "RevitModel";
            }
            string ifcPath = Path.Combine(tempDir, $"{fileName}_{DateTime.Now:yyyyMMdd_HHmmss}.ifc");

            // Configure IFC export options
            var exportOptions = new IFCExportOptions();
            exportOptions.ExportBaseQuantities = true;
            exportOptions.WallAndColumnSplitting = true;
            exportOptions.SpaceBoundaryLevel = 2;
            exportOptions.FileVersion = IFCVersion.IFC2x3CV2;
            exportOptions.ExportInternalRevitPropertySets = true;
            exportOptions.ExportIFCCommonPropertySets = true;
            exportOptions.Export2DElements = false;
            exportOptions.ExportPartsAsBuildingElements = false;
            exportOptions.ExportBoundingBox = false;
            exportOptions.ExportSolidModelRep = false;
            exportOptions.ExportSchedulesAsTabs = false;
            exportOptions.ExportUserDefinedPsets = false;
            exportOptions.ExportLinkedFiles = false;
            exportOptions.IncludeSiteElevation = false;
            exportOptions.UseActiveViewGeometry = false;
            exportOptions.ExportSpecificSchedules = false;

            // Perform the export
            var transaction = new Transaction(doc, "Export to IFC");
            transaction.Start();
            
            try
            {
                doc.Export(Path.GetDirectoryName(ifcPath), Path.GetFileName(ifcPath), exportOptions);
                transaction.Commit();
                return ifcPath;
            }
            catch (Exception ex)
            {
                transaction.RollBack();
                throw new Exception($"IFC export failed: {ex.Message}");
            }
        }

        /// <summary>
        /// Get project information from the Revit document
        /// </summary>
        private ProjectInfo GetProjectInfo(Document doc)
        {
            var projectInfo = new ProjectInfo();
            
            // Get project information
            var projectInfoElement = doc.ProjectInformation;
            if (projectInfoElement != null)
            {
                projectInfo.ProjectName = projectInfoElement.Name ?? "Unnamed Project";
                projectInfo.ProjectNumber = projectInfoElement.Number ?? "";
                projectInfo.ProjectAddress = projectInfoElement.Address ?? "";
                projectInfo.ClientName = projectInfoElement.ClientName ?? "";
                projectInfo.ProjectStatus = projectInfoElement.Status ?? "";
            }
            
            // Get document information
            projectInfo.DocumentName = Path.GetFileNameWithoutExtension(doc.PathName) ?? "Unnamed Document";
            projectInfo.DocumentPath = doc.PathName ?? "";
            projectInfo.IsWorkshared = doc.IsWorkshared;
            projectInfo.RevitVersion = doc.Application.VersionNumber;
            
            // Get model statistics
            var collector = new FilteredElementCollector(doc);
            projectInfo.TotalElements = collector.GetElementCount();
            
            // Get level information
            var levelCollector = new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Levels)
                .WhereElementIsNotElementType();
            projectInfo.LevelCount = levelCollector.GetElementCount();
            
            // Get view information
            var viewCollector = new FilteredElementCollector(doc)
                .OfCategory(BuiltInCategory.OST_Views)
                .WhereElementIsNotElementType();
            projectInfo.ViewCount = viewCollector.GetElementCount();
            
            return projectInfo;
        }

        /// <summary>
        /// Upload the IFC file to Vitruvius
        /// </summary>
        private UploadResult UploadToVitruvius(string ifcPath, ProjectInfo projectInfo, ProgressForm progressForm)
        {
            var vitruviusApi = new VitruviusAPI();
            
            // Update progress
            progressForm.UpdateProgress(70, "Connecting to Vitruvius...");
            
            // Upload the file
            var uploadTask = vitruviusApi.UploadModelAsync(ifcPath, projectInfo, 
                (progress) => progressForm.UpdateProgress(70 + (int)(progress * 0.3), "Uploading model..."));
            
            return uploadTask.Result;
        }

        /// <summary>
        /// Open the Vitruvius web interface in the default browser
        /// </summary>
        private void OpenVitruviusWebInterface(int projectId)
        {
            try
            {
                var vitruviusApi = new VitruviusAPI();
                string url = vitruviusApi.GetProjectUrl(projectId);
                System.Diagnostics.Process.Start(url);
            }
            catch (Exception ex)
            {
                TaskDialog.Show("Error", $"Failed to open web interface: {ex.Message}");
            }
        }
    }

    /// <summary>
    /// Container for project information
    /// </summary>
    public class ProjectInfo
    {
        public string ProjectName { get; set; }
        public string ProjectNumber { get; set; }
        public string ProjectAddress { get; set; }
        public string ClientName { get; set; }
        public string ProjectStatus { get; set; }
        public string DocumentName { get; set; }
        public string DocumentPath { get; set; }
        public bool IsWorkshared { get; set; }
        public string RevitVersion { get; set; }
        public int TotalElements { get; set; }
        public int LevelCount { get; set; }
        public int ViewCount { get; set; }
    }

    /// <summary>
    /// Result of the upload operation
    /// </summary>
    public class UploadResult
    {
        public bool Success { get; set; }
        public string UploadId { get; set; }
        public int ProjectId { get; set; }
        public string ErrorMessage { get; set; }
    }

    /// <summary>
    /// Simple progress form for showing upload progress
    /// </summary>
    public class ProgressForm : System.Windows.Forms.Form
    {
        private ProgressBar progressBar;
        private Label statusLabel;

        public ProgressForm(string title)
        {
            InitializeComponent();
            this.Text = title;
            this.ShowInTaskbar = false;
            this.StartPosition = FormStartPosition.CenterParent;
        }

        private void InitializeComponent()
        {
            this.progressBar = new ProgressBar();
            this.statusLabel = new Label();
            this.SuspendLayout();

            // progressBar
            this.progressBar.Location = new System.Drawing.Point(12, 40);
            this.progressBar.Name = "progressBar";
            this.progressBar.Size = new System.Drawing.Size(360, 23);
            this.progressBar.TabIndex = 0;

            // statusLabel
            this.statusLabel.Location = new System.Drawing.Point(12, 15);
            this.statusLabel.Name = "statusLabel";
            this.statusLabel.Size = new System.Drawing.Size(360, 20);
            this.statusLabel.TabIndex = 1;
            this.statusLabel.Text = "Processing...";

            // ProgressForm
            this.ClientSize = new System.Drawing.Size(384, 80);
            this.Controls.Add(this.statusLabel);
            this.Controls.Add(this.progressBar);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.Name = "ProgressForm";
            this.ResumeLayout(false);
        }

        public void UpdateProgress(int percentage, string status)
        {
            if (this.InvokeRequired)
            {
                this.Invoke(new Action<int, string>(UpdateProgress), percentage, status);
                return;
            }

            this.progressBar.Value = Math.Max(0, Math.Min(100, percentage));
            this.statusLabel.Text = status;
            this.Refresh();
        }
    }
}