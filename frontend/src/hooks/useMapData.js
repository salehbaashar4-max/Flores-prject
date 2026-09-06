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

/* Genuine no-drill areas: military land, cemeteries, airport airside (OSM). */
export const useRestrictedZones = () => {
  return useQuery({
    queryKey: ['restrictedZones'],
    queryFn: () => fetcher('/api/osm/restricted-zones'),
    ...queryOptions,
  });
};

/* National parks and nature reserves — permit zones, not drilling bans.
   Fetched only once the user switches the layer on: the park relations are
   large and most sessions never need them. */
export const useProtectedAreas = (enabled = false) => {
  return useQuery({
    queryKey: ['protectedAreas'],
    queryFn: () => fetcher('/api/osm/protected-areas'),
    enabled,
    ...queryOptions,
  });
};

/* Rivers and streams (OSM). Also lazy — it is the heaviest Overpass query. */
export const useRivers = (enabled = false) => {
  return useQuery({
    queryKey: ['rivers'],
    queryFn: () => fetcher('/api/geodata/rivers'),
    enabled,
    ...queryOptions,
  });
};

/* Live discovery of official WMS layers (USGS / BGR / ESDM / BIG / OneGeology).
   Returns per-source reachability + resolved geology/groundwater layer names.
   Never blocks the app: unreachable servers simply produce no toggle. */
export const useWMSConfig = () => {
  return useQuery({
    queryKey: ['wmsConfig'],
    queryFn: () => fetcher('/api/wms/config'),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });
};
