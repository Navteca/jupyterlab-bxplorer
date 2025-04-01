import React from 'react';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Box from '@mui/material/Box';
import CustomTabPanel from './CustomTabPanel';
import FMViewComponent from './FMViewComponent';

interface BasicTabsProps {
  downloadsFolder: string;
}

const BasicTabs: React.FC<BasicTabsProps> = (props): JSX.Element => {
  const [value, setValue] = React.useState(0);

  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    setValue(newValue);
  };


  const a11yProps = (index: number) => ({
    id: `simple-tab-${index}`,
    'aria-controls': `simple-tabpanel-${index}`,
  });

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={value} onChange={handleChange} aria-label="basic tabs example">
          <Tab label="Private" {...a11yProps(0)} />
          <Tab label="Public" {...a11yProps(1)} />
          {/* <Tab label="Favorites" {...a11yProps(2)} /> */}
        </Tabs>
      </Box>
      <CustomTabPanel value={value} index={0}>
        <FMViewComponent downloadsFolder={props.downloadsFolder} clientType="private" />
      </CustomTabPanel>
      <CustomTabPanel value={value} index={1}>
        <FMViewComponent downloadsFolder={props.downloadsFolder} clientType="public" />
      </CustomTabPanel>
      {/* <CustomTabPanel value={value} index={2}>
        <FMViewComponent downloadsFolder={props.downloadsFolder} clientType="favorites" />
      </CustomTabPanel> */}
    </Box>
  );
};

export default BasicTabs;
