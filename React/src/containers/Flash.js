import { useState } from "react";
import { FaTimes } from "react-icons/fa";
import FlashMessage from 'react-flash-message'

export default function Flash({type, message, duration, setType}) {

    return (
        <FlashMessage duration={duration} persistOnHover={true}>
        <div className="notificationContainer">
            <div className={`notification success`}><p>{message}</p><div className="icon"><FaTimes onClick={() => setType('none')}/></div></div>
        </div>
        </FlashMessage>
    );
    }
