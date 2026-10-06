import axios from 'axios';
import { Platform } from 'react-native';

import { getAccessToken } from './auth';

const baseURL = process.env.EXPO_PUBLIC_API_URL ?? (
  Platform.OS === 'web'
    ? 'http://127.0.0.1:5000/api'
    : 'http://192.168.1.39:5000/api'
);

const API = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

API.interceptors.request.use(async (config) => {
  if (!config.url?.startsWith('/auth/')) {
    const token = await getAccessToken();
    if (token) {
      config.headers.set('Authorization', `Bearer ${token}`);
    }
  }

  return config;
});

export default API;