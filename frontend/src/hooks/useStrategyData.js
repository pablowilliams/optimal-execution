/**
 * React-query hooks for REST API endpoints.
 */
import { useQuery, useMutation } from '@tanstack/react-query';
import axios from 'axios';
import toast from 'react-hot-toast';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({ baseURL: API_URL });

// Health check
export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => api.get('/health').then((r) => r.data),
    refetchInterval: 10000,
  });
}

// Calibrate
export function useCalibrate() {
  return useMutation({
    mutationFn: (useSynthetic = true) =>
      api.post('/calibrate', { use_synthetic: useSynthetic }).then((r) => r.data),
    onSuccess: () => toast.success('Calibration complete'),
    onError: (e) => toast.error(`Calibration failed: ${e.message}`),
  });
}

// Run strategy
export function useRunStrategy() {
  return useMutation({
    mutationFn: (params) => api.post('/run-strategy', params).then((r) => r.data),
    onError: (e) => toast.error(`Strategy failed: ${e.message}`),
  });
}

// Efficient frontier
export function useEfficientFrontier() {
  return useMutation({
    mutationFn: (params) => api.post('/efficient-frontier', params).then((r) => r.data),
    onError: (e) => toast.error(`Frontier failed: ${e.message}`),
  });
}

// Sensitivity heatmap
export function useSensitivity() {
  return useMutation({
    mutationFn: (params) => api.post('/sensitivity', params).then((r) => r.data),
    onError: (e) => toast.error(`Sensitivity failed: ${e.message}`),
  });
}

// Train RL
export function useTrainRL() {
  return useMutation({
    mutationFn: (params) => api.post('/train-rl', params).then((r) => r.data),
    onSuccess: (data) => toast.success(`Training started: job ${data.job_id}`),
    onError: (e) => toast.error(`Training failed: ${e.message}`),
  });
}

// Training status
export function useTrainStatus(jobId) {
  return useQuery({
    queryKey: ['train-status', jobId],
    queryFn: () => api.get(`/train-status/${jobId}`).then((r) => r.data),
    enabled: !!jobId,
    refetchInterval: 2000,
  });
}

// Training curve
export function useTrainingCurve() {
  return useQuery({
    queryKey: ['training-curve'],
    queryFn: () => api.get('/training-curve').then((r) => r.data),
    enabled: false,
  });
}

// Compare strategies
export function useCompare() {
  return useMutation({
    mutationFn: (params) => api.post('/compare', params).then((r) => r.data),
    onError: (e) => toast.error(`Comparison failed: ${e.message}`),
  });
}
