import { useQuery } from '@tanstack/react-query';

const fetcher = async (url) => {
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
  const res = await fetch(`${baseUrl}${url}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${url}`);
  }
  return res.json();
};

const queryOptions = {
  staleTime: Infinity, // Cache in memory for instant toggling
  retry: 1,
};

export const useElevationLayer = () => {
  return useQuery({
    queryKey: ['elevation'],
    queryFn: () => fetcher('/api/gee/elevation'),
    ...queryOptions,
  });
};

export const useNDVILayer = () => {
  return useQuery({
    queryKey: ['ndvi'],
    queryFn: () => fetcher('/api/gee/ndvi'),
    ...queryOptions,
  });
};

export const useMoistureLayer = () => {
  return useQuery({
    queryKey: ['moisture'],
    queryFn: () => fetcher('/api/gee/moisture'),
    ...queryOptions,
  });
};

export const useGroundwaterPotential = () => {
  return useQuery({
    queryKey: ['groundwaterPotential'],
    queryFn: () => fetcher('/api/gee/potential'),
    ...queryOptions,
  });
};

export const useRestrictedZones = () => {
  return useQuery({
    queryKey: ['restrictedZones'],
    queryFn: () => fetcher('/api/osm/restricted-zones'),
    ...queryOptions,
  });
};

export const useCATBasins = () => {
  return useQuery({
    queryKey: ['catBasins'],
    queryFn: () => fetcher('/api/geodata/cat-basins'),
    ...queryOptions,
  });
};

export const useGeology = () => {
  return useQuery({
    queryKey: ['geology'],
    queryFn: () => fetcher('/api/geodata/geology'),
    ...queryOptions,
  });
};

export const useRivers = () => {
  return useQuery({
    queryKey: ['rivers'],
    queryFn: () => fetcher('/api/geodata/rivers'),
    ...queryOptions,
  });
};

/* Live discovery of official Indonesian WMS layers (ESDM / BIG / OneGeology).
   Returns per-source reachability + resolved geology/groundwater layer names.
   Retried a bit since government servers can be slow, but never blocks the app. */
export const useWMSConfig = () => {
  return useQuery({
    queryKey: ['wmsConfig'],
    queryFn: () => fetcher('/api/wms/config'),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
};
