import {
  ILayoutRestorer,
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { ISettingRegistry } from '@jupyterlab/settingregistry';
import { MainAreaWidget } from '@jupyterlab/apputils';
import { telescopeIcon, telescopeDownloadsIcon } from './style/IconsStyle';
import { BXplorerPanelWidget } from './widgets/BXplorerPanelWidget';
import { DownloadsPanelWidget } from './widgets/DownloadsPanelWidget'

const PLUGIN_ID = 'jupyterlab_bxplorer:plugin';

const plugin: JupyterFrontEndPlugin<void> = {
  id: PLUGIN_ID,
  autoStart: true,
  optional: [ILayoutRestorer, ISettingRegistry],
  activate: activate
};

async function activate(app: JupyterFrontEnd, restorer: ILayoutRestorer): Promise<void> {

  const content = new BXplorerPanelWidget()
  const widget = new MainAreaWidget<BXplorerPanelWidget>({ content })
  widget.toolbar.hide()
  widget.title.icon = telescopeIcon;
  widget.title.caption = 'BXplorer';
  app.shell.add(widget, 'left', { rank: 501 });

  setTimeout(() => {
      console.log('Updating widget...')
      widget.update()
      widget.content.update()
  }, 15000);

  const downloadsContent = new DownloadsPanelWidget()
  downloadsContent.addClass('jp-PropertyInspector-placeholderContent');
  const downloadsWidget = new MainAreaWidget<DownloadsPanelWidget>({ content: downloadsContent })
  downloadsWidget.toolbar.hide()
  downloadsWidget.title.icon = telescopeDownloadsIcon;
  downloadsWidget.title.caption = 'BXplorer Downloads';
  app.shell.add(downloadsWidget, 'right', { rank: 501 });

  restorer.add(widget, 'bxplorerWidget');
}

export default plugin;
