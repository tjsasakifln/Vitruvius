/*
 * Production use requires a separate commercial license from the Licensor.
 * For commercial licenses, please contact Tiago Sasaki at tiago@confenge.com.br.
 */

import { render, screen } from '@testing-library/react';
import App from './App';

test('renders Vitruvius header', () => {
  render(<App />);
  const headerElement = screen.getByText(/Vitruvius/i);
  expect(headerElement).toBeInTheDocument();
});

test('renders dashboard component', () => {
  render(<App />);
  const dashboardElement = screen.getByText(/BIM Project Coordination Platform with Prescriptive Analysis Engine/i);
  expect(dashboardElement).toBeInTheDocument();
});
