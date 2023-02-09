import React, { useEffect, useState } from 'react';
import { DownloadContextType } from './downloads'
import { requestAPI } from '../handler'
import { IDownloadsProps, IObjectToDownloadArgs, IDeleteDownloads } from './CustomProps'

type DownloadProviderProps = {
    children: React.ReactNode
}

export const DownloadContext = React.createContext<DownloadContextType | null>(null);

const DownloadProvider: React.FC<DownloadProviderProps> = ({ children }) => {
    const [downloads, setDownload] = useState<IDownloadsProps>([])

    useEffect(() => {
        getDownloadsList()
    }, []);

    const downloadObject = async ({ bucket, prefix, source = '', downloadPath = 'Downloads' }: IObjectToDownloadArgs): Promise<void> => {
        try {
            await requestAPI<any>('downloads',
                {
                    method: "POST",
                    body: JSON.stringify({ bucket, prefix, source, downloadPath })
                })
            getDownloadsList()
        } catch (e) {
            console.log(`There has been an error trying to download an object => ${JSON.stringify(e, null, 2)}`)
        }
    }

    const deleteDownloadFromList = async ({ id, pid, deleteAll = false }: IDeleteDownloads): Promise<void> => {
        try {
            await requestAPI<any>('downloads',
                {
                    method: "DELETE",
                    body: JSON.stringify({ deleteAll, id, pid })
                });
            getDownloadsList()
        } catch (e) {
            console.log(`There has been an error trying to delete an object from the list of downloads => ${e}`)
        }
    }

    const getDownloadsList = async (): Promise<void> => {
        const response = await requestAPI<any>('downloads');
        setDownload(response.reverse())
    }

    return (
        <DownloadContext.Provider value={{ downloads, getDownloadsList, downloadObject, deleteDownloadFromList }}>
            {children}
        </DownloadContext.Provider>
    );
}

export default DownloadProvider;