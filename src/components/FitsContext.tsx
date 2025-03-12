import React from 'react';
import { FitsContextType } from './fits';
import { requestAPI } from '../handler';

type FitsProviderProps = {
  children: React.ReactNode;
};

export const FitsContext = React.createContext<FitsContextType | null>(null);

const FitsProvider: React.FC<FitsProviderProps> = ({ children }) => {
  const getFitsHeader = async (file: string, bucket: string, anon: boolean) => {
    const response = await requestAPI<string>(
      'fits?file=' + file + '&bucket=' + bucket + '&anon=' + anon
    );
    return response;
  };

  return (
    <FitsContext.Provider value={{ getFitsHeader }}>
      {children}
    </FitsContext.Provider>
  );
};

export default FitsProvider;
