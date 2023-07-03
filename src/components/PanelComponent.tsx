import React, { useState, useEffect } from 'react';
import Tab from 'react-bootstrap/Tab';
import Tabs from 'react-bootstrap/Tabs';
import Stack from 'react-bootstrap/Stack';
import FitsProvider from './FitsContext';
import FavoriteProvider from './FavoriteContext';
import DownloadProvider from './DownloadsContext';
import FileBrowserComponent from './FileBrowserComponent';
import OpenDataDropdownComponent from './OpenDataDropdownComponent';
import { FileArray } from 'chonky-navteca';
import { requestAPI } from '../handler'

export const PanelComponent: React.FC = () => {
    const [key, setKey] = useState('private');
    const [selectedOpenDataSource, setSelectedOpenDataSource] = useState<string>('AWS')
    const [, updateState] = React.useState({});

    const forceUpdate = React.useCallback(() => updateState({}), []);
    const getRootFileStructure = async (bucket: string = '', prefix: string = '/', clientType: string, source?: string): Promise<FileArray> => {
        const response = await requestAPI<any>('get_file_data',
            {
                method: "POST",
                body: JSON.stringify({ bucket, prefix, clientType, source })
            });
        return response
    };

    useEffect(() => {
        const timer = setTimeout(() => {
            console.log('Re-rendering')
            forceUpdate()
        }, 30000);
        return () => clearTimeout(timer);
    }, [])


    return (
        <div style={{ width: "100%", minWidth: "400px" }}>
            <FavoriteProvider>
                <DownloadProvider>
                    <FitsProvider>
                        <Tabs
                            defaultActiveKey='nasa'
                            id='buckets-tabs'
                            activeKey={key}
                            onSelect={(k) => setKey(k!)}
                            justify>
                            <Tab eventKey='private' title='Private'>
                                <FileBrowserComponent getRootFileStructure={getRootFileStructure} instanceId='private' />
                            </Tab>
                            <Tab eventKey='public' title='Public'>
                                <Stack gap={2} className="pt-2">
                                    <OpenDataDropdownComponent setODSource={setSelectedOpenDataSource} />
                                    <FileBrowserComponent getRootFileStructure={getRootFileStructure} instanceId='public' selectedOpenDataSource={selectedOpenDataSource} />
                                </Stack>
                            </Tab>
                            <Tab eventKey='favorites' title='Favorites'>
                                <FileBrowserComponent getRootFileStructure={getRootFileStructure} instanceId='favorites' />
                            </Tab>
                        </Tabs>
                    </FitsProvider>
                </DownloadProvider>
            </FavoriteProvider>
        </div >

    );
}
