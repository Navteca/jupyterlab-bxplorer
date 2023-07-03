/* eslint-disable prettier/prettier */
import {
    ChonkyActions,
    ChonkyFileActionData,
    ChonkyIconName,
    defineFileAction,
    FileArray,
    FileBrowser,
    FileContextMenu,
    FileData,
    FileList,
    FileNavbar,
    FileToolbar
} from 'chonky-navteca';
import { ChonkyIconFA } from 'chonky-navteca-icon-fontawesome';
import path from 'path';
import React, { useCallback, useEffect, useState, useContext, useMemo, useRef } from 'react';
import { FitsContext } from './FitsContext'
import { FitsContextType } from './fits'
import { FavoriteContext } from './FavoriteContext'
import { FavoriteContextType, IFavorite } from './favorites'
import { DownloadContext } from './DownloadsContext';
import { DownloadContextType } from './downloads';
import { ExternalBucketSearchComponent } from './ExternalBucketSearchComponent';
import { DownloadPathSetterComponent } from './DownloadPathSetterComponent'
import { ViewFitsFileInfoComponent } from './ViewFitsFileInfoComponent'
import { IFileBrowserProps } from './CustomProps'
import { INotification } from 'jupyterlab_toastify';
import isEmpty from 'lodash.isempty'

export const FileBrowserComponent: React.FC<IFileBrowserProps> = ({ getRootFileStructure, instanceId, selectedOpenDataSource }) => {
    const [folderPrefix, setKeyPrefix] = useState<string>('/');
    const [files, setFiles] = useState<FileArray>([]);
    const [isRoot, setIsRoot] = useState<boolean>(true);
    const [bucketName, setBucketName] = useState<string>('');
    const [selectedOption, setSelectedOption] = useState<string>('');
    const [showAddExternalBucketModal, setShowAddExternalBucketModal] = useState(false);
    const [showDownloadPathSetterModal, setShowDownloadPathSetterModal] = useState(false);
    const [showViewFitsFileInfoModal, setShowViewFitsFileInfoModal] = useState(false);
    const { favorite, addFavorite, deleteFavorite } = useContext(FavoriteContext) as FavoriteContextType;
    const { getFitsHeader } = useContext(FitsContext) as FitsContextType;
    const [downloadPath, setDownloadPath] = useState<string>('Downloads');
    const [fitsInfo, setFitsInfo] = useState<string>('');
    const { downloadObject } = useContext(DownloadContext) as DownloadContextType;
    let downloadPathValue = useRef('')

    useEffect(() => {
        if (isRoot) {
            if (instanceId === 'private') {
                getRootFileStructure('', '/', instanceId).then(setFiles).catch((error) => console.log(error))
            } else if ((selectedOpenDataSource) && (instanceId === 'public')) {
                getRootFileStructure('', '/', instanceId, selectedOpenDataSource).then((chonky_files) => {
                    setFiles(!isEmpty(chonky_files) ? chonky_files : [])
                }).catch((error) => console.log(error))
            } else { // favorites
                let chonky_obj: FileArray<FileData> = []
                if (favorite) {
                    favorite.forEach((value) => {
                        chonky_obj.push(JSON.parse(value.chonky_object))
                    })
                    setFiles(chonky_obj)
                }
            }
        }

    }, [isRoot, getRootFileStructure, selectedOpenDataSource, favorite, instanceId]);

    useEffect(() => {
        if (!isRoot) {
            const newPrefix = (bucketName === folderPrefix.split('/')[0]) ? folderPrefix.replace(bucketName, "") : folderPrefix
            if (instanceId === 'favorites') {
                if (favorite.filter(item => item.path === bucketName).length > 0) {
                    let clientType = JSON.parse(favorite.filter(item => item.path === bucketName)[0].chonky_object).additionalInfo[0].type
                    getRootFileStructure(bucketName, newPrefix.replace(/^\/+/, ''), clientType).then(setFiles).catch((error) => console.log(error))
                }
            } else {
                getRootFileStructure(bucketName, newPrefix.replace(/^\/+/, ''), instanceId).then(setFiles).catch((error) => console.log(error))
            }
        }
    }, [bucketName, folderPrefix, setFiles, isRoot, getRootFileStructure, instanceId, favorite]);

    useEffect(() => {
        downloadPathValue.current = downloadPath
    }, [downloadPath])

    const initiateDownload = async () => {
        if (instanceId === 'private') {
            await downloadObject({
                bucket: folderChain[1]!.name,
                prefix: selectedOption,
                source: '',
                downloadPath: downloadPathValue.current
            })
        } else if ((selectedOpenDataSource) && (instanceId === 'public')) {
            await downloadObject({
                bucket: folderChain[1]!.name,
                prefix: selectedOption,
                source: selectedOpenDataSource,
                downloadPath: downloadPathValue.current
            })
        }
    }

    const handCloseAddExternalBucketModal = () => setShowAddExternalBucketModal(false);
    const handCloseDownloadPathSetterModal = () => {
        setShowDownloadPathSetterModal(false);
        initiateDownload()
    }
    const handCloseViewFitsFileInfoModal = () => {
        setShowViewFitsFileInfoModal(false);
    }

    const folderChain = useMemo(() => {
        let folderChain: FileArray;
        switch (true) {
            case (folderPrefix === '/'): {
                setIsRoot(true)
                folderChain = [{
                    id: '/',
                    name: '/',
                    isDir: true,
                }];
                return folderChain
            }
            case ((folderPrefix.split('/').length === 2) && (folderPrefix.split('/')[0] === bucketName)): {
                setIsRoot(false)
                folderChain = [{
                    id: '/',
                    name: '/',
                    isDir: true,
                }, {
                    id: bucketName,
                    name: bucketName,
                    isDir: true,
                }];
                return folderChain;
            }
            case (folderPrefix.split('/')[0] !== bucketName): {
                setIsRoot(false)
                folderChain = [{
                    id: '/',
                    name: '/',
                    isDir: true,
                }, {
                    id: bucketName,
                    name: bucketName,
                    isDir: true,
                }];
                let currentPrefix = '';
                let folderChainAddition = folderPrefix
                    .replace(/\/*$/, '')
                    .split('/')
                    .map(
                        (prefixPart): FileData => {
                            currentPrefix = currentPrefix
                                ? path.join(currentPrefix, prefixPart)
                                : path.join(bucketName, prefixPart);
                            return {
                                id: currentPrefix,
                                name: prefixPart,
                                isDir: true,
                            };
                        }
                    );
                folderChain = [...folderChain, ...folderChainAddition];
                return folderChain
            }
            default: {
                setIsRoot(false)
                folderChain = [{
                    id: '/',
                    name: '/',
                    isDir: true,
                }];
                let currentPrefix = '';
                let folderChainAddition = folderPrefix
                    .replace(/\/*$/, '')
                    .split('/')
                    .map(
                        (prefixPart): FileData => {
                            currentPrefix = currentPrefix
                                ? path.join(currentPrefix, prefixPart)
                                : path.join(prefixPart);
                            return {
                                id: currentPrefix,
                                name: prefixPart,
                                isDir: true,
                            };
                        }
                    );
                folderChain = [...folderChain, ...folderChainAddition];
                return folderChain
            }

        }
    }, [bucketName, folderPrefix]);

    const customViewFitsFileInfo = defineFileAction({
        id: 'view_fits_info',
        requiresSelection: true,
        button: {
            name: 'View FITS file info',
            toolbar: true,
            contextMenu: true,
            group: 'Actions',
            icon: ChonkyIconName.info,
        },
    },
        async ({ state }) => {
            if (state.contextMenuTriggerFile) {
                const clientType = JSON.parse(favorite.filter(item => item.path === bucketName)[0].chonky_object).additionalInfo[0].type
                const file = state.contextMenuTriggerFile.id
                const response = await getFitsHeader(file, bucketName, clientType === 'public')
                setSelectedOption(file)
                setFitsInfo(response)
            }
        });

    const customDownloadFiles = defineFileAction({
        id: 'download_files',
        requiresSelection: true,
        button: {
            name: 'Download files',
            toolbar: true,
            contextMenu: true,
            group: 'Actions',
            icon: ChonkyIconName.download,
        },
    } as const,
        ({ state }) => {
            if (state.contextMenuTriggerFile) {
                setSelectedOption(state.contextMenuTriggerFile.id)
            }
        });

    const customAddToFavorites = defineFileAction({
        id: 'add_to_favorites',
        requiresSelection: true,
        button: {
            name: 'Add to Favorites',
            toolbar: true,
            contextMenu: true,
            group: 'Actions',
            icon: ChonkyIconName.folderCreate,
        },
    },
        async ({ state }) => {
            if (state.contextMenuTriggerFile) {
                if ((state.selectedFiles[0].hasOwnProperty('isDir')) && (folderPrefix === '/')) {
                    let newFavorite: IFavorite = {
                        path: folderChain.length === 1 ? state.contextMenuTriggerFile.id : `${folderChain[1]?.id}/${state.contextMenuTriggerFile.id}`,
                        bucket_source: selectedOpenDataSource ? selectedOpenDataSource : 'AWS',
                        bucket_source_type: instanceId,
                        chonky_object: state.selectedFiles[0]
                    }
                    const response = await addFavorite(newFavorite)
                    if (response.status_code === 200) {
                        INotification.success(response.data, { autoClose: 5000 })
                    } else {
                        INotification.error(response.error?.message, { autoClose: 5000 })
                    }
                } else {
                    console.log(`Only buckets can be added to favorites.`)
                }

            }
        });

    const customRemoveFromFavorite = defineFileAction({
        id: 'remove_from_favorite',
        requiresSelection: true,
        button: {
            name: 'Remove from Favorites',
            toolbar: true,
            contextMenu: true,
            group: 'Actions',
            icon: ChonkyIconName.clearSelection,
        },
    },
        async ({ state }) => {
            if (isRoot && state.contextMenuTriggerFile) {
                const response = await deleteFavorite(state.contextMenuTriggerFile.id)
                if (response.status_code === 200) {
                    INotification.success(response.data, { autoClose: 5000 })
                } else {
                    INotification.error(response.error?.message, { autoClose: 5000 })
                }
            }
        });

    const customAddBucket = defineFileAction({
        id: 'add_bucket',
        button: {
            name: 'Add bucket',
            toolbar: true,
            icon: ChonkyIconName.folderCreate,
        },
    });

    const handleFileAction = useCallback(
        async (data: ChonkyFileActionData) => {
            if (data.id === ChonkyActions.OpenFiles.id) {
                if (data.payload.files && data.payload.files.length !== 1) return;
                if (!data.payload.targetFile || !data.payload.targetFile.isDir) return;

                const newPrefix = `${data.payload.targetFile.id.replace(/\/*$/, '')}/`;
                setKeyPrefix(newPrefix);

                if (folderPrefix === '/') {
                    setBucketName(data.payload.targetFile.id.replace('/', ''))
                    setIsRoot(false)
                }
            }
            if (data.id === ChonkyActions.DownloadFiles.id) {
                if (isRoot) {
                    console.log('You are not allowed to download entire buckets')
                    INotification.info('It is not possible to download entire buckets.', { autoClose: 3000 })
                } else {
                    if (folderChain.length >= 2) {
                        setShowDownloadPathSetterModal(true)
                    } else {
                        INotification.info('It is not possible to download entire buckets.', { autoClose: 3000 })
                    }
                }
            }
            if (data.id === customViewFitsFileInfo.id) {
                if (isRoot) {
                    console.log('Not a FITS file.')
                    INotification.warning('Only FITS files are allowed.', { autoClose: 3000 })
                } else {
                    if (selectedOption.match(/^.*\.(fits|fit)$/)) {
                        setShowViewFitsFileInfoModal(true)
                    } else {
                        INotification.warning('Only FITS files are allowed.', { autoClose: 3000 })
                    }
                }
            }
            if (data.id === customAddToFavorites.id) {
                if (!isRoot) {
                    console.log('You are only allowed to add buckets to favorites.')
                    INotification.warning('You are only allowed to add buckets to favorites.', { autoClose: 3000 })
                }
            }
            if (data.id === customRemoveFromFavorite.id) {
                if (!isRoot) {
                    console.log('You are only allowed to remove buckets from favorites.')
                    INotification.warning('You are only allowed to remove buckets from favorites.', { autoClose: 3000 })
                }
            }
            if (data.id === customAddBucket.id) {
                setShowAddExternalBucketModal(true)
            }
        },
        [setKeyPrefix, folderPrefix, folderChain, isRoot, selectedOption, selectedOpenDataSource, instanceId, customAddBucket.id, customViewFitsFileInfo.id, customAddToFavorites.id, customRemoveFromFavorite.id]
    );

    let customFileActions: any[];
    if (instanceId === 'favorites') { customFileActions = [customAddBucket, customDownloadFiles, customRemoveFromFavorite, customViewFitsFileInfo]; }
    else if (instanceId === 'private') { customFileActions = [customDownloadFiles, customAddToFavorites, customViewFitsFileInfo]; }
    else { customFileActions = [customDownloadFiles, customAddToFavorites, customViewFitsFileInfo]; }

    const actionsToDisable: string[] = [
        ChonkyActions.EnableGridView.id,
        ChonkyActions.SelectAllFiles.id,
        ChonkyActions.ClearSelection.id,
        ChonkyActions.OpenSelection.id,
        ChonkyActions.SortFilesByDate.id,
        ChonkyActions.SortFilesByName.id,
        ChonkyActions.SortFilesBySize.id,
        ChonkyActions.ToggleHiddenFiles.id
    ];

    return (
        <div style={{ height: '87vh' }}>
            <FileBrowser
                instanceId={instanceId}
                files={files}
                folderChain={folderChain}
                onFileAction={handleFileAction}
                fileActions={customFileActions}
                disableDefaultFileActions={actionsToDisable}
                iconComponent={ChonkyIconFA}
                defaultSortActionId={ChonkyActions.SortFilesByName.id}
                defaultFileViewActionId={ChonkyActions.EnableListView.id}
            >
                <FileNavbar />
                <FileToolbar />
                <FileList />
                <FileContextMenu />
            </FileBrowser>
            {showAddExternalBucketModal &&
                <ExternalBucketSearchComponent
                    show={showAddExternalBucketModal}
                    handleClose={handCloseAddExternalBucketModal}
                />
            }
            {showDownloadPathSetterModal &&
                <DownloadPathSetterComponent
                    show={showDownloadPathSetterModal}
                    handleClose={handCloseDownloadPathSetterModal}
                    setDownloadPath={setDownloadPath}
                />
            }
            {showViewFitsFileInfoModal &&
                <ViewFitsFileInfoComponent
                    show={showViewFitsFileInfoModal}
                    handleClose={handCloseViewFitsFileInfoModal}
                    filename={selectedOption}
                    headerInfo={fitsInfo}
                />
            }
        </div>
    );
};

export default FileBrowserComponent;