import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import App from './App';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 30000,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#0D1320',
            color: '#E8ECF0',
            border: '1px solid #1A2535',
          },
          error: {
            style: { borderColor: '#E05C5C' },
          },
          success: {
            style: { borderColor: '#4CAF8C' },
          },
        }}
      />
    </QueryClientProvider>
  </React.StrictMode>
);
