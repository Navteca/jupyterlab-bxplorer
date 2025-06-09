import { ReactWidget } from '@jupyterlab/apputils';
import { Message } from '@lumino/messaging';
import React from 'react';
import FileManagerPanelComponent from '../components/FileManagerPanelComponent';

export class FileManagerPanelWidget extends ReactWidget {
  downloadsFolder: string;
  atlasId: string;
  constructor(downloadsFolder: string, atlasId: string) {
    super();
    this.downloadsFolder = downloadsFolder;
    this.atlasId = atlasId;
    this.node.style.minWidth = '600px';
  }

  render(): JSX.Element {
    return (
      <div
        style={{
          width: '100%'
        }}
      >
        <FileManagerPanelComponent
          downloadsFolder={this.downloadsFolder}
          atlasId={this.atlasId}
        />
      </div>
    );
  }

  /**
   * It is triggered when the user activates this widget in the UI (click on the tab).
   */
  protected onAfterShow(msg: Message): void {
    super.onAfterShow(msg);
    window.dispatchEvent(new CustomEvent('filemanager-panel-open'));
  }
}
