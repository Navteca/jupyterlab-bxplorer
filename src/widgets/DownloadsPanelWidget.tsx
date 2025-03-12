import React from "react";
import { ReactWidget } from "@jupyterlab/apputils";
import { DownloadsPanelComponent } from '../components/DownloadsPanelComponent';
import DownloadProvider from '../components/DownloadsContext';


export class DownloadsPanelWidget extends ReactWidget {

    constructor() {
        super()
    }

    render(): JSX.Element {
        return (
            <div style={{
                minWidth: "400px",
                display: 'flex',
                flexDirection: 'column',
                background: 'var(--jp-layout-color1)'
            }}>
                <DownloadProvider>
                    <DownloadsPanelComponent />
                </DownloadProvider>
            </div>
        )
    }

}