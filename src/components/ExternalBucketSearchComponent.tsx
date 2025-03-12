import React from 'react';
import Button from 'react-bootstrap/Button';
import Form from 'react-bootstrap/Form';
import Modal from 'react-bootstrap/Modal';
import Stack from 'react-bootstrap/Stack';
import { FavoriteContext } from './FavoriteContext'
import { FavoriteContextType, IFavorite } from './favorites'
import { IModalHandlerProps } from './CustomProps'
import { INotification } from 'jupyterlab_toastify';
import * as Yup from 'yup'
import { useFormik } from 'formik'

interface IValues {
    bucketname: string
}

export const ExternalBucketSearchComponent: React.FC<IModalHandlerProps> = ({ show, handleClose }) => {
    const { addFavorite } = React.useContext(FavoriteContext) as FavoriteContextType;
    const formSchema = Yup.object().shape({
        bucketname: Yup.string()
            .trim()
            .required('A bucket name must be provided')
            .min(3, 'Bucket name should at least be 3 characters longs.')
            .max(63, 'Bucket name should not be more than 63 characters long.')
            .matches(/^[a-zA-Z0-9.\_\-]{1,255}$/, 'Bucket name should not include special characters.')
    })

    const onSubmit = async (values: IValues) => {
        let bucketName = values.bucketname
        let newFavorite: IFavorite = {
            path: bucketName,
            bucket_source: 'AWS',
            bucket_source_type: 'External',
            chonky_object: {
                id: bucketName,
                name: bucketName,
                isDir: true,
                additionalInfo: [{ type: "public", isCrossAccount: true }],
            }
        }
        const response = await addFavorite(newFavorite)
        if (response.status_code === 200) {
            INotification.success(response.data, { autoClose: 5000 })
            handleClose()
        } else {
            INotification.error(response.error?.message, { autoClose: 5000 })
            handleClose()
        }
    }

    const { values, handleBlur, handleChange, handleSubmit, errors, touched } = useFormik({
        initialValues: {
            bucketname: ''
        },
        onSubmit,
        validationSchema: formSchema
    });

    return (
        <Modal show={show} onHide={handleClose}>
            <Modal.Header closeButton>
                <Modal.Title>External Bucket Search</Modal.Title>
            </Modal.Header>
            <Modal.Body>
                <Form noValidate onSubmit={handleSubmit} autoComplete="off">
                    <Form.Group className="mb-3">
                        <Form.Label>Bucket Name</Form.Label>
                        <Form.Control
                            id="bucketname"
                            type="text"
                            value={values.bucketname}
                            placeholder="Bucket name"
                            onChange={handleChange}
                            onBlur={handleBlur}
                            className={errors.bucketname && touched.bucketname ? 'text-danger' : ''}
                            autoFocus
                        />
                        {errors.bucketname
                            ? (<p className="text-danger" aria-live="polite">{errors.bucketname}</p>)
                            : null
                        }
                    </Form.Group>
                    <Form.Group>
                        <Stack gap={2} direction="horizontal" className="d-flex justify-content-end">
                            <Button type="submit" disabled={!!errors.bucketname}>Add</Button>
                            <Button variant="secondary" onClick={handleClose}>Close</Button>
                        </Stack>
                    </Form.Group>
                </Form>
            </Modal.Body>
        </Modal>
    );
}

export default ExternalBucketSearchComponent;