import React, { useEffect, useContext } from 'react';
import Stack from 'react-bootstrap/Stack';
import Button from 'react-bootstrap/Button';
import ButtonGroup from 'react-bootstrap/ButtonGroup';
import { DownloadComponent } from './DownloadComponent';
import { DownloadContext } from './DownloadsContext';
import { DownloadContextType } from './downloads';

export const DownloadsPanelComponent: React.FC = (): JSX.Element => {
    const { getDownloadsList, deleteDownloadFromList, downloads } = useContext(DownloadContext) as DownloadContextType;

    useEffect(() => {
        getDownloadsList()
    }, [])

    const handleDelete = (event: React.MouseEvent<HTMLElement>) => {
        event.preventDefault();
        deleteDownloadFromList({ deleteAll: true })
        getDownloadsList()
    }

    return (
        <div className='scroll'>
            <div>
                <Stack gap={2} className='d-flex justify-content-end'>
                    <ButtonGroup className="p-2" aria-label="Downloads Utilities">
                        <Button variant="link" size='sm' onClick={(e) => handleDelete(e)}>
                            <i className="fa-solid fa-trash-list m-2 fa-lg" aria-hidden="true"></i>
                        </Button>
                        <Button variant="link" size='sm' onClick={getDownloadsList}>
                            <i className="fa fa-solid fa-arrows-rotate m-2 fa-lg" aria-hidden="true"></i>
                        </Button>
                    </ButtonGroup>
                </Stack>
            </div>
            <div className='downloads-container'>
                {downloads.map((download) => {
                    return (
                        <DownloadComponent download={download} />
                    )
                })}
            </div>
        </div>
    );
}