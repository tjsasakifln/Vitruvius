/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

import React, { useState, useEffect } from 'react';

function ActivityTimeline({ projectId, conflictId, limit = 50 }) {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({
    activityTypes: [],
    users: [],
    dateRange: 'all'
  });
  const [availableFilters, setAvailableFilters] = useState({
    activityTypes: [],
    users: []
  });

  useEffect(() => {
    fetchActivities();
  }, [projectId, conflictId, limit]);

  const fetchActivities = async () => {
    try {
      setLoading(true);
      
      const endpoint = conflictId 
        ? `/api/collaboration/conflicts/${conflictId}/activity?limit=${limit}`
        : `/api/collaboration/projects/${projectId}/activity?limit=${limit}`;
      
      const response = await fetch(endpoint);
      
      if (!response.ok) {
        throw new Error('Failed to fetch activity data');
      }
      
      const data = await response.json();
      setActivities(data.activities || []);
      
      // Extract unique activity types and users for filters
      const activityTypes = [...new Set(data.activities.map(a => a.activity_type))];
      const users = [...new Set(data.activities.map(a => a.user).filter(u => u).map(u => ({ id: u.id, name: u.full_name })))];
      
      setAvailableFilters({
        activityTypes,
        users
      });
      
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDateTime = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffMinutes < 1) {
      return 'Just now';
    } else if (diffMinutes < 60) {
      return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    } else if (diffDays < 7) {
      return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  const getActivityIcon = (activityType) => {
    const icons = {
      'conflict_created': '🚨',
      'conflict_updated': '📝',
      'conflict_status_changed': '🔄',
      'comment_added': '💬',
      'solution_added': '💡',
      'annotation_added': '📌',
      'feedback_submitted': '⭐',
      'user_assigned': '👤',
      'file_uploaded': '📎',
      'integration_sync': '🔗'
    };
    return icons[activityType] || '📋';
  };

  const getActivityColor = (activityType) => {
    const colors = {
      'conflict_created': '#dc3545',
      'conflict_updated': '#ffc107',
      'conflict_status_changed': '#17a2b8',
      'comment_added': '#28a745',
      'solution_added': '#007bff',
      'annotation_added': '#6f42c1',
      'feedback_submitted': '#fd7e14',
      'user_assigned': '#20c997',
      'file_uploaded': '#6c757d',
      'integration_sync': '#e83e8c'
    };
    return colors[activityType] || '#6c757d';
  };

  const formatActivityType = (activityType) => {
    return activityType
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const filteredActivities = activities.filter(activity => {
    // Filter by activity type
    if (filters.activityTypes.length > 0 && !filters.activityTypes.includes(activity.activity_type)) {
      return false;
    }
    
    // Filter by user
    if (filters.users.length > 0 && (!activity.user || !filters.users.includes(activity.user.id))) {
      return false;
    }
    
    // Filter by date range
    if (filters.dateRange !== 'all') {
      const activityDate = new Date(activity.created_at);
      const now = new Date();
      const daysAgo = parseInt(filters.dateRange);
      const cutoffDate = new Date(now.getTime() - daysAgo * 24 * 60 * 60 * 1000);
      
      if (activityDate < cutoffDate) {
        return false;
      }
    }
    
    return true;
  });

  const handleFilterChange = (filterType, value) => {
    setFilters(prev => {
      const newFilters = { ...prev };
      
      if (filterType === 'activityTypes') {
        if (newFilters.activityTypes.includes(value)) {
          newFilters.activityTypes = newFilters.activityTypes.filter(t => t !== value);
        } else {
          newFilters.activityTypes.push(value);
        }
      } else if (filterType === 'users') {
        if (newFilters.users.includes(value)) {
          newFilters.users = newFilters.users.filter(u => u !== value);
        } else {
          newFilters.users.push(value);
        }
      } else if (filterType === 'dateRange') {
        newFilters.dateRange = value;
      }
      
      return newFilters;
    });
  };

  const clearFilters = () => {
    setFilters({
      activityTypes: [],
      users: [],
      dateRange: 'all'
    });
  };

  if (loading) {
    return <div style={{ padding: '20px', textAlign: 'center' }}>Loading activity timeline...</div>;
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: 'red' }}>
        <h3>Error loading activity: {error}</h3>
        <button onClick={fetchActivities}>Retry</button>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h3>Activity Timeline</h3>
        <button 
          onClick={fetchActivities}
          style={{ 
            padding: '8px 16px', 
            backgroundColor: '#007bff', 
            color: 'white', 
            border: 'none', 
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div style={{ 
        backgroundColor: '#f8f9fa', 
        padding: '15px', 
        borderRadius: '8px', 
        marginBottom: '20px',
        border: '1px solid #dee2e6'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h5 style={{ margin: 0 }}>Filters</h5>
          <button 
            onClick={clearFilters}
            style={{ 
              padding: '4px 8px', 
              backgroundColor: 'transparent', 
              color: '#6c757d', 
              border: '1px solid #6c757d', 
              borderRadius: '3px',
              cursor: 'pointer',
              fontSize: '12px'
            }}
          >
            Clear All
          </button>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '15px' }}>
          {/* Activity Type Filter */}
          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '5px' }}>Activity Types:</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
              {availableFilters.activityTypes.map(type => (
                <button
                  key={type}
                  onClick={() => handleFilterChange('activityTypes', type)}
                  style={{
                    padding: '4px 8px',
                    border: `1px solid ${getActivityColor(type)}`,
                    borderRadius: '12px',
                    backgroundColor: filters.activityTypes.includes(type) ? getActivityColor(type) : 'white',
                    color: filters.activityTypes.includes(type) ? 'white' : getActivityColor(type),
                    cursor: 'pointer',
                    fontSize: '11px'
                  }}
                >
                  {getActivityIcon(type)} {formatActivityType(type)}
                </button>
              ))}
            </div>
          </div>

          {/* Date Range Filter */}
          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '5px' }}>Date Range:</label>
            <select
              value={filters.dateRange}
              onChange={(e) => handleFilterChange('dateRange', e.target.value)}
              style={{ 
                padding: '6px', 
                border: '1px solid #ced4da', 
                borderRadius: '4px',
                width: '100%'
              }}
            >
              <option value="all">All Time</option>
              <option value="1">Last 24 Hours</option>
              <option value="7">Last 7 Days</option>
              <option value="30">Last 30 Days</option>
              <option value="90">Last 3 Months</option>
            </select>
          </div>

          {/* User Filter */}
          <div>
            <label style={{ display: 'block', fontWeight: 'bold', marginBottom: '5px' }}>Users:</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
              {availableFilters.users.map(user => (
                <button
                  key={user.id}
                  onClick={() => handleFilterChange('users', user.id)}
                  style={{
                    padding: '4px 8px',
                    border: '1px solid #007bff',
                    borderRadius: '12px',
                    backgroundColor: filters.users.includes(user.id) ? '#007bff' : 'white',
                    color: filters.users.includes(user.id) ? 'white' : '#007bff',
                    cursor: 'pointer',
                    fontSize: '11px'
                  }}
                >
                  👤 {user.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div style={{ position: 'relative' }}>
        {/* Timeline line */}
        <div style={{
          position: 'absolute',
          left: '20px',
          top: '0',
          bottom: '0',
          width: '2px',
          backgroundColor: '#dee2e6'
        }} />

        {filteredActivities.length > 0 ? (
          <div>
            {filteredActivities.map((activity, index) => (
              <div
                key={activity.id}
                style={{
                  position: 'relative',
                  marginBottom: '20px',
                  paddingLeft: '50px'
                }}
              >
                {/* Timeline dot */}
                <div style={{
                  position: 'absolute',
                  left: '12px',
                  top: '8px',
                  width: '16px',
                  height: '16px',
                  borderRadius: '50%',
                  backgroundColor: getActivityColor(activity.activity_type),
                  border: '2px solid white',
                  boxShadow: '0 0 0 1px #dee2e6',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '8px'
                }}>
                  {getActivityIcon(activity.activity_type)}
                </div>

                {/* Activity content */}
                <div style={{
                  backgroundColor: 'white',
                  border: '1px solid #dee2e6',
                  borderRadius: '8px',
                  padding: '15px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{
                        padding: '2px 8px',
                        backgroundColor: getActivityColor(activity.activity_type),
                        color: 'white',
                        borderRadius: '12px',
                        fontSize: '11px',
                        fontWeight: 'bold'
                      }}>
                        {formatActivityType(activity.activity_type)}
                      </span>
                      <strong>{activity.user?.full_name || 'System'}</strong>
                    </div>
                    <small style={{ color: '#6c757d' }}>
                      {formatDateTime(activity.created_at)}
                    </small>
                  </div>

                  <p style={{ margin: '8px 0', color: '#495057' }}>
                    {activity.description}
                  </p>

                  {/* Show additional data if available */}
                  {(activity.old_values || activity.new_values) && (
                    <div style={{ marginTop: '10px', fontSize: '12px' }}>
                      {activity.old_values && (
                        <div style={{ marginBottom: '5px' }}>
                          <strong>Previous:</strong> 
                          <code style={{ marginLeft: '5px', padding: '2px 4px', backgroundColor: '#f8f9fa', borderRadius: '3px' }}>
                            {JSON.stringify(activity.old_values)}
                          </code>
                        </div>
                      )}
                      {activity.new_values && (
                        <div>
                          <strong>New:</strong> 
                          <code style={{ marginLeft: '5px', padding: '2px 4px', backgroundColor: '#f8f9fa', borderRadius: '3px' }}>
                            {JSON.stringify(activity.new_values)}
                          </code>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Show metadata if available */}
                  {activity.metadata && (
                    <div style={{ marginTop: '8px', fontSize: '11px', color: '#6c757d' }}>
                      <details>
                        <summary style={{ cursor: 'pointer' }}>Additional Details</summary>
                        <pre style={{ marginTop: '5px', fontSize: '10px', backgroundColor: '#f8f9fa', padding: '8px', borderRadius: '3px', overflow: 'auto' }}>
                          {JSON.stringify(activity.metadata, null, 2)}
                        </pre>
                      </details>
                    </div>
                  )}

                  {/* Link to related entity */}
                  {activity.conflict_id && (
                    <div style={{ marginTop: '8px' }}>
                      <a 
                        href={`/projects/${projectId}/conflicts/${activity.conflict_id}`}
                        style={{ 
                          fontSize: '12px', 
                          color: '#007bff', 
                          textDecoration: 'none',
                          padding: '2px 6px',
                          border: '1px solid #007bff',
                          borderRadius: '3px'
                        }}
                      >
                        View Conflict #{activity.conflict_id}
                      </a>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ 
            textAlign: 'center', 
            padding: '40px', 
            color: '#6c757d',
            backgroundColor: '#f8f9fa',
            borderRadius: '8px'
          }}>
            <h4>No Activities Found</h4>
            <p>
              {activities.length === 0 
                ? 'No activities have been recorded yet.'
                : 'No activities match the current filters.'
              }
            </p>
            {filters.activityTypes.length > 0 || filters.users.length > 0 || filters.dateRange !== 'all' ? (
              <button 
                onClick={clearFilters}
                style={{ 
                  padding: '8px 16px', 
                  backgroundColor: '#007bff', 
                  color: 'white', 
                  border: 'none', 
                  borderRadius: '4px',
                  cursor: 'pointer',
                  marginTop: '10px'
                }}
              >
                Clear Filters
              </button>
            ) : null}
          </div>
        )}
      </div>

      {/* Activity Summary */}
      {activities.length > 0 && (
        <div style={{ 
          marginTop: '30px', 
          padding: '15px', 
          backgroundColor: '#e9ecef', 
          borderRadius: '8px',
          fontSize: '14px'
        }}>
          <strong>Summary:</strong> Showing {filteredActivities.length} of {activities.length} activities
          {filters.activityTypes.length > 0 && (
            <span> • Filtered by {filters.activityTypes.length} activity type{filters.activityTypes.length !== 1 ? 's' : ''}</span>
          )}
          {filters.users.length > 0 && (
            <span> • Filtered by {filters.users.length} user{filters.users.length !== 1 ? 's' : ''}</span>
          )}
          {filters.dateRange !== 'all' && (
            <span> • Last {filters.dateRange} day{filters.dateRange !== '1' ? 's' : ''}</span>
          )}
        </div>
      )}
    </div>
  );
}

export default ActivityTimeline;