import React from 'react';
import Box from '@mui/material/Box';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const CustomTabPanel: React.FC<TabPanelProps> = (
  props: TabPanelProps
): JSX.Element => {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
      style={{ height: 'calc(100vh - 48px)' }}
    >
      {value === index && (
        <Box sx={{ p: 3, height: '100%', overflowY: 'auto' }}>{children}</Box>
      )}
    </div>
  );
};

export default CustomTabPanel;
