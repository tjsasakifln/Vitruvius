import { render, screen } from '@testing-library/react';
import App from './App';

test('renders Vitruvius header', () => {
  render(<App />);
  const headerElement = screen.getByText(/Vitruvius/i);
  expect(headerElement).toBeInTheDocument();
});

test('renders dashboard component', () => {
  render(<App />);
  const dashboardElement = screen.getByText(/AI-Powered BIM Project Coordination Platform/i);
  expect(dashboardElement).toBeInTheDocument();
});