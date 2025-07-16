// Production use requires a separate commercial license from the Licensor.
// For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.

using System;
using System.IO;
using System.Reflection;
using System.Windows.Media.Imaging;
using Autodesk.Revit.UI;

namespace VitruviusRevitAddin
{
    /// <summary>
    /// Implements the IExternalApplication interface to add Vitruvius functionality to Revit
    /// </summary>
    public class VitruviusApplication : IExternalApplication
    {
        // Static variable to store the application instance
        public static VitruviusApplication Instance { get; private set; }

        /// <summary>
        /// Called when Revit starts up
        /// </summary>
        public Result OnStartup(UIControlledApplication application)
        {
            try
            {
                Instance = this;
                
                // Create the Vitruvius ribbon tab
                string tabName = "Vitruvius";
                application.CreateRibbonTab(tabName);

                // Create the ribbon panel
                RibbonPanel ribbonPanel = application.CreateRibbonPanel(tabName, "Clash Detection");

                // Create the "Send to Vitruvius" button
                CreateSendToVitruviusButton(ribbonPanel);

                // Create the "View Clashes" button
                CreateViewClashesButton(ribbonPanel);

                // Create the "Settings" button
                CreateSettingsButton(ribbonPanel);

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                TaskDialog.Show("Error", $"Failed to initialize Vitruvius Add-in: {ex.Message}");
                return Result.Failed;
            }
        }

        /// <summary>
        /// Called when Revit shuts down
        /// </summary>
        public Result OnShutdown(UIControlledApplication application)
        {
            return Result.Succeeded;
        }

        /// <summary>
        /// Creates the "Send to Vitruvius" button
        /// </summary>
        private void CreateSendToVitruviusButton(RibbonPanel ribbonPanel)
        {
            string thisAssemblyPath = Assembly.GetExecutingAssembly().Location;
            
            PushButtonData buttonData = new PushButtonData(
                "SendToVitruvius",
                "Send to\nVitruvius",
                thisAssemblyPath,
                "VitruviusRevitAddin.SendToVitruviusCommand");

            PushButton pushButton = ribbonPanel.AddItem(buttonData) as PushButton;
            
            // Set the button properties
            pushButton.ToolTip = "Send current Revit model to Vitruvius for clash detection";
            pushButton.LongDescription = "Export the current Revit model to IFC format and upload it to Vitruvius for intelligent clash detection and resolution suggestions.";
            
            // Set the button icon
            pushButton.LargeImage = GetEmbeddedImage("vitruvius-icon.png");
            pushButton.Image = GetEmbeddedImage("vitruvius-icon.png");
        }

        /// <summary>
        /// Creates the "View Clashes" button
        /// </summary>
        private void CreateViewClashesButton(RibbonPanel ribbonPanel)
        {
            string thisAssemblyPath = Assembly.GetExecutingAssembly().Location;
            
            PushButtonData buttonData = new PushButtonData(
                "ViewClashes",
                "View\nClashes",
                thisAssemblyPath,
                "VitruviusRevitAddin.ViewClashesCommand");

            PushButton pushButton = ribbonPanel.AddItem(buttonData) as PushButton;
            
            pushButton.ToolTip = "View clash detection results from Vitruvius";
            pushButton.LongDescription = "Open the Vitruvius web interface to view clash detection results and resolution suggestions for the current project.";
            
            pushButton.LargeImage = GetEmbeddedImage("vitruvius-icon.png");
            pushButton.Image = GetEmbeddedImage("vitruvius-icon.png");
        }

        /// <summary>
        /// Creates the "Settings" button
        /// </summary>
        private void CreateSettingsButton(RibbonPanel ribbonPanel)
        {
            string thisAssemblyPath = Assembly.GetExecutingAssembly().Location;
            
            PushButtonData buttonData = new PushButtonData(
                "VitruviusSettings",
                "Settings",
                thisAssemblyPath,
                "VitruviusRevitAddin.SettingsCommand");

            PushButton pushButton = ribbonPanel.AddItem(buttonData) as PushButton;
            
            pushButton.ToolTip = "Configure Vitruvius settings";
            pushButton.LongDescription = "Configure API endpoints, authentication credentials, and other settings for the Vitruvius integration.";
            
            pushButton.LargeImage = GetEmbeddedImage("vitruvius-icon.png");
            pushButton.Image = GetEmbeddedImage("vitruvius-icon.png");
        }

        /// <summary>
        /// Gets an embedded image resource
        /// </summary>
        private BitmapImage GetEmbeddedImage(string name)
        {
            try
            {
                Assembly assembly = Assembly.GetExecutingAssembly();
                string resourceName = $"VitruviusRevitAddin.Resources.{name}";
                
                using (Stream stream = assembly.GetManifestResourceStream(resourceName))
                {
                    if (stream != null)
                    {
                        BitmapImage image = new BitmapImage();
                        image.BeginInit();
                        image.StreamSource = stream;
                        image.CacheOption = BitmapCacheOption.OnLoad;
                        image.EndInit();
                        return image;
                    }
                }
            }
            catch (Exception ex)
            {
                // Log the error or use a default image
                System.Diagnostics.Debug.WriteLine($"Failed to load embedded image {name}: {ex.Message}");
            }
            
            return null;
        }
    }
}