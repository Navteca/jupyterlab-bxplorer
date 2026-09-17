/**
 * FMViewComponent.tsx
 *
 * This component renders a file manager view using the Syncfusion FileManagerComponent.
 * It configures AJAX settings for communication with the JupyterLab Bxplorer API and handles
 * context menu actions such as file downloading.
 *
 * Props:
 *   - downloadsFolder: string representing the folder where downloads will be saved.
 *   - clientType: string representing the type of S3 client ('private' or 'public').
 */

import React, { useEffect, useImperativeHandle, useRef } from 'react';
import {
  FailureEventArgs,
  FileManagerComponent,
  Inject,
  DetailsView,
  Toolbar,
  BeforePopupOpenCloseEventArgs
} from '@syncfusion/ej2-react-filemanager';
import { requestAPI } from '../handler';
import { showDialog, Dialog, showErrorMessage } from '@jupyterlab/apputils';
interface FMViewComponentProps {
  downloadsFolder: string;
  clientType: string;
  folderOptions: string[];
}
import { useDownloadHistory } from '../contexts/DownloadHistoryContext';

/**
 * FMViewComponent React Functional Component.
 *
 * Renders a file manager interface with customized AJAX settings, context menu handlers,
 * and toolbar and details view configurations. It also modifies request data to include
 * the client type.
 *
 * @param {FMViewComponentProps} props - The component properties.
 * @returns {JSX.Element} The rendered component.
 */
