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

import React, { useRef } from 'react';
import {
  FileManagerComponent,
  Inject,
  DetailsView,
  Toolbar,
} from '@syncfusion/ej2-react-filemanager';
import { requestAPI } from '../handler';
import { showDialog, Dialog, showErrorMessage } from '@jupyterlab/apputils';

interface FMViewComponentProps {
  downloadsFolder: string;
  clientType: string;
}

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
const FMViewComponent: React.FC<FMViewComponentProps> = (props): JSX.Element => {
  const downloadsFolder = props.downloadsFolder || "downloads";
  const clientType = props.clientType || "private";
  const fileManagerRef = useRef<FileManagerComponent>(null);

  /**
   * Computes the base URL for backend API requests.
   *
   * If the URL contains a "/user/" segment, it constructs the URL using the user path.
   * Otherwise, it returns the window's origin.
   *
   * @returns {string} The base URL.
   */
  const getBaseUrl = () => {
    const pathParts = window.location.pathname.split("/");
    const userIndex = pathParts.indexOf("user");

    if (userIndex !== -1 && pathParts.length > userIndex + 1) {
      return `${window.location.origin}/user/${pathParts[userIndex + 1]}`;
    }

    return window.location.origin;
  };

  const backendUrl = getBaseUrl();

  console.log(backendUrl);

  const ajaxSettings: object = {
    url: backendUrl + "/jupyterlab-bxplorer-v2/FileOperations",
  };

  /**
   * Retrieves a cookie value by its name.
   *
   * @param {any} name - The name of the cookie.
   * @returns {string | null} The cookie value if found, otherwise null.
   */
  function getCookie(name: any) {
    const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
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
        args.httpRequest.setRequestHeader("X-XSRFToken", xsrfToken);
      };
    }
    console.log("ajaxBeforeSend action:", args.action);
    console.log("ajaxBeforeSend args:", args);
    let currentData = args.ajaxSettings.data;
    if (typeof currentData === "string") {
      try {
        currentData = JSON.parse(currentData);
      } catch (e) {
        console.error("Error parsing ajaxSettings.data:", e);
        currentData = {};
      }
    }
    const modifiedData = { ...currentData, client_type: clientType };
    args.ajaxSettings.data = JSON.stringify(modifiedData);
    console.log("ajaxBeforeSend modified args:", args);
  };

  /**
   * Handles context menu click events for the FileManager.
   *
   * If the "Download" option is selected, it initiates a download action by preparing
   * the payload and sending a request to the backend API. Displays dialogs for feedback.
   *
   * @param {any} args - The event arguments from the context menu click.
   */
  const contextMenuClickHandler = (args: any): void => {
    console.log("menuClick args:", args);
    if (args.item && args.item.text === "Download") {
      args.cancel = true;
      const currentPath = (fileManagerRef.current as any).path || "/";
      const selectedItems = args.data || (fileManagerRef.current && (fileManagerRef.current as any).selectedItems);
      if (!selectedItems || selectedItems.length === 0) {
        showDialog({
          title: 'Information',
          body: 'No file selected',
          buttons: [Dialog.okButton({ label: 'OK' })]
        });
        return;
      }

      const payloadObj = {
        action: "download",
        path: currentPath,
        downloadsFolder: downloadsFolder,
        client_type: clientType,
        names: selectedItems.map((item: any) => item.name || item),
        data: selectedItems.map((item: any) => {
          if (typeof item === "string") {
            return {
              name: item,
              isFile: true,
              path: currentPath.endsWith("/")
                ? currentPath + item
                : currentPath + "/" + item,
            };
          } else {
            return item;
          }
        }),
      };

      const payload = JSON.stringify(payloadObj);
      const formData = new URLSearchParams();
      formData.append("downloadInput", payload);

      requestAPI('FileOperations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData.toString(),
      })
        .then((data: any) => {
          showDialog({
            title: 'Successful Operation',
            body: `File saved in: ${data.file_saved}`,
            buttons: [Dialog.okButton({ label: 'OK' })]
          });
        })
        .catch((error: any) => {
          console.error("Download error:", error);
          showErrorMessage('Download Error', 'An error occurred while downloading the file.');
        });
    }
  };

  return (
    <div className="control-section" style={{ height: "100%" }}>
      <FileManagerComponent
        ref={fileManagerRef}
        id="file"
        ajaxSettings={ajaxSettings}
        beforeSend={onBeforeSend.bind(this)}
        toolbarSettings={{
          items: ['SortBy', 'Refresh'],
          visible: true,
        }}
        contextMenuSettings={{
          file: ['Download', '|', 'Details'],
          folder: ['Open', '|', 'Details'],
          layout: [],
          visible: true,
        }}
        detailsViewSettings={{
          columns: [
            { field: "name", headerText: "Name", minWidth: 120, width: "auto" },
            { field: "region", headerText: "Region", minWidth: 100, width: "120px" },
            { field: "dateModified", headerText: "Modified", minWidth: 120, width: "150px" },
            { field: "size", headerText: "Size", minWidth: 80, width: "100px" },
          ],
        }}
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
