import { IResponse, IDownloadsProps, IObjectToDownloadArgs, IDeleteDownloads } from './CustomProps'

export type DownloadContextType = {
    downloads: IDownloadsProps;
    getDownloadsList: () => Promise<void>;
    downloadObject: (obj: IObjectToDownloadArgs) => Promise<void>;
    deleteDownloadFromList: (obj: IDeleteDownloads) => Promise<void>;
};