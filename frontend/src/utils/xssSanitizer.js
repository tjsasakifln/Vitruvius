/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

/**
 * XSS Protection utilities for safe rendering of user-generated content
 */

/**
 * Escapes HTML special characters to prevent XSS attacks
 * @param {string} text - Text to escape
 * @returns {string} - Escaped text
 */
export function escapeHtml(text) {
  if (typeof text !== 'string') {
    return '';
  }
  
  const htmlEscapes = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#x27;',
    '/': '&#x2F;'
  };
  
  return text.replace(/[&<>"'/]/g, (match) => htmlEscapes[match]);
}

/**
 * Sanitizes text for safe display in HTML attributes
 * @param {string} text - Text to sanitize
 * @returns {string} - Sanitized text
 */
export function sanitizeAttribute(text) {
  if (typeof text !== 'string') {
    return '';
  }
  
  // Remove any characters that could break out of attributes
  return text.replace(/[<>"'`=]/g, '');
}

/**
 * Sanitizes URLs to prevent javascript: and data: URI attacks
 * @param {string} url - URL to sanitize
 * @returns {string} - Sanitized URL or empty string if dangerous
 */
export function sanitizeUrl(url) {
  if (typeof url !== 'string') {
    return '';
  }
  
  // Remove whitespace and convert to lowercase for checking
  const cleanUrl = url.trim().toLowerCase();
  
  // Block dangerous protocols
  const dangerousProtocols = [
    'javascript:',
    'data:',
    'vbscript:',
    'file:',
    'ftp:'
  ];
  
  if (dangerousProtocols.some(protocol => cleanUrl.startsWith(protocol))) {
    return '';
  }
  
  // Allow only safe protocols
  const safeProtocols = ['http:', 'https:', 'mailto:', 'tel:'];
  const hasProtocol = safeProtocols.some(protocol => cleanUrl.startsWith(protocol));
  
  // If no protocol, assume it's a relative URL (safe)
  if (!hasProtocol && !cleanUrl.includes(':')) {
    return url;
  }
  
  // If it has a protocol, it must be a safe one
  if (hasProtocol) {
    return url;
  }
  
  // Default to empty string for safety
  return '';
}

/**
 * Sanitizes text while preserving basic formatting (newlines)
 * @param {string} text - Text to sanitize
 * @returns {string} - Sanitized text with preserved formatting
 */
export function sanitizeText(text) {
  if (typeof text !== 'string') {
    return '';
  }
  
  // Escape HTML but preserve newlines
  const escaped = escapeHtml(text);
  
  // Convert newlines to <br> tags for display
  return escaped.replace(/\n/g, '<br>');
}

/**
 * Validates and sanitizes user input for comments
 * @param {string} input - User input to validate
 * @returns {object} - {isValid: boolean, sanitized: string, error?: string}
 */
export function validateAndSanitizeComment(input) {
  if (typeof input !== 'string') {
    return { isValid: false, sanitized: '', error: 'Invalid input type' };
  }
  
  // Check length limits
  if (input.length > 10000) {
    return { isValid: false, sanitized: '', error: 'Comment too long (max 10,000 characters)' };
  }
  
  // Check for suspicious patterns
  const suspiciousPatterns = [
    /<script[^>]*>.*?<\/script>/gi,
    /javascript:/gi,
    /vbscript:/gi,
    /onload=/gi,
    /onerror=/gi,
    /onclick=/gi,
    /onmouseover=/gi,
    /<iframe/gi,
    /<object/gi,
    /<embed/gi,
    /<form/gi,
    /<meta/gi,
    /<link/gi
  ];
  
  for (const pattern of suspiciousPatterns) {
    if (pattern.test(input)) {
      return { isValid: false, sanitized: '', error: 'Content contains potentially dangerous elements' };
    }
  }
  
  // Sanitize the input
  const sanitized = sanitizeText(input.trim());
  
  return { isValid: true, sanitized };
}

/**
 * Validates and sanitizes user input for titles and names
 * @param {string} input - User input to validate
 * @returns {object} - {isValid: boolean, sanitized: string, error?: string}
 */
export function validateAndSanitizeTitle(input) {
  if (typeof input !== 'string') {
    return { isValid: false, sanitized: '', error: 'Invalid input type' };
  }
  
  // Check length limits
  if (input.length > 200) {
    return { isValid: false, sanitized: '', error: 'Title too long (max 200 characters)' };
  }
  
  // Remove any HTML tags completely
  const withoutTags = input.replace(/<[^>]*>/g, '');
  
  // Escape any remaining special characters
  const sanitized = escapeHtml(withoutTags.trim());
  
  return { isValid: true, sanitized };
}

/**
 * React component wrapper for safe text rendering
 * @param {object} props - Component props
 * @param {string} props.text - Text to render safely
 * @param {string} props.className - CSS class name
 * @param {string} props.tag - HTML tag to use (default: 'span')
 * @returns {JSX.Element} - Safe text component
 */
export function SafeText({ text, className, tag = 'span' }) {
  const sanitized = sanitizeText(text || '');
  
  const Tag = tag;
  
  return (
    <Tag 
      className={className}
      dangerouslySetInnerHTML={{ __html: sanitized }}
    />
  );
}

/**
 * React component wrapper for safe HTML rendering with limited tags
 * @param {object} props - Component props
 * @param {string} props.html - HTML to render safely
 * @param {string} props.className - CSS class name
 * @param {string} props.tag - HTML tag to use (default: 'div')
 * @returns {JSX.Element} - Safe HTML component
 */
export function SafeHtml({ html, className, tag = 'div' }) {
  // Only allow specific safe tags
  const allowedTags = ['b', 'strong', 'i', 'em', 'u', 'br', 'p'];
  
  let sanitized = escapeHtml(html || '');
  
  // Re-enable only allowed tags
  allowedTags.forEach(tagName => {
    const openTag = `&lt;${tagName}&gt;`;
    const closeTag = `&lt;/${tagName}&gt;`;
    const openTagRegex = new RegExp(openTag, 'gi');
    const closeTagRegex = new RegExp(closeTag, 'gi');
    
    sanitized = sanitized.replace(openTagRegex, `<${tagName}>`);
    sanitized = sanitized.replace(closeTagRegex, `</${tagName}>`);
  });
  
  const Tag = tag;
  
  return (
    <Tag 
      className={className}
      dangerouslySetInnerHTML={{ __html: sanitized }}
    />
  );
}

/**
 * Sanitizes object properties recursively
 * @param {object} obj - Object to sanitize
 * @param {Array<string>} textFields - Fields that should be treated as text
 * @param {Array<string>} htmlFields - Fields that should be treated as HTML
 * @returns {object} - Sanitized object
 */
export function sanitizeObject(obj, textFields = [], htmlFields = []) {
  if (!obj || typeof obj !== 'object') {
    return obj;
  }
  
  if (Array.isArray(obj)) {
    return obj.map(item => sanitizeObject(item, textFields, htmlFields));
  }
  
  const sanitized = {};
  
  Object.keys(obj).forEach(key => {
    const value = obj[key];
    
    if (textFields.includes(key)) {
      sanitized[key] = escapeHtml(value);
    } else if (htmlFields.includes(key)) {
      const validation = validateAndSanitizeComment(value);
      sanitized[key] = validation.isValid ? validation.sanitized : '';
    } else if (typeof value === 'string') {
      sanitized[key] = escapeHtml(value);
    } else if (typeof value === 'object' && value !== null) {
      sanitized[key] = sanitizeObject(value, textFields, htmlFields);
    } else {
      sanitized[key] = value;
    }
  });
  
  return sanitized;
}

/**
 * Content Security Policy helper functions
 */
export const CSPHelpers = {
  /**
   * Generates a secure nonce for CSP
   * @returns {string} - Random nonce
   */
  generateNonce() {
    const array = new Uint8Array(16);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  },
  
  /**
   * Validates if a resource URL is allowed by CSP
   * @param {string} url - URL to validate
   * @param {Array<string>} allowedDomains - List of allowed domains
   * @returns {boolean} - Whether URL is allowed
   */
  isAllowedResource(url, allowedDomains = []) {
    try {
      const urlObj = new URL(url);
      const domain = urlObj.hostname;
      
      // Allow same origin
      if (domain === window.location.hostname) {
        return true;
      }
      
      // Check against allowed domains
      return allowedDomains.some(allowed => 
        domain === allowed || domain.endsWith(`.${allowed}`)
      );
    } catch (e) {
      return false;
    }
  }
};

// Export default object with all functions
export default {
  escapeHtml,
  sanitizeAttribute,
  sanitizeUrl,
  sanitizeText,
  validateAndSanitizeComment,
  validateAndSanitizeTitle,
  SafeText,
  SafeHtml,
  sanitizeObject,
  CSPHelpers
};