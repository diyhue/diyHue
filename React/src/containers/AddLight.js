import { useState } from 'react'
import axios from "axios";
import Dropdown from 'react-dropdown';
import 'react-dropdown/style.css';

const AddLight = () => {

    const [protocol, setProtocol] = useState('auto')

    const protocols = [
        { value: 'auto', label: 'Autodetect' },
        { value: 'domoticz', label: 'Domoticz' },
        { value: 'flex', label: 'Flex' },
        { value: 'jeedom', label: 'Jeedom' },
        { value: 'milight', label: 'MiLight' },
        { value: 'mibox', label: 'Mi Box' },
        { value: 'wiz', label: 'Wiz' }
    ]

    const milightGroups = [
        "1",
        "2",
        "3",
        "4"
    ]

    const milightModes = [
        { value: 'rgbw', label: 'RGBW' },
        { value: 'cct', label: 'CCT' },
        { value: 'rgb_cct', label: 'RGB-CCT' },
        { value: 'rgb', label: 'RGB' }
    ]

    const lightModelIds = [
        { value: 'LOM001', label: 'On/Off Plug' },
        { value: 'LWB010', label: 'Dimmable Light' },
        { value: 'LTW001', label: 'Color temperature Light' },
        { value: 'LCT015', label: 'Color Light' },
        { value: 'LST002', label: 'Color Strip' }
    ]

    return (

        <form className='add-form'>
            <Dropdown
                options={protocols}
                value={protocol}
                onChange={(e) => setProtocol(e.value)}
                placeholder="Choose light protocol"
            />
            <div className='form-control'>
                <label>Light Ip</label>
                <input
                    type='text'
                    placeholder='192.168.x.x'
                //value={deconzHost}
                //onChange={(e) => setDeconzHost(e.target.value)}
                />
            </div>
            {
                protocol !== 'auto' && 
                <>
                    <div className='form-control'>
                        <label>Name</label>
                        <input
                            type='text'
                            placeholder='Name used on diyhue'
                        />
                    </div>
                    <div className='form-control'>
                        <Dropdown
                            options={lightModelIds}
                            //value={protocol}
                            //onChange={(e) => setProtocol(e.value)} 
                            placeholder="Emulated light type"
                        /></div>
                </>
            }
            {
                (protocol === 'milight' || protocol === 'mibox') && <>
                    <div className='form-control'>
                        <label>Device ID</label>
                        <input
                            type='text'
                            placeholder='0x1234'
                        />
                    </div>
                    <Dropdown
                        options={milightModes}
                        //value={protocol}
                        //onChange={(e) => setProtocol(e.value)} 
                        placeholder="Choose light mode"
                    />
                    <Dropdown
                        options={milightGroups}
                        //value={protocol}
                        //onChange={(e) => setProtocol(e.value)} 
                        placeholder="Choose light group"
                    />
                </>
            }
            {
                protocol === 'mibox' &&
                <div className='form-control'>
                    <label>Port</label>
                    <input
                        type='number'
                        placeholder='Mi Box port'
                    />
                </div>
            }
            {
                protocol === 'domoticz' &&
                <div className='form-control'>
                    <label>Device ID</label>
                    <input
                        type='text'
                        placeholder=''
                    />
                </div>

            }
            {
                protocol === 'jeedom' && <>
                    <div className='form-control'>
                        <label>Light Api</label>
                        <input
                            type='text'
                            placeholder='Light Api'
                        />
                    </div>
                    <div className='form-control'>
                        <label>Light ID</label>
                        <input
                            type='text'
                            placeholder='Light ID'
                        />
                    </div>
                </>
            }
            <div className='form-control'>
                <input type='submit' value='Add Light' className='btn btn-block' />
            </div>
        </form>

    )
}

export default AddLight