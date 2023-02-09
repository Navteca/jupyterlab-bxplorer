import FileArray from 'chonky-navteca';
import { IResponse } from './CustomProps'

export interface IFavorite {
    path: string;
    chonky_object: FileArray;
    bucket_source: string;
    bucket_source_type: string;
}

export type FavoriteContextType = {
    favorite: IFavorite[];
    addFavorite: (favorite: IFavorite) => Promise<IResponse>;
    deleteFavorite: (favorite_bucket_name: string) => Promise<IResponse>;
};