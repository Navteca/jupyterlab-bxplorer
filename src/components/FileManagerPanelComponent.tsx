import React from 'react'
import BasicTabs from './BasicTabs';

interface FileManagerPanelComponentProps {
     downloadsFolder: string;
}

const FileManagerPanelComponent: React.FC<FileManagerPanelComponentProps> = (props): JSX.Element => {
     return (
          <div style={{ width: "100%", minWidth: "400px", height: "100vh" }}>
               <BasicTabs downloadsFolder={props.downloadsFolder} />
          </div>
     );
}

export default FileManagerPanelComponent;