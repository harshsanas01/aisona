import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { RoleProvider } from './RoleContext';
import { ToastProvider } from '../components/ui/Toast';
import { TranscriptDrawerProvider } from '../features/transcript-viewer/TranscriptDrawerContext';
import '../components/ui/ui.css';
import '../styles/global.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <RoleProvider>
        <ToastProvider>
          <TranscriptDrawerProvider>
            <App />
          </TranscriptDrawerProvider>
        </ToastProvider>
      </RoleProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
