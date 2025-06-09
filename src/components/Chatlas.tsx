import React, { useEffect, useRef } from 'react';

interface ChatlasProps {
  atlasId: string;
  fullScreen?: boolean;
  voiceEnabled?: boolean;
}

const Chatlas: React.FC<ChatlasProps> = ({
  atlasId,
  fullScreen = true,
  voiceEnabled = false
}): JSX.Element => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const script = document.createElement('script');
    script.src = 'https://app.dev.thevoiceatlas.com/bot/chatlas.js';
    script.async = true;
    document.body.appendChild(script);

    const customEl = document.createElement('app-chatlas');
    customEl.setAttribute('collection-id', atlasId);
    customEl.setAttribute('full-screen', fullScreen.toString());
    customEl.setAttribute('voice-enabled', voiceEnabled.toString());
    // customEl.style.width = '70%'; // <- aquí se aplica el ancho
    // customEl.style.height = '100%'; // opcional, según tus necesidades

    containerRef.current?.appendChild(customEl);

    return () => {
      document.body.removeChild(script);
      containerRef.current?.removeChild(customEl);
    };
  }, [atlasId, fullScreen, voiceEnabled]);

  return (
    <div ref={containerRef} style={{ width: '100%', height: '97%' }}></div>
  );
};

export default Chatlas;
