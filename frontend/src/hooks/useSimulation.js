/**
 * WebSocket hook for live simulation playback.
 */
import { useState, useRef, useCallback, useEffect } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export function useSimulation() {
  const [trajectoryData, setTrajectoryData] = useState([]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const wsRef = useRef(null);
  const bufferRef = useRef([]);
  const timerRef = useRef(null);
  const speedRef = useRef(1);

  const play = useCallback(({ strategy, X, T, N, lambda_risk }) => {
    // Clean up existing connection
    if (wsRef.current) {
      wsRef.current.close();
    }

    setTrajectoryData([]);
    setCurrentStep(0);
    setIsPlaying(true);
    bufferRef.current = [];

    const ws = new WebSocket(`${WS_URL}/ws/simulate`);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ strategy, X, T, N, lambda_risk }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.error) {
        setIsPlaying(false);
        return;
      }

      if (data.done) {
        setIsPlaying(false);
        return;
      }

      // Buffer messages and release at controlled rate
      bufferRef.current.push(data);

      setTrajectoryData((prev) => [...prev, data]);
      setCurrentStep(data.step);
    };

    ws.onclose = () => {
      setIsPlaying(false);
    };

    ws.onerror = () => {
      setIsPlaying(false);
    };
  }, []);

  const pause = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    setIsPlaying(false);
  }, []);

  const reset = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    setTrajectoryData([]);
    setCurrentStep(0);
    setIsPlaying(false);
    bufferRef.current = [];
  }, []);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  return {
    trajectoryData,
    isPlaying,
    play,
    pause,
    reset,
    currentStep,
  };
}
