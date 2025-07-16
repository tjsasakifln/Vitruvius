# Vitruvius Revit Add-in

This add-in integrates Autodesk Revit with the Vitruvius intelligent BIM clash detection system, allowing users to send their Revit models directly to Vitruvius for advanced conflict analysis and AI-powered resolution suggestions.

## Features

- **One-Click Export**: Send your Revit model to Vitruvius with a single click
- **Intelligent Processing**: AI-powered clash detection and resolution suggestions
- **Project Management**: Automatically creates and manages projects in Vitruvius
- **Progress Tracking**: Real-time progress updates during export and upload
- **Web Integration**: Direct links to view results in the Vitruvius web interface

## Installation

### Prerequisites

- Autodesk Revit 2024 or later
- .NET Framework 4.8 or later
- Active internet connection for Vitruvius API access

### Installation Steps

1. **Build the Add-in**:
   - Open `VitruviusRevitAddin.sln` in Visual Studio
   - Build the solution in Release mode
   - The output will be in `bin\Release\`

2. **Install the Add-in**:
   - Copy `VitruviusRevitAddin.dll` to your Revit add-ins folder:
     - `C:\Users\[USERNAME]\AppData\Roaming\Autodesk\Revit\Addins\2024\`
   - Copy `VitruviusRevitAddin.addin` to the same folder
   - Copy `app.config` to the same folder and rename it to `VitruviusRevitAddin.dll.config`

3. **Configuration**:
   - Edit `VitruviusRevitAddin.dll.config` to set your Vitruvius API URL and credentials
   - Update the `VitruviusApiUrl` and `VitruviusWebUrl` settings

## Usage

### Sending a Model to Vitruvius

1. **Open your Revit model**
2. **Save the model** (required before export)
3. **Click the "Send to Vitruvius" button** in the Vitruvius ribbon tab
4. **Wait for processing** - the add-in will:
   - Export your model to IFC format
   - Upload it to Vitruvius
   - Process it for clash detection
5. **View results** - optionally open the web interface to view clash detection results

### Viewing Results

1. **Click the "View Clashes" button** in the Vitruvius ribbon tab
2. **Or** click "Yes" when prompted after upload completion
3. **Review clashes** in the Vitruvius web interface
4. **Get AI-powered suggestions** for resolving conflicts

## Configuration Options

Edit the `app.config` file to customize the add-in behavior:

```xml
<appSettings>
  <!-- API Configuration -->
  <add key="VitruviusApiUrl" value="https://your-vitruvius-api.com/api/v1" />
  <add key="VitruviusWebUrl" value="https://your-vitruvius-web.com" />
  <add key="VitruviusApiKey" value="your-api-key" />
  
  <!-- Behavior Options -->
  <add key="AutoOpenWebInterface" value="true" />
  <add key="DeleteTempFiles" value="true" />
  
  <!-- Export Options -->
  <add key="ExportIFCVersion" value="IFC2x3CV2" />
  <add key="ExportBaseQuantities" value="true" />
  <add key="ExportInternalProperties" value="true" />
</appSettings>
```

## Development

### Building from Source

1. **Clone the repository**
2. **Open in Visual Studio 2019 or later**
3. **Add Revit API references**:
   - Reference `RevitAPI.dll` from your Revit installation
   - Reference `RevitAPIUI.dll` from your Revit installation
4. **Build the solution**

### Project Structure

```
VitruviusRevitAddin/
├── VitruviusApplication.cs      # Main application class (IExternalApplication)
├── SendToVitruviusCommand.cs    # Command for sending models to Vitruvius
├── VitruviusAPI.cs             # API client for Vitruvius backend
├── VitruviusRevitAddin.addin   # Revit add-in manifest
├── app.config                  # Configuration file
└── Resources/
    └── vitruvius-icon.png      # Icon for ribbon buttons
```

## API Integration

The add-in integrates with the Vitruvius API endpoints:

- `POST /api/v1/projects/` - Create new project
- `POST /api/v1/projects/{id}/upload-ifc` - Upload IFC model
- `GET /api/v1/projects/{id}/conflicts` - Get clash detection results

## Troubleshooting

### Common Issues

1. **"No active document found"**:
   - Ensure you have a Revit model open
   - Save the model before attempting to send to Vitruvius

2. **"Failed to export IFC file"**:
   - Check that the model is valid and saved
   - Verify you have write permissions to the temp directory

3. **"Failed to upload model to Vitruvius"**:
   - Check your internet connection
   - Verify the API URL and credentials in the config file
   - Check if the Vitruvius service is running

4. **Add-in not loading**:
   - Ensure the `.addin` file is in the correct Revit add-ins folder
   - Check that the DLL path in the `.addin` file is correct
   - Verify .NET Framework 4.8 is installed

### Debug Mode

To enable debug logging:

1. Build the solution in Debug mode
2. Use a tool like DebugView to view debug output
3. Check the Revit journal files for error messages

## Support

For support and bug reports, please contact the Vitruvius team or create an issue in the project repository.

## License

This add-in is part of the Vitruvius project. See the main project license for terms and conditions.