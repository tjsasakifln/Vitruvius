/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

import React, { useState, useEffect, useRef } from 'react';
import { SafeText, validateAndSanitizeComment, sanitizeObject, escapeHtml } from '../utils/xssSanitizer';

function ConflictDetails({ conflictId, projectId, currentUser }) {
  const [conflict, setConflict] = useState(null);
  const [comments, setComments] = useState([]);
  const [annotations, setAnnotations] = useState([]);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Real-time state
  const [connectedUsers, setConnectedUsers] = useState([]);
  const [typingUsers, setTypingUsers] = useState(new Set());
  const [isConnected, setIsConnected] = useState(false);
  
  // Comment form state
  const [newComment, setNewComment] = useState('');
  const [commentType, setCommentType] = useState('general');
  const [isInternal, setIsInternal] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  
  // WebSocket connection
  const ws = useRef(null);
  const typingTimeoutRef = useRef(null);
  
  // Active view state
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    if (conflictId) {
      fetchConflictData();
      connectWebSocket();
    }

    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, [conflictId]);

  const fetchConflictData = async () => {
    try {
      setLoading(true);

      const [conflictRes, commentsRes, annotationsRes, activityRes] = await Promise.all([
        fetch(`/api/projects/${projectId}/conflicts/${conflictId}`),
        fetch(`/api/collaboration/conflicts/${conflictId}/comments`),
        fetch(`/api/collaboration/conflicts/${conflictId}/annotations`),
        fetch(`/api/collaboration/conflicts/${conflictId}/activity`)
      ]);

      if (!conflictRes.ok) {
        throw new Error('Failed to fetch conflict data');
      }

      const [conflictData, commentsData, annotationsData, activityData] = await Promise.all([
        conflictRes.json(),
        commentsRes.ok ? commentsRes.json() : { comments: [] },
        annotationsRes.ok ? annotationsRes.json() : [],
        activityRes.ok ? activityRes.json() : { activities: [] }
      ]);

      // Sanitize data before setting state
      const sanitizedConflict = sanitizeObject(conflictData, ['description', 'type'], []);
      const sanitizedComments = (commentsData.comments || []).map(comment => 
        sanitizeObject(comment, ['message', 'user.full_name'], [])
      );
      const sanitizedAnnotations = annotationsData.map(annotation => 
        sanitizeObject(annotation, ['title', 'description', 'user.full_name'], [])
      );
      const sanitizedActivity = (activityData.activities || []).map(activity => 
        sanitizeObject(activity, ['description', 'user.full_name'], [])
      );
      
      setConflict(sanitizedConflict);
      setComments(sanitizedComments);
      setAnnotations(sanitizedAnnotations);
      setActivity(sanitizedActivity);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/collaboration/ws/conflict/${conflictId}?user_id=${currentUser?.id}`;
    
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      // Attempt to reconnect after 5 seconds
      setTimeout(() => {
        if (conflictId) {
          connectWebSocket();
        }
      }, 5000);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };
  };

  const handleWebSocketMessage = (message) => {
    switch (message.type) {
      case 'comment_added':
        setComments(prev => [message.data, ...prev]);
        break;
      
      case 'annotation_added':
        setAnnotations(prev => [message.data, ...prev]);
        break;
      
      case 'solution_added':
        // Refresh conflict data to get updated solutions
        fetchConflictData();
        break;
      
      case 'conflict_status_changed':
        setConflict(prev => ({ ...prev, ...message.data }));
        break;
      
      case 'user_joined':
        setConnectedUsers(prev => {
          if (!prev.some(user => user.id === message.user_id)) {
            return [...prev, { id: message.user_id, status: 'online' }];
          }
          return prev;
        });
        break;
      
      case 'user_left':
        setConnectedUsers(prev => prev.filter(user => user.id !== message.user_id));
        break;
      
      case 'typing_indicator':
        setTypingUsers(prev => {
          const newSet = new Set(prev);
          if (message.is_typing && message.user_id !== currentUser?.id) {
            newSet.add(message.user_id);
          } else {
            newSet.delete(message.user_id);
          }
          return newSet;
        });
        break;
      
      case 'user_presence':
        setConnectedUsers(prev => 
          prev.map(user => 
            user.id === message.user_id 
              ? { ...user, status: message.status }
              : user
          )
        );
        break;
      
      default:
        console.log('Unknown message type:', message.type);
    }
  };

  const sendWebSocketMessage = (message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  };

  const handleCommentSubmit = async (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;

    // Validate and sanitize comment before submission
    const validation = validateAndSanitizeComment(newComment);
    if (!validation.isValid) {
      alert(`Error: ${validation.error}`);
      return;
    }

    try {
      const response = await fetch(`/api/collaboration/conflicts/${conflictId}/comments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: validation.sanitized,
          comment_type: commentType,
          is_internal: isInternal
        })
      });

      if (!response.ok) {
        throw new Error('Failed to add comment');
      }

      setNewComment('');
      setCommentType('general');
      setIsInternal(false);
      
      // Stop typing indicator
      handleTypingStop();
    } catch (err) {
      alert(`Error adding comment: ${err.message}`);
    }
  };

  const handleCommentChange = (e) => {
    setNewComment(e.target.value);
    
    if (!isTyping) {
      setIsTyping(true);
      sendWebSocketMessage({
        type: 'typing',
        is_typing: true
      });
    }

    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Set new timeout to stop typing indicator
    typingTimeoutRef.current = setTimeout(() => {
      handleTypingStop();
    }, 2000);
  };

  const handleTypingStop = () => {
    if (isTyping) {
      setIsTyping(false);
      sendWebSocketMessage({
        type: 'typing',
        is_typing: false
      });
    }
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
  };

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusColor = (status) => {
    const colors = {
      'detected': '#dc3545',
      'investigating': '#ffc107',
      'solution_proposed': '#17a2b8',
      'under_review': '#6f42c1',
      'resolved': '#28a745',
      'closed': '#6c757d'
    };
    return colors[status] || '#6c757d';
  };

  const getSeverityColor = (severity) => {
    const colors = {
      'low': '#28a745',
      'medium': '#ffc107',
      'high': '#fd7e14',
      'critical': '#dc3545'
    };
    return colors[severity] || '#6c757d';
  };

  if (loading) {
    return <div style={{ padding: '20px' }}>Loading conflict details...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: 'red' }}>
        <h3>Error: {error}</h3>
        <button onClick={fetchConflictData}>Retry</button>
      </div>
    );
  }

  if (!conflict) {
    return <div style={{ padding: '20px' }}>Conflict not found</div>;
  }

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Conflict Details</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ 
            padding: '4px 8px', 
            borderRadius: '4px', 
            backgroundColor: isConnected ? '#d4edda' : '#f8d7da',
            color: isConnected ? '#155724' : '#721c24',
            fontSize: '12px'
          }}>
            {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
          </span>
          <span style={{ fontSize: '12px', color: '#6c757d' }}>
            {connectedUsers.length} user{connectedUsers.length !== 1 ? 's' : ''} online
          </span>
        </div>
      </div>

      {/* Conflict Summary */}
      <div style={{ 
        backgroundColor: '#f8f9fa', 
        padding: '20px', 
        borderRadius: '8px', 
        marginBottom: '20px',
        border: `3px solid ${getStatusColor(conflict.status)}`
      }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div>
            <h3 style={{ margin: '0 0 10px 0' }}>
              <SafeText text={conflict.type || 'Unknown Type'} /> Conflict
            </h3>
            <p><strong>Description:</strong> <SafeText text={conflict.description} /></p>
            <p><strong>Elements:</strong> {conflict.elements?.length || 0} affected</p>
          </div>
          <div>
            <p><strong>Status:</strong> 
              <span style={{ 
                marginLeft: '8px', 
                padding: '4px 8px', 
                borderRadius: '4px', 
                backgroundColor: getStatusColor(conflict.status),
                color: 'white',
                fontSize: '12px'
              }}>
                {conflict.status}
              </span>
            </p>
            <p><strong>Severity:</strong> 
              <span style={{ 
                marginLeft: '8px', 
                padding: '4px 8px', 
                borderRadius: '4px', 
                backgroundColor: getSeverityColor(conflict.severity),
                color: 'white',
                fontSize: '12px'
              }}>
                {conflict.severity}
              </span>
            </p>
            <p><strong>Detected:</strong> {formatDateTime(conflict.created_at)}</p>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div style={{ 
        borderBottom: '1px solid #ddd', 
        marginBottom: '20px',
        display: 'flex',
        gap: '0'
      }}>
        {['overview', 'comments', 'annotations', 'activity'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: '10px 20px',
              border: 'none',
              borderBottom: activeTab === tab ? '2px solid #007bff' : '2px solid transparent',
              backgroundColor: 'transparent',
              cursor: 'pointer',
              textTransform: 'capitalize',
              fontWeight: activeTab === tab ? 'bold' : 'normal',
              color: activeTab === tab ? '#007bff' : '#6c757d'
            }}
          >
            {tab}
            {tab === 'comments' && comments.length > 0 && (
              <span style={{ 
                marginLeft: '5px', 
                backgroundColor: '#dc3545', 
                color: 'white', 
                borderRadius: '10px', 
                padding: '2px 6px', 
                fontSize: '10px' 
              }}>
                {comments.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div>
          <h3>Solutions</h3>
          {conflict.solutions && conflict.solutions.length > 0 ? (
            <div style={{ display: 'grid', gap: '15px' }}>
              {conflict.solutions.map((solution, index) => (
                <div key={solution.id || index} style={{ 
                  padding: '15px', 
                  border: '1px solid #ddd', 
                  borderRadius: '5px',
                  backgroundColor: 'white'
                }}>
                  <h4><SafeText text={solution.type || 'Solution'} /></h4>
                  <p><SafeText text={solution.description} /></p>
                  {solution.estimated_cost && (
                    <p><strong>Estimated Cost:</strong> ${solution.estimated_cost.toLocaleString()}</p>
                  )}
                  {solution.estimated_time && (
                    <p><strong>Estimated Time:</strong> {solution.estimated_time} days</p>
                  )}
                  <p><strong>Confidence:</strong> {((solution.confidence_score || 0) * 100).toFixed(1)}%</p>
                </div>
              ))}
            </div>
          ) : (
            <p>No solutions available yet.</p>
          )}
        </div>
      )}

      {activeTab === 'comments' && (
        <div>
          {/* Comment Form */}
          <form onSubmit={handleCommentSubmit} style={{ 
            backgroundColor: '#f8f9fa', 
            padding: '20px', 
            borderRadius: '8px', 
            marginBottom: '20px' 
          }}>
            <h4>Add Comment</h4>
            <div style={{ marginBottom: '15px' }}>
              <select 
                value={commentType} 
                onChange={(e) => setCommentType(e.target.value)}
                style={{ padding: '5px', marginRight: '10px', borderRadius: '3px', border: '1px solid #ddd' }}
              >
                <option value="general">General</option>
                <option value="solution_review">Solution Review</option>
                <option value="annotation">Annotation</option>
                <option value="status_update">Status Update</option>
              </select>
              <label style={{ fontSize: '14px' }}>
                <input 
                  type="checkbox" 
                  checked={isInternal} 
                  onChange={(e) => setIsInternal(e.target.checked)}
                  style={{ marginRight: '5px' }}
                />
                Internal comment (team only)
              </label>
            </div>
            <textarea
              value={newComment}
              onChange={handleCommentChange}
              placeholder="Type your comment here..."
              style={{ 
                width: '100%', 
                minHeight: '100px', 
                padding: '10px', 
                border: '1px solid #ddd', 
                borderRadius: '5px',
                resize: 'vertical'
              }}
              required
            />
            {typingUsers.size > 0 && (
              <div style={{ fontSize: '12px', color: '#6c757d', marginTop: '5px' }}>
                {Array.from(typingUsers).join(', ')} {typingUsers.size === 1 ? 'is' : 'are'} typing...
              </div>
            )}
            <button 
              type="submit"
              style={{ 
                marginTop: '10px',
                padding: '8px 16px', 
                backgroundColor: '#007bff', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Add Comment
            </button>
          </form>

          {/* Comments List */}
          <div>
            {comments.length > 0 ? (
              <div style={{ display: 'grid', gap: '15px' }}>
                {comments.map(comment => (
                  <div key={comment.id} style={{ 
                    padding: '15px', 
                    border: '1px solid #ddd', 
                    borderRadius: '5px',
                    backgroundColor: comment.is_internal ? '#fff3cd' : 'white'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                      <div>
                        <strong><SafeText text={comment.user?.full_name || 'Unknown User'} /></strong>
                        <span style={{ 
                          marginLeft: '10px', 
                          padding: '2px 6px', 
                          backgroundColor: '#e9ecef', 
                          borderRadius: '10px', 
                          fontSize: '10px' 
                        }}>
                          {comment.comment_type}
                        </span>
                        {comment.is_internal && (
                          <span style={{ 
                            marginLeft: '5px', 
                            padding: '2px 6px', 
                            backgroundColor: '#856404', 
                            color: 'white',
                            borderRadius: '10px', 
                            fontSize: '10px' 
                          }}>
                            Internal
                          </span>
                        )}
                      </div>
                      <small style={{ color: '#6c757d' }}>
                        {formatDateTime(comment.created_at)}
                        {comment.is_edited && ' (edited)'}
                      </small>
                    </div>
                    <p style={{ margin: '0', whiteSpace: 'pre-wrap' }}>
                      <SafeText text={comment.message} />
                    </p>
                    {comment.attachments && comment.attachments.length > 0 && (
                      <div style={{ marginTop: '10px' }}>
                        <strong>Attachments:</strong>
                        {comment.attachments.map(att => (
                          <div key={att.id} style={{ marginTop: '5px' }}>
                            📎 <SafeText text={att.filename} /> ({(att.file_size / 1024).toFixed(1)} KB)
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p>No comments yet. Be the first to comment!</p>
            )}
          </div>
        </div>
      )}

      {activeTab === 'annotations' && (
        <div>
          <h3>Annotations</h3>
          {annotations.length > 0 ? (
            <div style={{ display: 'grid', gap: '15px' }}>
              {annotations.map(annotation => (
                <div key={annotation.id} style={{ 
                  padding: '15px', 
                  border: '1px solid #ddd', 
                  borderRadius: '5px',
                  backgroundColor: annotation.is_resolved ? '#d4edda' : 'white'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <h4 style={{ margin: 0 }}>
                      <SafeText text={annotation.title || `${annotation.annotation_type} annotation`} />
                    </h4>
                    <div>
                      <span style={{ 
                        padding: '4px 8px', 
                        borderRadius: '4px', 
                        backgroundColor: annotation.is_resolved ? '#28a745' : '#ffc107',
                        color: 'white',
                        fontSize: '12px',
                        marginRight: '5px'
                      }}>
                        {annotation.is_resolved ? 'Resolved' : 'Open'}
                      </span>
                      <span style={{ 
                        padding: '4px 8px', 
                        borderRadius: '4px', 
                        backgroundColor: '#6c757d',
                        color: 'white',
                        fontSize: '12px'
                      }}>
                        {annotation.priority}
                      </span>
                    </div>
                  </div>
                  <p><SafeText text={annotation.description} /></p>
                  <small style={{ color: '#6c757d' }}>
                    Created by <SafeText text={annotation.user?.full_name} /> on {formatDateTime(annotation.created_at)}
                  </small>
                </div>
              ))}
            </div>
          ) : (
            <p>No annotations yet.</p>
          )}
        </div>
      )}

      {activeTab === 'activity' && (
        <div>
          <h3>Activity Timeline</h3>
          {activity.length > 0 ? (
            <div style={{ display: 'grid', gap: '10px' }}>
              {activity.map(item => (
                <div key={item.id} style={{ 
                  padding: '15px', 
                  border: '1px solid #ddd', 
                  borderRadius: '5px',
                  backgroundColor: '#f8f9fa',
                  borderLeft: '4px solid #007bff'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong><SafeText text={item.user?.full_name} /></strong> 
                      <span style={{ marginLeft: '10px' }}>
                        <SafeText text={item.description} />
                      </span>
                    </div>
                    <small style={{ color: '#6c757d' }}>
                      {formatDateTime(item.created_at)}
                    </small>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p>No activity recorded yet.</p>
          )}
        </div>
      )}
    </div>
  );
}

export default ConflictDetails;