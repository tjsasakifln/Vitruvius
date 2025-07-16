import React, { useState, useEffect } from 'react';

function SolutionFeedback({ projectId, conflictId }) {
  const [solutions, setSolutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [selectedSolution, setSelectedSolution] = useState(null);
  const [customSolution, setCustomSolution] = useState('');
  const [implementationNotes, setImplementationNotes] = useState('');
  const [effectivenessRating, setEffectivenessRating] = useState(null);
  const [feedbackType, setFeedbackType] = useState('');

  useEffect(() => {
    fetchSolutions();
  }, [projectId, conflictId]);

  const fetchSolutions = async () => {
    try {
      const response = await fetch(`/api/projects/${projectId}/conflicts/${conflictId}/solutions`);
      if (response.ok) {
        const data = await response.json();
        setSolutions(data.solutions || []);
      }
    } catch (error) {
      console.error('Error fetching solutions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSolutionSelection = (solutionId) => {
    setSelectedSolution(solutionId);
    setFeedbackType('selected_suggested');
    setCustomSolution('');
  };

  const handleCustomSolutionToggle = () => {
    setSelectedSolution(null);
    setFeedbackType('custom_solution');
  };

  const handleSubmitFeedback = async () => {
    if (!feedbackType) {
      alert('Por favor, selecione uma solução sugerida ou descreva uma solução customizada.');
      return;
    }

    if (feedbackType === 'selected_suggested' && !selectedSolution) {
      alert('Por favor, selecione uma solução sugerida.');
      return;
    }

    if (feedbackType === 'custom_solution' && !customSolution.trim()) {
      alert('Por favor, descreva sua solução customizada.');
      return;
    }

    setSubmitting(true);

    try {
      const feedbackData = {
        feedback_type: feedbackType,
        solution_id: selectedSolution,
        custom_solution_description: customSolution,
        implementation_notes: implementationNotes,
        effectiveness_rating: effectivenessRating
      };

      const response = await fetch(`/api/projects/${projectId}/conflicts/${conflictId}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(feedbackData)
      });

      if (response.ok) {
        alert('Feedback enviado com sucesso! Obrigado por contribuir para a melhoria do sistema.');
        // Reset form
        setSelectedSolution(null);
        setCustomSolution('');
        setImplementationNotes('');
        setEffectivenessRating(null);
        setFeedbackType('');
      } else {
        const errorData = await response.json();
        alert(`Erro ao enviar feedback: ${errorData.detail}`);
      }
    } catch (error) {
      alert('Erro ao enviar feedback. Tente novamente.');
      console.error('Error submitting feedback:', error);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return <div>Carregando soluções...</div>;
  }

  return (
    <div style={{ 
      border: '1px solid #ddd', 
      borderRadius: '8px', 
      padding: '20px', 
      margin: '20px 0',
      backgroundColor: '#f9f9f9'
    }}>
      <h3>Soluções do Motor de Análise Prescritiva</h3>
      
      {solutions.length > 0 ? (
        <div>
          <h4>Soluções Sugeridas:</h4>
          {solutions.map(solution => (
            <div key={solution.id} style={{
              border: '1px solid #ccc',
              borderRadius: '5px',
              padding: '15px',
              margin: '10px 0',
              backgroundColor: selectedSolution === solution.id ? '#e3f2fd' : '#fff'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', marginBottom: '10px' }}>
                <input
                  type="radio"
                  id={`solution-${solution.id}`}
                  name="solution"
                  value={solution.id}
                  checked={selectedSolution === solution.id}
                  onChange={() => handleSolutionSelection(solution.id)}
                  style={{ marginRight: '10px' }}
                />
                <label htmlFor={`solution-${solution.id}`} style={{ fontWeight: 'bold' }}>
                  {solution.type}
                </label>
              </div>
              
              <p><strong>Descrição:</strong> {solution.description}</p>
              
              <div style={{ display: 'flex', gap: '20px', fontSize: '14px', color: '#666' }}>
                {solution.estimated_cost && (
                  <span><strong>Custo Estimado:</strong> R$ {solution.estimated_cost.toFixed(2)}</span>
                )}
                {solution.estimated_time && (
                  <span><strong>Tempo Estimado:</strong> {solution.estimated_time} dias</span>
                )}
                {solution.confidence_score && (
                  <span><strong>Confiança:</strong> {solution.confidence_score}%</span>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p>Nenhuma solução sugerida encontrada.</p>
      )}

      <div style={{ marginTop: '20px' }}>
        <h4>Ou descreva sua própria solução:</h4>
        <div style={{ marginBottom: '10px' }}>
          <input
            type="radio"
            id="custom-solution"
            name="solution"
            checked={feedbackType === 'custom_solution'}
            onChange={handleCustomSolutionToggle}
            style={{ marginRight: '10px' }}
          />
          <label htmlFor="custom-solution">Solução customizada</label>
        </div>
        
        {feedbackType === 'custom_solution' && (
          <textarea
            value={customSolution}
            onChange={(e) => setCustomSolution(e.target.value)}
            placeholder="Descreva a solução que você implementou ou pretende implementar..."
            style={{
              width: '100%',
              minHeight: '100px',
              padding: '10px',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontSize: '14px'
            }}
          />
        )}
      </div>

      {feedbackType && (
        <div style={{ marginTop: '20px' }}>
          <h4>Informações Adicionais (Opcional):</h4>
          
          <div style={{ marginBottom: '15px' }}>
            <label>Notas de Implementação:</label>
            <textarea
              value={implementationNotes}
              onChange={(e) => setImplementationNotes(e.target.value)}
              placeholder="Descreva detalhes da implementação, desafios encontrados, etc."
              style={{
                width: '100%',
                minHeight: '80px',
                padding: '10px',
                border: '1px solid #ddd',
                borderRadius: '4px',
                fontSize: '14px',
                marginTop: '5px'
              }}
            />
          </div>

          <div style={{ marginBottom: '15px' }}>
            <label>Avaliação da Eficácia (1-5):</label>
            <div style={{ marginTop: '5px' }}>
              {[1, 2, 3, 4, 5].map(rating => (
                <label key={rating} style={{ marginRight: '15px' }}>
                  <input
                    type="radio"
                    name="effectiveness"
                    value={rating}
                    checked={effectivenessRating === rating}
                    onChange={(e) => setEffectivenessRating(parseInt(e.target.value))}
                    style={{ marginRight: '5px' }}
                  />
                  {rating}
                </label>
              ))}
            </div>
          </div>

          <button
            onClick={handleSubmitFeedback}
            disabled={submitting}
            style={{
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '4px',
              cursor: submitting ? 'not-allowed' : 'pointer',
              fontSize: '16px'
            }}
          >
            {submitting ? 'Enviando...' : 'Enviar Feedback'}
          </button>
        </div>
      )}
    </div>
  );
}

export default SolutionFeedback;