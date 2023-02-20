import React, { useEffect, useContext } from 'react';
import Stack from 'react-bootstrap/Stack';
import Button from 'react-bootstrap/Button';
import OverlayTrigger from 'react-bootstrap/OverlayTrigger'
import Tooltip from 'react-bootstrap/Tooltip'
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

    const clearListTooltip = (<Tooltip id="clear-list">Clear all</Tooltip>);
    const refreshTooltip = (<Tooltip id="refresh">Refresh</Tooltip>);

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            overflowY: 'auto'
        }}>
            <Stack gap={2} direction='horizontal'>
                <h4>Downloads history</h4>
                <span style={{ flex: "1 1 auto" }}></span>
                <ButtonGroup className="p-2" aria-label="Downloads Utilities">
                    <OverlayTrigger placement="bottom" overlay={clearListTooltip}>
                        <Button
                            variant="link"
                            size='sm'
                            onClick={(e) => handleDelete(e)}
                            disabled={!!(downloads.length === 0)}
                        >
                            <i className="fa-solid fa-trash-list m-2 fa-lg" aria-hidden="true"></i>
                        </Button>
                    </OverlayTrigger>
                    <OverlayTrigger placement="bottom" overlay={refreshTooltip}>
                        <Button variant="link" size='sm' onClick={getDownloadsList}>
                            <i className="fa fa-solid fa-arrows-rotate m-2 fa-lg" aria-hidden="true"></i>
                        </Button>
                    </OverlayTrigger>

                </ButtonGroup>
            </Stack>
            <div>
                {downloads.map((download) => {
                    return (
                        <DownloadComponent download={download} />
                    )
                })}
            </div>
        </div>
    );
}