import React from 'react';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Modal from 'react-bootstrap/Modal';
import Stack from 'react-bootstrap/Stack';
import { IModalHandlerProps } from './CustomProps'
import * as Yup from 'yup'
import { useFormik } from 'formik'

interface IValues {
    downloadPath: string
}

export const DownloadPathSetterComponent: React.FC<IModalHandlerProps> = ({ show, handleClose, setDownloadPath }) => {
    const formSchema = Yup.object().shape({
        downloadPath: Yup.string()
            .trim()
            .required('A path must be provided')
            .matches(/^(?![\/])[a-zA-Z0-9.\-\_\/]+$/, "Only local paths in the current directory without special characters are allowed.")
    })

    const onSubmit = (values: IValues) => {
        let downloadPath = values.downloadPath
        setDownloadPath!(downloadPath)
        handleClose()
    }

    const { values, handleBlur, handleChange, handleSubmit, errors, touched } = useFormik({
        initialValues: {
            downloadPath: ''
        },
        onSubmit,
        validationSchema: formSchema
    });

    return (
        <Modal show={show} onHide={handleClose}>
            <Modal.Header closeButton>
                <Modal.Title>Download Path</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Form noValidate onSubmit={handleSubmit} autoComplete="off">
                    <Form.Group className="mb-3">
                        <Form.Label>Download Path</Form.Label>
                        <Form.Control
                            id="downloadPath"
                            type="text"
                            value={values.downloadPath}
                            placeholder="Downloads"
                            onChange={handleChange}
                            onBlur={handleBlur}
                            className={errors.downloadPath && touched.downloadPath ? 'text-danger' : ''}
                            autoFocus
                        />
                        {errors.downloadPath
                            ? (<p className="text-danger" aria-live="polite">{errors.downloadPath}</p>)
                            : null
                        }
                    </Form.Group>
                    <Form.Group>
                        <Stack gap={2} direction="horizontal" className="d-flex justify-content-end">
                            <Button type="submit" disabled={!!errors.downloadPath}>Ok</Button>
                            <Button variant="secondary" onClick={handleClose}>Close</Button>
                        </Stack>
                    </Form.Group>
                </Form>
            </Modal.Body>
        </Modal>
    );
}

export default DownloadPathSetterComponent;