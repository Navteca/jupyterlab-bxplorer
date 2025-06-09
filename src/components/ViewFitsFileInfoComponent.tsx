import React from 'react';
import Modal from 'react-bootstrap/Modal';
import Table from 'react-bootstrap/Table';
import { IFitsModalHandlerProps } from './CustomProps';

export const ViewFitsFileInfoComponent: React.FC<IFitsModalHandlerProps> = ({
  show,
  handleClose,
  filename,
  headerInfo
}) => {
  return (
    <Modal size="lg" show={show} onHide={handleClose} scrollable>
      <Modal.Header closeButton>
        <Modal.Title>{filename} header</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Table striped bordered hover>
          <tbody>
            {Object.entries(headerInfo).map(item => {
              const str: any = item[1];
              const [first, ...rest] = str.split('=');
              const remainder = rest.join('=').trim().slice(0, -4);

              return (
                <tr>
                  <td>{first}</td>
                  <td>{remainder}</td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </Modal.Body>
    </Modal>
  );
};

export default ViewFitsFileInfoComponent;
