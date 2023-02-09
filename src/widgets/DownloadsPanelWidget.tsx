import React from "react";
import { ReactWidget } from "@jupyterlab/apputils";
import { DownloadsPanelWrapperProviderComponent } from "../components/DownloadsPanelWrapperProviderComponent";


export class DownloadsPanelWidget extends ReactWidget {

    constructor() {
        super()
    }

    render(): JSX.Element {
        return (
            <div style={{ width: "100%", minWidth: "200px" }}>
                <DownloadsPanelWrapperProviderComponent />
            </div>
        )
    }

}