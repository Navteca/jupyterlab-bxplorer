import { FileArray } from 'chonky-navteca';

export interface IModalHandlerProps {
    handleClose: () => void;
    show: boolean;
    setDownloadPath?: React.Dispatch<React.SetStateAction<string>>
    // stateSetter?: React.Dispatch<React.SetStateAction<string>>
}

export interface IFitsModalHandlerProps {
    handleClose: () => void;
    show: boolean;
    filename: string;
    headerInfo: any;
    // stateSetter?: React.Dispatch<React.SetStateAction<string>>
}

export interface IFileBrowserProps {
    instanceId: string;
    selectedOpenDataSource?: string;
    getRootFileStructure: (bucket: string, prefix: string, clientType: string, source?: string) => Promise<FileArray>;
}

interface IError {
    code: number;
    message: string;
}

export interface IResponse {
    status_code: number;
    data: string;
    error?: IError;
}

export interface IDownloads {
    id: number;
    pid: number;
    name: string;
    status: string;
    message?: string;
}

export interface IDownloadsProps extends Array<IDownloads> { }

export interface IObjectToDownloadArgs {
    bucket: string;
    prefix: string;
    source: string;
    downloadPath: string;
}

export interface IDeleteDownloads {
    id?: number;
    pid?: number;
    deleteAll?: boolean;
}