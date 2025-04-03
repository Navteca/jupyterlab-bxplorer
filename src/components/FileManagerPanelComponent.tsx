import React from 'react'
import { DownloadHistoryProvider } from '../contexts/DownloadHistoryContext';
import BasicTabs from './BasicTabs';
interface FileManagerPanelComponentProps {
     downloadsFolder: string;
}

const FileManagerPanelComponent: React.FC<FileManagerPanelComponentProps> = (props): JSX.Element => {
     return (
          <div style={{ width: "100%", minWidth: "400px", height: "100vh" }}>
               <DownloadHistoryProvider>
                    <BasicTabs downloadsFolder={props.downloadsFolder} />
               </DownloadHistoryProvider>
          </div>
     );
}

export default FileManagerPanelComponent;