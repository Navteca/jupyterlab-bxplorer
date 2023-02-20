import React from "react";
import { ReactWidget } from "@jupyterlab/apputils";
import { PanelComponent } from "../components/PanelComponent";

export class BXplorerPanelWidget extends ReactWidget {
    constructor() {
        super()
    }

    render(): JSX.Element {
        return (
            <div style={{ width: "100%" }}>
                <PanelComponent />
            </div>
        )
    }

}