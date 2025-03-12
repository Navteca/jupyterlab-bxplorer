export type FitsContextType = {
    getFitsHeader: (file: string, bucket: string, anon: boolean) => Promise<string>;
};