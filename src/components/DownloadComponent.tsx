import React, { useContext } from 'react';
import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Stack from 'react-bootstrap/Stack';
import { DownloadContext } from './DownloadsContext';
import { DownloadContextType } from './downloads';
import { IDownloads } from './CustomProps';
import "../../node_modules/bootstrap/dist/css/bootstrap.min.css"

interface Props {
    download: IDownloads
}

export const DownloadComponent: React.FC<Props> = ({ download }): JSX.Element => {
    const { deleteDownloadFromList, getDownloadsList } = useContext(DownloadContext) as DownloadContextType;
    const handleDeleteClick = async (event: React.MouseEvent<HTMLElement>, id: number, pid: number) => {
        event.preventDefault();
        deleteDownloadFromList({ id, pid })
        getDownloadsList()
    }

    return (
        <div>
            <Card className='m-2'>
                <Card.Body>
                    <Stack gap={1} direction='horizontal'>
                        <Stack gap={1}>
                            <span>{download.name}</span>
                            <span>{download.status}</span>
                        </Stack>
                        <Button className="ms-auto" variant="link" size='sm' onClick={(e) => handleDeleteClick(e, download.id, download.pid)} disabled={!!(download.status === 'Downloading')}>
                            <span className="fa fa-solid fa-trash m-2" aria-hidden="true"></span>
                        </Button>
                    </Stack>
                </Card.Body>
            </Card>
        </div >
    );
}
