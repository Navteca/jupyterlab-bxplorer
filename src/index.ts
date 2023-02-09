import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import { requestAPI } from './handler';

/**
 * Initialization data for the jupyterlab-bxplorer extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'jupyterlab-bxplorer:plugin',
  autoStart: true,
  activate: (app: JupyterFrontEnd) => {
    console.log('JupyterLab extension jupyterlab-bxplorer is activated!');

    requestAPI<any>('get_example')
      .then(data => {
        console.log(data);
      })
      .catch(reason => {
        console.error(
          `The jupyterlab_bxplorer server extension appears to be missing.\n${reason}`
        );
      });
  }
};

export default plugin;