const FMViewComponent: React.FC<FMViewComponentProps> = (
  props,
  ref
): JSX.Element => {
  const { fetchHistory, startPolling } = useDownloadHistory();
  const downloadsFolder = props.downloadsFolder || 'downloads';
  const clientType = props.clientType || 'private';
  const fileManagerRef = useRef<FileManagerComponent>(null);

  // Allow parent to call refresh (if desired)
  useImperativeHandle(ref, () => ({
    refresh: () => fileManagerRef.current?.refresh()
  }));

  // Listens for the panel opening event and refreshes the FileManager
  useEffect(() => {
    const handlePanelOpen = () => {
      // Forcing recalculation and rendering of FileManager
      fileManagerRef.current?.refresh();
    };
    window.addEventListener('filemanager-panel-open', handlePanelOpen);
    return () => {
      window.removeEventListener('filemanager-panel-open', handlePanelOpen);
    };
  }, []);

  /**
   * Computes the base URL for backend API requests.
   *
   * If the URL contains a "/user/" segment, it constructs the URL using the user path.
   * Otherwise, it returns the window's origin.
   *
   * @returns {string} The base URL.
   */
  const getBaseUrl = () => {
    const pathParts = window.location.pathname.split('/');
    const userIndex = pathParts.indexOf('user');

    if (userIndex !== -1 && pathParts.length > userIndex + 1) {
      return `${window.location.origin}/user/${pathParts[userIndex + 1]}`;
    }

    return window.location.origin;
  };

  const backendUrl = getBaseUrl();

  const ajaxSettings: object = {
    url: backendUrl + '/jupyterlab-bxplorer/FileOperations'
  };

  /**
   * Retrieves a cookie value by its name.
   *
   * @param {any} name - The name of the cookie.
   * @returns {string | null} The cookie value if found, otherwise null.
   */
  function getCookie(name: any) {
    const match = document.cookie.match(
      new RegExp('(^| )' + name + '=([^;]+)')
    );
    return match ? match[2] : null;
  }

  /**
   * Modifies AJAX request settings before sending the request.
   *
   * Sets the X-XSRFToken header and adds the client type to the request data.
   *
   * @param {any} args - The AJAX request arguments.
   */
  const onBeforeSend = (args: any): void => {
    if (args.ajaxSettings) {
      const xsrfToken = getCookie('_xsrf');
      args.ajaxSettings.beforeSend = function (args: any) {
        args.httpRequest.setRequestHeader('X-XSRFToken', xsrfToken);
      };
    }

    let currentData = args.ajaxSettings.data;
    if (typeof currentData === 'string') {
      try {
        currentData = JSON.parse(currentData);
      } catch (e) {
        console.error('Error parsing ajaxSettings.data:', e);
        currentData = {};
      }
    }
    const modifiedData = { ...currentData, client_type: clientType };
    args.ajaxSettings.data = JSON.stringify(modifiedData);
  };

  /**
   * Handles context menu click events for the FileManager.
   *
   * If the "Download" option is selected, it initiates a download action by preparing
   * the payload and sending a request to the backend API. Displays dialogs for feedback.
   *
   * @param {any} args - The event arguments from the context menu click.
   */
  const contextMenuClickHandler = async (args: any): Promise<void> => {
    if (args.item && args.item.text === 'Add to favorites') {
      args.cancel = true;

      const currentPath = (fileManagerRef.current as any).path || '/';
      const selectedItems =
        args.data ||
        (fileManagerRef.current &&
          (fileManagerRef.current as any).selectedItems);

      const depth = currentPath.split('/').filter((seg: any) => seg).length;
      if (
        (clientType === 'private' && depth !== 0) ||
        (clientType === 'public' && depth !== 1)
      ) {
        showDialog({
          title: 'Not Allowed',
          body: 'You can only add buckets to favorites.',
          buttons: [Dialog.okButton({ label: 'OK' })]
        });
        return;
      }

      const selectedBucket = selectedItems?.[0];
      if (!selectedBucket) {
        showDialog({
          title: 'No Selection',
          body: 'No bucket selected to add to favorites.',
          buttons: [Dialog.okButton({ label: 'OK' })]
        });
        return;
      }

      try {
        await requestAPI('favorites', {
          method: 'POST',
          body: JSON.stringify({
            bucket: selectedBucket,
            client_type: clientType
          }),
          headers: { 'Content-Type': 'application/json' }
        });

        showDialog({
          title: 'Success',
          body: `"${selectedBucket}" added to favorites.`,
          buttons: [Dialog.okButton({ label: 'OK' })]
        });
      } catch (error) {
        console.error('Add to favorites error:', error);
        showErrorMessage('Error', 'Failed to add bucket to favorites.');
      }

      return;
    }

    if (args.item && args.item.text === 'Remove from favorites') {
      args.cancel = true;

      const currentPath = (fileManagerRef.current as any).path || '/';
      const selectedItems =
        args.data ||
        (fileManagerRef.current &&
          (fileManagerRef.current as any).selectedItems);

      if (currentPath !== '/') {
        showDialog({
          title: 'Not Allowed',
          body: 'You can only remove buckets from favorites from the root.',
          buttons: [Dialog.okButton({ label: 'OK' })]
        });
        return;
      }

      const selectedBucket = selectedItems?.[0];
      if (!selectedBucket) {
        showDialog({
          title: 'No Selection',
          body: 'No bucket selected to remove from favorites.',
          buttons: [Dialog.okButton({ label: 'OK' })]
        });
        return;
      }

      try {
        await requestAPI('favorites', {
          method: 'DELETE',
          body: JSON.stringify({ bucket: selectedBucket }),
          headers: { 'Content-Type': 'application/json' }
        });

        showDialog({
          title: 'Success',
          body: `"${selectedBucket}" removed from favorites.`,
          buttons: [Dialog.okButton({ label: 'OK' })]
        });
        const fm = fileManagerRef.current as any;
        if (fm) {
          const currentPath = fm.path;
          fm.path = '/temp-refresh';
          fm.path = currentPath;
        }
      } catch (error) {
        console.error('Remove from favorites error:', error);
        showErrorMessage('Error', 'Failed to remove bucket from favorites.');
      }

      return;
    }

    if (args.item && args.item.text === 'Download') {
      args.cancel = true;
      const currentPath = (fileManagerRef.current as any).path || '/';
      const selectedItems =
        args.data ||
        (fileManagerRef.current &&
          (fileManagerRef.current as any).selectedItems);
      if (!selectedItems || selectedItems.length === 0) {
        showDialog({
          title: 'Information',
          body: 'No file selected',
          buttons: [Dialog.okButton({ label: 'OK' })]
        });
        return;
      }

      const payloadObj = {
        action: 'download',
        path: currentPath,
        downloadsFolder: downloadsFolder,
        client_type: clientType,
        names: selectedItems.map((item: any) => item.name || item),
        data: selectedItems.map((item: any) => {
          if (typeof item === 'string') {
            return {
              name: item,
              isFile: true,
              path: currentPath.endsWith('/')
                ? currentPath + item
                : currentPath + '/' + item
            };
          } else {
            return item;
          }
        })
      };

      const payload = JSON.stringify(payloadObj);
      const formData = new URLSearchParams();
      formData.append('downloadInput', payload);

      await requestAPI('FileOperations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString()
      })
        .then(async (data: any) => {
          await fetchHistory();
          startPolling();

          let savedPath: string;
          if (typeof data === 'string') {
            savedPath = data;
          } else if (data.file_saved) {
            savedPath = data.file_saved;
          } else {
            savedPath = downloadsFolder;
          }

          showDialog({
            title: 'Successful Operation',
            body: `File saved in: ${savedPath}`,
            buttons: [Dialog.okButton({ label: 'OK' })]
          });
        })
        .catch((error: any) => {
          console.error('Download error:', error);
          showErrorMessage(
            'Download Error',
            'An error occurred while downloading the file.'
          );
        });
    }
  };

  const onFileLoad = (args: any) => {
    const currentPath = fileManagerRef.current?.path || '/';
    const depth = currentPath.split('/').filter(seg => seg).length;

    const icons = args.element.querySelectorAll('.e-fe-icon.e-fe-folder');
    icons.forEach((icon: any) => {
      if (clientType === 'public' && depth === 0) {
        icon.className = 'e-icons dataset-icon';
      } else if (
        (clientType === 'private' && depth === 0) ||
        (clientType === 'favorites' && depth === 0) ||
        (clientType === 'public' && depth === 1)
      ) {
        icon.className = 'e-icons bucket-icon';
      } else {
        icon.className = 'e-fe-icon e-fe-folder';
      }
    });
  };

  const onFailure = (args: FailureEventArgs) => {
    if (args.action === 'read') {
      showDialog({
        title: 'Access Error',
        body: (
          <div>
            <p>
              An error occurred while trying to access the dataset or bucket.
            </p>
            <p>
              Please open an issue at{' '}
              <a
                href="https://github.com/Navteca/jupyterlab-bxplorer/issues"
                target="_blank"
                rel="noopener"
              >
                https://github.com/Navteca/jupyterlab-bxplorer/issues
              </a>{' '}
              so we can investigate and resolve it.
            </p>
          </div>
        ),
        buttons: [Dialog.okButton({ label: 'OK' })]
      });
    }
  };

  const onBeforePopupOpen = (args: BeforePopupOpenCloseEventArgs) => {
    // suppress Syncfusion's default error dialog
    if (args.popupName === 'Error') {
      args.cancel = true;
    }
  };

  return (
    <div className="control-section" style={{ height: '100%', width: '100%' }}>
      <FileManagerComponent
        ref={fileManagerRef}
        id="file"
        ajaxSettings={ajaxSettings}
        beforeSend={onBeforeSend.bind(this)}
        toolbarSettings={{
          items: ['SortBy', 'Refresh'],
          visible: true
        }}
        contextMenuSettings={{
          file: ['Download', '|', 'Details'],
          folder: props.folderOptions,
          layout: [],
          visible: true
        }}
        detailsViewSettings={{
          columns: [
            {
              field: 'name',
              headerText: 'Name',
              minWidth: 200,
              width: 'auto'
            },
            {
              field: 'region',
              headerText: 'Region',
              minWidth: 10,
              width: 'auto'
            },
            {
              field: 'dateModified',
              headerText: 'Modified',
              minWidth: 10,
              width: 'auto'
            },
            { field: 'size', headerText: 'Size', minWidth: 10, width: 'auto' }
          ]
        }}
        fileLoad={onFileLoad}
        beforePopupOpen={onBeforePopupOpen}
        failure={onFailure}
        view="Details"
        allowMultiSelection={false}
        height="100%"
        {...({ menuClick: contextMenuClickHandler } as any)}
      >
        <Inject services={[DetailsView, Toolbar]} />
      </FileManagerComponent>
    </div>
  );
};

export default FMViewComponent;
