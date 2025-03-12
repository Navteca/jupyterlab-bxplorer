import React, { useContext } from 'react';
import Button from 'react-bootstrap/Button';
import Card from 'react-bootstrap/Card';
import Stack from 'react-bootstrap/Stack';
import OverlayTrigger from 'react-bootstrap/OverlayTrigger'
import Tooltip from 'react-bootstrap/Tooltip'
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

    const removeFromListTooltip = (<Tooltip id="remove-from-list">Remove from list</Tooltip>);

    return (
        <div>
            <Card className='m-2'>
                <Card.Body>
                    <Stack gap={1} direction='horizontal'>
                        <Stack gap={1}>
                            <span>{download.name}</span>
                            <span>{download.status}</span>
                        </Stack>
                        <OverlayTrigger placement="bottom" overlay={removeFromListTooltip}>
                            <Button className="ms-auto" variant="link" size='sm' onClick={(e) => handleDeleteClick(e, download.id, download.pid)} disabled={!!(download.status === 'Downloading')} >
                                <span className="fa fa-solid fa-xmark m-2" aria-hidden="true"></span>
                            </Button>
                        </OverlayTrigger>
                    </Stack>
                </Card.Body>
            </Card>
        </div >
    );
}
