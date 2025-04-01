import { ReactWidget } from "@jupyterlab/apputils";
import React from 'react';
import FileManagerPanelComponent from "../components/FileManagerPanelComponent";

export class FileManagerPanelWidget extends ReactWidget {
  downloadsFolder
  constructor(downloadsFolder: string) {
    super()
    this.downloadsFolder = downloadsFolder
  }

  render(): JSX.Element {
    return (
      <div
        style={{
          width: '100%',
        }}
      >
        <FileManagerPanelComponent downloadsFolder={this.downloadsFolder} />
      </div>
    )
  }
}