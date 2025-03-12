import React from 'react';
import DownloadProvider from './DownloadsContext';
import { DownloadsPanelComponent } from './DownloadsPanelComponent';


export const DownloadsPanelWrapperProviderComponent: React.FC = (): JSX.Element => {
    return (
        <div className='overflow-auto'>
            <DownloadProvider>
                <DownloadsPanelComponent />
            </DownloadProvider>
        </div>
    );
}
