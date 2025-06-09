import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Typography,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  CircularProgress
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import DeleteIcon from '@mui/icons-material/Delete';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import { requestAPI } from '../handler';
import {
  DownloadItem,
  useDownloadHistory
} from '../contexts/DownloadHistoryContext';

const DownloadHistory: React.FC = (): JSX.Element => {
  const { history, loading, fetchHistory } = useDownloadHistory();
  const [pollInterval, setPollInterval] = useState<number>(2000);
  const timerRef = useRef<number | null>(null);

  // Borrar todos los registros
  const handleClearAll = async () => {
    try {
      const result: any = await requestAPI('download_history?action=clean', {
        method: 'DELETE'
      });
      console.log(result.message);
      await fetchHistory();
    } catch (error) {
      console.error(error);
    }
  };

  // Borrar un ítem individual
  const handleDeleteItem = async (id: number) => {
    try {
      const result: any = await requestAPI(`download_history?id=${id}`, {
        method: 'DELETE'
      });
      console.log(result.message);
      await fetchHistory();
    } catch (error) {
      console.error(error);
    }
  };

  // Polling
  const pollHistory = async () => {
    const newHistory = await fetchHistory();
    const anyDownloading = newHistory.some(
      (item: DownloadItem) => item.status === 'downloading'
    );
    if (anyDownloading) {
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

  useEffect(() => {
    pollHistory();
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  return (
    <Box
      sx={{
        // Llenar el espacio disponible en el panel JupyterLab
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        width: '100%',
        overflow: 'hidden', // Sin scroll en el contenedor externo
        bgcolor: 'background.default'
      }}
    >
      <Box
        sx={{
          // Panel interno que se centrará horizontalmente si se quiere un ancho máx
          maxWidth: 600,
          width: '100%',
          margin: '0 auto',

          // Estructura en columna
          display: 'flex',
          flexDirection: 'column',
          flex: 1, // Ocupa el espacio vertical
          minHeight: 0, // Permite que el hijo con overflow se desplace
          bgcolor: 'background.paper',
          boxShadow: 3,
          borderRadius: 2
        }}
      >
        {/* Cabecera */}
        <Box
          sx={{
            flex: '0 0 auto',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            p: 1,
            borderBottom: 1,
            borderColor: 'divider'
          }}
        >
          <Typography variant="h6" component="h2">
            Download History
          </Typography>
          <Box>
            <IconButton
              onClick={fetchHistory}
              color="primary"
              aria-label="refresh"
              sx={{ mr: 1 }}
            >
              <RefreshIcon />
            </IconButton>
            <IconButton
              onClick={handleClearAll}
              color="secondary"
              aria-label="clear all"
            >
              <DeleteSweepIcon />
            </IconButton>
          </Box>
        </Box>

        {/* Contenido scrollable: la lista */}
        <Box
          sx={{
            flex: '1 1 auto', // Se expande para ocupar el espacio sobrante
            minHeight: 0, // Crucial para permitir el scroll interno
            overflowY: 'auto', // Scrollbar solo aquí
            p: 1
          }}
        >
          {loading ? (
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100%'
              }}
            >
              <CircularProgress />
            </Box>
          ) : (
            <List sx={{ p: 0 }}>
              {history.length > 0 ? (
                history.map(download => (
                  <ListItem key={download.id} divider>
                    <ListItemText
                      primary={
                        <span style={{ fontSize: '0.95rem' }}>
                          <strong>
                            {download.bucket}/{download.key}
                          </strong>
                        </span>
                      }
                      secondary={
                        <span style={{ fontSize: '0.85rem' }}>
                          Start:{' '}
                          {new Date(download.start_time).toLocaleString()}
                          {download.end_time
                            ? ` | End: ${new Date(download.end_time).toLocaleString()}`
                            : ''}
                          <div />
                          Status: {download.status}
                          {download.error_message
                            ? ` | Error: ${download.error_message}`
                            : ''}
                        </span>
                      }
                    />
                    <ListItemSecondaryAction>
                      <IconButton
                        edge="end"
                        onClick={() => handleDeleteItem(download.id)}
                        aria-label="delete"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </ListItemSecondaryAction>
                  </ListItem>
                ))
              ) : (
                <Typography sx={{ textAlign: 'center', py: 2 }}>
                  No downloads available
                </Typography>
              )}
            </List>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default DownloadHistory;
