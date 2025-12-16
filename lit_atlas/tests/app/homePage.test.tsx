import { render } from '@testing-library/react';
import Home from '@/app/page';

describe('Home Page', () => {
  it('renders the application shell', () => {
    const { getByTestId } = render(<Home />);
    expect(getByTestId('app-shell')).toBeInTheDocument();
  });
});
