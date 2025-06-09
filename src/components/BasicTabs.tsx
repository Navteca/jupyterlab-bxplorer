import React from 'react';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Box from '@mui/material/Box';
import CustomTabPanel from './CustomTabPanel';
import FMViewComponent from './FMViewComponent';
import { DownloadHistoryProvider } from '../contexts/DownloadHistoryContext';
import DownloadHistory from './DownloadHistory';
import Chatlas from './Chatlas';

interface BasicTabsProps {
  downloadsFolder: string;
  atlasId: string;
}

const BasicTabs: React.FC<BasicTabsProps> = (props): JSX.Element => {
  const [value, setValue] = React.useState(0);

  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    setValue(newValue);
  };

  const a11yProps = (index: number) => ({
    id: `simple-tab-${index}`,
    'aria-controls': `simple-tabpanel-${index}`
  });

  return (
    <DownloadHistoryProvider>
      <Box sx={{ width: '100%' }}>
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs
            value={value}
            onChange={handleChange}
            aria-label="basic tabs example"
          >
            <Tab label="Favorites" {...a11yProps(0)} />
            <Tab label="Private" {...a11yProps(1)} />
            <Tab label="Public" {...a11yProps(2)} />
            <Tab label="Download History" {...a11yProps(3)} />
            <Tab label="Chatlas" {...a11yProps(4)} />
          </Tabs>
        </Box>
        <CustomTabPanel value={value} index={0}>
          <FMViewComponent
            downloadsFolder={props.downloadsFolder}
            clientType="favorites"
            folderOptions={['Open', '|', 'Remove from favorites', 'Details']}
          />
        </CustomTabPanel>
        <CustomTabPanel value={value} index={1}>
          <FMViewComponent
            downloadsFolder={props.downloadsFolder}
            clientType="private"
            folderOptions={['Open', '|', 'Add to favorites', 'Details']}
          />
        </CustomTabPanel>
        <CustomTabPanel value={value} index={2}>
          <FMViewComponent
            downloadsFolder={props.downloadsFolder}
            clientType="public"
            folderOptions={['Open', '|', 'Add to favorites', 'Details']}
          />
        </CustomTabPanel>
        <CustomTabPanel value={value} index={3}>
          <DownloadHistory />
        </CustomTabPanel>
        <CustomTabPanel value={value} index={4}>
          <Chatlas atlasId={props.atlasId} />
        </CustomTabPanel>
      </Box>
    </DownloadHistoryProvider>
  );
};

export default BasicTabs;
