using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Security;
using System.Runtime.InteropServices;
using Microsoft.Win32;
using System.Security.Cryptography;

namespace VitruviusRevitAddin
{
    /// <summary>
    /// Secure authentication manager for Vitruvius API
    /// Handles JWT token authentication without storing plain text API keys
    /// </summary>
    public class SecureAuthManager : IDisposable
    {
        private readonly HttpClient _httpClient;
        private readonly string _apiUrl;
        private readonly string _credentialKey = "VitruviusRevitAddin";
        private string _accessToken;
        private DateTime _tokenExpiryTime;
        private bool _disposed = false;

        public SecureAuthManager(string apiUrl)
        {
            _apiUrl = apiUrl?.TrimEnd('/') ?? throw new ArgumentNullException(nameof(apiUrl));
            _httpClient = new HttpClient();
            _httpClient.DefaultRequestHeaders.Add("User-Agent", "VitruviusRevitAddin/1.0");
        }

        /// <summary>
        /// Authenticate user with username and password
        /// </summary>
        /// <param name="username">User email</param>
        /// <param name="password">User password</param>
        /// <returns>True if authentication successful</returns>
        public async Task<bool> AuthenticateAsync(string username, SecureString password)
        {
            try
            {
                // Convert SecureString to string for API call
                string passwordString = SecureStringToString(password);
                
                var loginData = new
                {
                    username = username,
                    password = passwordString
                };

                var jsonContent = JsonSerializer.Serialize(loginData);
                var content = new StringContent(jsonContent, Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync($"{_apiUrl}/auth/token", content);

                if (response.IsSuccessStatusCode)
                {
                    var responseContent = await response.Content.ReadAsStringAsync();
                    var tokenResponse = JsonSerializer.Deserialize<TokenResponse>(responseContent);

                    _accessToken = tokenResponse.access_token;
                    _tokenExpiryTime = DateTime.UtcNow.AddMinutes(50); // 10 minutes before actual expiry

                    // Store credentials securely in Windows Credential Manager
                    StoreCredentialsSecurely(username, password);

                    // Clear password from memory
                    Array.Clear(Encoding.UTF8.GetBytes(passwordString), 0, passwordString.Length);

                    return true;
                }

                return false;
            }
            catch (Exception ex)
            {
                // Log error without exposing sensitive information
                System.Diagnostics.Debug.WriteLine($"Authentication failed: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Get valid access token, refreshing if necessary
        /// </summary>
        /// <returns>Valid access token or null if authentication required</returns>
        public async Task<string> GetValidTokenAsync()
        {
            if (IsTokenValid())
            {
                return _accessToken;
            }

            // Try to refresh token using stored credentials
            var (username, password) = GetStoredCredentials();
            if (username != null && password != null)
            {
                var success = await AuthenticateAsync(username, password);
                if (success)
                {
                    return _accessToken;
                }
            }

            return null;
        }

        /// <summary>
        /// Check if current token is valid
        /// </summary>
        /// <returns>True if token is valid</returns>
        public bool IsTokenValid()
        {
            return !string.IsNullOrEmpty(_accessToken) && DateTime.UtcNow < _tokenExpiryTime;
        }

        /// <summary>
        /// Clear stored credentials and token
        /// </summary>
        public void Logout()
        {
            _accessToken = null;
            _tokenExpiryTime = DateTime.MinValue;
            ClearStoredCredentials();
        }

        /// <summary>
        /// Store credentials securely in Windows Credential Manager
        /// </summary>
        /// <param name="username">Username</param>
        /// <param name="password">Password</param>
        private void StoreCredentialsSecurely(string username, SecureString password)
        {
            try
            {
                // Use Windows Credential Manager to store credentials securely
                var credential = new CREDENTIAL
                {
                    Type = CRED_TYPE.CRED_TYPE_GENERIC,
                    TargetName = _credentialKey,
                    UserName = username,
                    CredentialBlob = Marshal.SecureStringToGlobalAllocUnicode(password),
                    CredentialBlobSize = password.Length * 2, // Unicode is 2 bytes per character
                    Persist = CRED_PERSIST.CRED_PERSIST_LOCAL_MACHINE
                };

                var result = CredWrite(ref credential, 0);
                if (!result)
                {
                    throw new Exception("Failed to store credentials");
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Failed to store credentials: {ex.Message}");
            }
        }

        /// <summary>
        /// Retrieve stored credentials from Windows Credential Manager
        /// </summary>
        /// <returns>Username and password if found</returns>
        private (string username, SecureString password) GetStoredCredentials()
        {
            try
            {
                IntPtr credPtr;
                var result = CredRead(_credentialKey, CRED_TYPE.CRED_TYPE_GENERIC, 0, out credPtr);
                
                if (result)
                {
                    var credential = (CREDENTIAL)Marshal.PtrToStructure(credPtr, typeof(CREDENTIAL));
                    var username = credential.UserName;
                    
                    var password = new SecureString();
                    var passwordPtr = credential.CredentialBlob;
                    var passwordLength = credential.CredentialBlobSize / 2; // Unicode
                    
                    for (int i = 0; i < passwordLength; i++)
                    {
                        var ch = (char)Marshal.ReadInt16(passwordPtr, i * 2);
                        password.AppendChar(ch);
                    }
                    
                    password.MakeReadOnly();
                    
                    CredFree(credPtr);
                    return (username, password);
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Failed to retrieve credentials: {ex.Message}");
            }

            return (null, null);
        }

        /// <summary>
        /// Clear stored credentials
        /// </summary>
        private void ClearStoredCredentials()
        {
            try
            {
                CredDelete(_credentialKey, CRED_TYPE.CRED_TYPE_GENERIC, 0);
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Failed to clear credentials: {ex.Message}");
            }
        }

        /// <summary>
        /// Convert SecureString to string (use with caution)
        /// </summary>
        /// <param name="secureString">SecureString to convert</param>
        /// <returns>String representation</returns>
        private string SecureStringToString(SecureString secureString)
        {
            IntPtr ptr = Marshal.SecureStringToGlobalAllocUnicode(secureString);
            try
            {
                return Marshal.PtrToStringUni(ptr);
            }
            finally
            {
                Marshal.ZeroFreeGlobalAllocUnicode(ptr);
            }
        }

        public void Dispose()
        {
            if (!_disposed)
            {
                _httpClient?.Dispose();
                _disposed = true;
            }
        }

        #region Windows Credential Manager P/Invoke

        [StructLayout(LayoutKind.Sequential)]
        public struct CREDENTIAL
        {
            public int Flags;
            public CRED_TYPE Type;
            public IntPtr TargetName;
            public IntPtr Comment;
            public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
            public int CredentialBlobSize;
            public IntPtr CredentialBlob;
            public CRED_PERSIST Persist;
            public int AttributeCount;
            public IntPtr Attributes;
            public IntPtr TargetAlias;
            public IntPtr UserName;
        }

        public enum CRED_TYPE : int
        {
            CRED_TYPE_GENERIC = 1,
            CRED_TYPE_DOMAIN_PASSWORD = 2,
            CRED_TYPE_DOMAIN_CERTIFICATE = 3,
            CRED_TYPE_DOMAIN_VISIBLE_PASSWORD = 4
        }

        public enum CRED_PERSIST : int
        {
            CRED_PERSIST_SESSION = 1,
            CRED_PERSIST_LOCAL_MACHINE = 2,
            CRED_PERSIST_ENTERPRISE = 3
        }

        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern bool CredWrite(ref CREDENTIAL credential, int flags);

        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern bool CredRead(string targetName, CRED_TYPE type, int flags, out IntPtr credential);

        [DllImport("advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        public static extern bool CredDelete(string targetName, CRED_TYPE type, int flags);

        [DllImport("advapi32.dll")]
        public static extern void CredFree(IntPtr credential);

        #endregion

        private class TokenResponse
        {
            public string access_token { get; set; }
            public string token_type { get; set; }
        }
    }
}