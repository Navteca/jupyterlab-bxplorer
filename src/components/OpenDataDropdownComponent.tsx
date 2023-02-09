import React, { useEffect } from 'react';
import Dropdown from 'react-bootstrap/Dropdown';
import { requestAPI } from '../handler'

interface Props {
    setODSource: React.Dispatch<React.SetStateAction<string>>;
}

const getOpenDataSourcesList = async (): Promise<string[]> => {
    const response = await requestAPI<any>('/open_data/get_sources_list')
    return response.sources
}

const OpenDataDropdownComponent: React.FC<Props> = ({ setODSource }) => {
    const [openDataSources, setOpenDataSourcesList] = React.useState<string[]>([])
    const [selectedSource, setSelectedSource] = React.useState<string>('AWS')

    useEffect(() => {
        getOpenDataSourcesList().then(setOpenDataSourcesList).catch((error) => console.log(error))
    }, []);

    return (
        <div className='dropdown'>
            <Dropdown>
                <Dropdown.Toggle id="open-data">
                    {selectedSource}
                </Dropdown.Toggle>
                <Dropdown.Menu>
                    {openDataSources.map((e, index) => {
                        return (<Dropdown.Item value={e + "-" + index} key={e + "-" + index} onClick={() => {
                            setODSource(e)
                            setSelectedSource(e)
                        }} disabled={e != 'AWS'}>{e}</Dropdown.Item>)
                    })}
                </Dropdown.Menu>
            </Dropdown>
        </div >
    )
}

export default OpenDataDropdownComponent;