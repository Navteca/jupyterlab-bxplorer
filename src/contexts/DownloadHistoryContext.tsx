import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { requestAPI } from '../handler';

export interface DownloadItem {
  id: number;
  bucket: string;
  key: string;
  local_path: string;
  status: string;
  error_message?: string;
  start_time: string;
  end_time?: string;
}

interface DownloadHistoryContextType {
  history: DownloadItem[];
  loading: boolean;
  fetchHistory: () => Promise<DownloadItem[]>;
  startPolling: () => void;
}

const DownloadHistoryContext = createContext<DownloadHistoryContextType | undefined>(undefined);

export const DownloadHistoryProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [history, setHistory] = useState<DownloadItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [pollInterval, setPollInterval] = useState<number>(2000);
  const timerRef = useRef<number | null>(null);

  const fetchHistory = async (): Promise<DownloadItem[]> => {
    setLoading(true);
    try {
      const data = await requestAPI('download_history', {
        method: 'GET',
      });

      const historyData: DownloadItem[] = data as DownloadItem[];
      setHistory(historyData);
      setLoading(false);
      return historyData;
    } catch (error) {
      console.error('Error fetching download history:', error);
      setLoading(false);
      return [];
    }
  };

  const pollHistory = async () => {
    await fetchHistory();
    const anyDownloading = history.some((item) => item.status === 'downloading');
    if (anyDownloading) {
      // Incremento geométrico del intervalo, hasta 30 segundos
      const newInterval = Math.min(pollInterval * 1.5, 30000);
      setPollInterval(newInterval);
      timerRef.current = window.setTimeout(pollHistory, newInterval);
    } else {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      setPollInterval(2000);
    }
  };

  const startPolling = () => {
    pollHistory();
  };

  useEffect(() => {
    // Opcionalmente, se puede iniciar el fetch inmediato al montar el provider:
    fetchHistory();
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  return (
    <DownloadHistoryContext.Provider value={{ history, loading, fetchHistory, startPolling }}>
      {children}
    </DownloadHistoryContext.Provider>
  );
};

export const useDownloadHistory = () => {
  const context = useContext(DownloadHistoryContext);
  if (!context) {
    throw new Error('useDownloadHistory must be used within a DownloadHistoryProvider');
  }
  return context;
};