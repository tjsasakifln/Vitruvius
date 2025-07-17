/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

import React, { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement,
} from 'chart.js';
import { Bar, Pie, Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  PointElement,
  LineElement
);

function PortfolioDashboard() {
  const [portfolioData, setPortfolioData] = useState(null);
  const [conflictsByDiscipline, setConflictsByDiscipline] = useState(null);
  const [costAnalysis, setCostAnalysis] = useState(null);
  const [performanceMetrics, setPerformanceMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAnalyticsData();
  }, []);

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true);
      
      // Fetch all analytics data concurrently
      const [overviewRes, disciplineRes, costRes, performanceRes] = await Promise.all([
        fetch('/api/analytics/portfolio/overview'),
        fetch('/api/analytics/conflicts/by-discipline'),
        fetch('/api/analytics/costs/analysis'),
        fetch('/api/analytics/performance/metrics')
      ]);

      if (!overviewRes.ok || !disciplineRes.ok || !costRes.ok || !performanceRes.ok) {
        throw new Error('Failed to fetch analytics data');
      }

      const [overview, discipline, cost, performance] = await Promise.all([
        overviewRes.json(),
        disciplineRes.json(),
        costRes.json(),
        performanceRes.json()
      ]);

      setPortfolioData(overview);
      setConflictsByDiscipline(discipline);
      setCostAnalysis(cost);
      setPerformanceMetrics(performance);
    } catch (err) {
      setError(err.message);
      console.error('Error fetching analytics data:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center' }}>
        <h2>Loading Portfolio Analytics...</h2>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '20px', color: 'red' }}>
        <h2>Error loading analytics: {error}</h2>
        <button onClick={fetchAnalyticsData} style={{ marginTop: '10px', padding: '5px 10px' }}>
          Retry
        </button>
      </div>
    );
  }

  // Chart configurations
  const conflictsBySeverityData = {
    labels: portfolioData?.conflicts_by_severity?.map(item => item.severity.charAt(0).toUpperCase() + item.severity.slice(1)) || [],
    datasets: [{
      label: 'Number of Conflicts',
      data: portfolioData?.conflicts_by_severity?.map(item => item.count) || [],
      backgroundColor: [
        'rgba(255, 99, 132, 0.6)',
        'rgba(54, 162, 235, 0.6)',
        'rgba(255, 205, 86, 0.6)',
        'rgba(75, 192, 192, 0.6)'
      ],
      borderColor: [
        'rgba(255, 99, 132, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 205, 86, 1)',
        'rgba(75, 192, 192, 1)'
      ],
      borderWidth: 1
    }]
  };

  const conflictsByTypeData = {
    labels: conflictsByDiscipline?.conflicts_by_type?.map(item => item.conflict_type) || [],
    datasets: [{
      label: 'Number of Conflicts',
      data: conflictsByDiscipline?.conflicts_by_type?.map(item => item.count) || [],
      backgroundColor: 'rgba(75, 192, 192, 0.6)',
      borderColor: 'rgba(75, 192, 192, 1)',
      borderWidth: 1
    }]
  };

  const costBreakdownData = {
    labels: costAnalysis?.project_cost_breakdown?.map(item => item.parameter_name) || [],
    datasets: [{
      label: 'Total Cost',
      data: costAnalysis?.project_cost_breakdown?.map(item => item.total_cost) || [],
      backgroundColor: 'rgba(255, 206, 86, 0.6)',
      borderColor: 'rgba(255, 206, 86, 1)',
      borderWidth: 1
    }]
  };

  const resolutionTimeData = {
    labels: performanceMetrics?.resolution_time_metrics?.map(item => item.conflict_type) || [],
    datasets: [{
      label: 'Average Resolution Time (Days)',
      data: performanceMetrics?.resolution_time_metrics?.map(item => item.avg_resolution_days) || [],
      backgroundColor: 'rgba(153, 102, 255, 0.6)',
      borderColor: 'rgba(153, 102, 255, 1)',
      borderWidth: 1
    }]
  };

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Portfolio Analytics Dashboard'
      },
    },
    scales: {
      y: {
        beginAtZero: true
      }
    }
  };

  const pieOptions = {
    responsive: true,
    plugins: {
      legend: {
        position: 'right',
      }
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <h1>Portfolio Analytics Dashboard</h1>
      
      {/* Overview Stats */}
      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
        gap: '20px', 
        marginBottom: '30px' 
      }}>
        <div style={{ 
          padding: '20px', 
          backgroundColor: '#f8f9fa', 
          borderRadius: '8px', 
          textAlign: 'center' 
        }}>
          <h3 style={{ margin: '0 0 10px 0', color: '#007bff' }}>Total Projects</h3>
          <p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>
            {portfolioData?.total_projects || 0}
          </p>
        </div>
        
        <div style={{ 
          padding: '20px', 
          backgroundColor: '#f8f9fa', 
          borderRadius: '8px', 
          textAlign: 'center' 
        }}>
          <h3 style={{ margin: '0 0 10px 0', color: '#28a745' }}>Active Projects</h3>
          <p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>
            {portfolioData?.active_projects || 0}
          </p>
        </div>
        
        <div style={{ 
          padding: '20px', 
          backgroundColor: '#f8f9fa', 
          borderRadius: '8px', 
          textAlign: 'center' 
        }}>
          <h3 style={{ margin: '0 0 10px 0', color: '#dc3545' }}>Total Conflicts</h3>
          <p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>
            {portfolioData?.total_conflicts || 0}
          </p>
        </div>
        
        <div style={{ 
          padding: '20px', 
          backgroundColor: '#f8f9fa', 
          borderRadius: '8px', 
          textAlign: 'center' 
        }}>
          <h3 style={{ margin: '0 0 10px 0', color: '#ffc107' }}>Avg Solution Confidence</h3>
          <p style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>
            {(portfolioData?.average_solution_confidence * 100).toFixed(1) || 0}%
          </p>
        </div>
      </div>

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px', marginBottom: '30px' }}>
        
        {/* Conflicts by Severity - Pie Chart */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3>Conflicts by Severity</h3>
          {portfolioData?.conflicts_by_severity?.length > 0 ? (
            <Pie data={conflictsBySeverityData} options={pieOptions} />
          ) : (
            <p>No conflict data available</p>
          )}
        </div>

        {/* Conflicts by Type - Bar Chart */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3>Conflicts by Type</h3>
          {conflictsByDiscipline?.conflicts_by_type?.length > 0 ? (
            <Bar data={conflictsByTypeData} options={chartOptions} />
          ) : (
            <p>No conflict type data available</p>
          )}
        </div>

        {/* Cost Breakdown */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3>Project Cost Breakdown</h3>
          {costAnalysis?.project_cost_breakdown?.length > 0 ? (
            <Bar data={costBreakdownData} options={chartOptions} />
          ) : (
            <p>No cost data available</p>
          )}
        </div>

        {/* Resolution Time Metrics */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3>Average Resolution Time</h3>
          {performanceMetrics?.resolution_time_metrics?.length > 0 ? (
            <Bar data={resolutionTimeData} options={chartOptions} />
          ) : (
            <p>No resolution time data available</p>
          )}
        </div>
      </div>

      {/* Additional Analytics Tables */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
        
        {/* Solution Success Rates */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3>Solution Success Rates</h3>
          {performanceMetrics?.solution_success_rates?.length > 0 ? (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa' }}>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd' }}>Solution Type</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd' }}>Success Rate</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd' }}>Feedback Count</th>
                </tr>
              </thead>
              <tbody>
                {performanceMetrics.solution_success_rates.map((item, index) => (
                  <tr key={index}>
                    <td style={{ padding: '10px', border: '1px solid #ddd' }}>{item.solution_type}</td>
                    <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                      {(item.success_rate * 100).toFixed(1)}%
                    </td>
                    <td style={{ padding: '10px', border: '1px solid #ddd' }}>{item.feedback_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No solution success rate data available</p>
          )}
        </div>

        {/* Historical Resolution Costs */}
        <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3>Historical Resolution Costs</h3>
          {costAnalysis?.historical_resolution_costs?.length > 0 ? (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f8f9fa' }}>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd' }}>Conflict Type</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd' }}>Avg Cost</th>
                  <th style={{ padding: '10px', textAlign: 'left', border: '1px solid #ddd' }}>Sample Size</th>
                </tr>
              </thead>
              <tbody>
                {costAnalysis.historical_resolution_costs.map((item, index) => (
                  <tr key={index}>
                    <td style={{ padding: '10px', border: '1px solid #ddd' }}>{item.conflict_type}</td>
                    <td style={{ padding: '10px', border: '1px solid #ddd' }}>
                      ${item.avg_cost.toLocaleString()}
                    </td>
                    <td style={{ padding: '10px', border: '1px solid #ddd' }}>{item.sample_size}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>No historical cost data available</p>
          )}
        </div>
      </div>

      {/* Refresh Button */}
      <div style={{ marginTop: '30px', textAlign: 'center' }}>
        <button 
          onClick={fetchAnalyticsData}
          style={{
            padding: '10px 20px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '5px',
            cursor: 'pointer',
            fontSize: '16px'
          }}
        >
          Refresh Analytics
        </button>
      </div>
    </div>
  );
}

export default PortfolioDashboard;