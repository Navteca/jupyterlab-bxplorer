import React, { useEffect, useState } from 'react';
import { FavoriteContextType, IFavorite } from './favorites'
import { requestAPI } from '../handler'
import { IResponse } from './CustomProps'

type FavoriteProviderProps = {
    children: React.ReactNode
}

export const FavoriteContext = React.createContext<FavoriteContextType | null>(null);

const FavoriteProvider: React.FC<FavoriteProviderProps> = ({ children }) => {
    const [favorite, setFavorite] = useState<IFavorite[]>([])

    useEffect(() => {
        getFavoritesList()
    }, []);

    const addFavorite = async (favorite: IFavorite): Promise<IResponse> => {
        let response: IResponse = { status_code: 0, data: '' };
        try {
            response = await requestAPI<any>('favorites',
                {
                    method: "POST",
                    body: JSON.stringify(favorite)
                });
            getFavoritesList()
        } catch (e) {
            console.log(`There has been an error trying to add a new favorite => ${JSON.stringify(e, null, 2)}`)
            response = e as IResponse
        }
        return response;
    }

    const deleteFavorite = async (favorite_bucket_name: string): Promise<IResponse> => {
        let response: IResponse = { status_code: 0, data: '' };
        try {
            response = await requestAPI<any>('favorites',
                {
                    method: "DELETE",
                    body: JSON.stringify(favorite_bucket_name)
                });
            getFavoritesList()
        } catch (e) {
            console.log(`There has been an error trying to add a new favorite => ${e}`)
            response = e as IResponse
        }
        return response;
    }

    const getFavoritesList = async () => {
        const response = await requestAPI<any>('favorites');
        setFavorite(response)
    }

    return (
        <FavoriteContext.Provider value={{ favorite, addFavorite, deleteFavorite }}>
            {children}
        </FavoriteContext.Provider>
    );
}

export default FavoriteProvider;