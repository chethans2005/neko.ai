import axios from 'axios';

const API_BASE = '/api';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

let authToken = localStorage.getItem('auth_token') || null;

export const setAuthToken = (token) => {
  authToken = token || null;
  if (token) {
    localStorage.setItem('auth_token', token);
  } else {
    localStorage.removeItem('auth_token');
  }
};

api.interceptors.request.use((config) => {
  if (authToken) {
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

// Auth endpoints
export const signup = async (name, email, password) => {
  const response = await api.post('/auth/signup', { name, email, password });
  return response.data;
};

export const login = async (email, password) => {
  const response = await api.post('/auth/login', { email, password });
  return response.data;
};

export const loginWithGoogle = async (idToken) => {
  const response = await api.post('/auth/google', { id_token: idToken });
  return response.data;
};

export const getMe = async () => {
  const response = await api.get('/auth/me');
  return response.data;
};

export const getHistory = async () => {
  const response = await api.get('/history');
  return response.data;
};

export const deleteHistoryItem = async (historyId) => {
  const response = await api.delete(`/history/${historyId}`);
  return response.data;
};

export const downloadHistoryPpt = async (historyId) => {
  const response = await api.get(`/history/download/${historyId}`, { responseType: 'blob' });
  return response;
};

// Session endpoints
export const startSession = async (template = 'professional', tone = 'professional') => {
  const response = await api.post('/session/start', { template, tone });
  return response.data;
};

export const getSession = async (sessionId) => {
  const response = await api.get(`/session/${sessionId}`);
  return response.data;
};

export const deleteSession = async (sessionId) => {
  const response = await api.delete(`/session/${sessionId}`);
  return response.data;
};

// Generation endpoints
export const generatePresentation = async (sessionId, topic, numSlides = 5, additionalContext = null) => {
  const response = await api.post('/generate', {
    session_id: sessionId,
    topic,
    num_slides: numSlides,
    additional_context: additionalContext,
  });
  return response.data;
};

export const generatePresentationSync = async (sessionId, topic, numSlides = 5, additionalContext = null) => {
  const response = await api.post('/generate-sync', {
    session_id: sessionId,
    topic,
    num_slides: numSlides,
    additional_context: additionalContext,
  });
  return response.data;
};

// Job status
export const getJobStatus = async (jobId) => {
  const response = await api.get(`/status/${jobId}`);
  return response.data;
};

// Preview
export const getPreview = async (sessionId) => {
  const response = await api.get(`/preview/${sessionId}`);
  return response.data;
};

// Slide operations
export const updateSlide = async (sessionId, slideNumber, instruction) => {
  const response = await api.post('/update-slide', {
    session_id: sessionId,
    slide_number: slideNumber,
    instruction,
  });
  return response.data;
};

export const rollbackSlide = async (sessionId, slideNumber, versionIndex) => {
  const response = await api.post('/rollback-slide', {
    session_id: sessionId,
    slide_number: slideNumber,
    version_index: versionIndex,
  });
  return response.data;
};

export const getSlideHistory = async (sessionId, slideNumber) => {
  const response = await api.get(`/slide-history/${sessionId}/${slideNumber}`);
  return response.data;
};

// Download
export const getDownloadUrl = (sessionId) => {
  return `${API_BASE}/download/${sessionId}`;
};

export const downloadSessionPpt = async (sessionId) => {
  const response = await api.get(`/download/${sessionId}`, { responseType: 'blob' });
  return response;
};

// Templates
export const getTemplates = async () => {
  const response = await api.get('/templates');
  return response.data;
};

export const updateSessionTemplate = async (sessionId, template) => {
  const response = await api.post(`/session/${sessionId}/template?template=${template}`);
  return response.data;
};

// AI Status
export const getAIStatus = async () => {
  const response = await api.get('/ai/status');
  return response.data;
};

// Chat History
export const getChatHistory = async (sessionId) => {
  const response = await api.get(`/chat/${sessionId}`);
  return response.data;
};

// Helper function to poll job status
export const pollJobStatus = async (jobId, onProgress, interval = 1000) => {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const status = await getJobStatus(jobId);
        
        if (onProgress) {
          onProgress(status);
        }
        
        if (status.status === 'completed') {
          resolve(status);
        } else if (status.status === 'failed') {
          reject(new Error(status.error || 'Job failed'));
        } else {
          setTimeout(poll, interval);
        }
      } catch (error) {
        reject(error);
      }
    };
    
    poll();
  });
};

export default api;
