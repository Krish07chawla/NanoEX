import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import './index.css';
import { get, refreshAccessToken } from './services/api';
import { useAuthStore } from './store/authStore';
import type { User } from './types';

/** On page load, try the httpOnly refresh cookie to restore the session. */
async function bootstrap() {
  const token = await refreshAccessToken();
  if (token) {
    try {
      useAuthStore.getState().setUser(await get<User>('/users/me'));
    } catch {
      useAuthStore.getState().clear();
    }
  }
  useAuthStore.getState().setBootstrapped();
}
bootstrap();

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
