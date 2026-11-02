export type NetworkNodeKind = 'hq' | 'branch' | 'partner'

export interface NetworkNode {
  id: string
  city: string
  country: string
  region: string
  lat: number
  lng: number
  kind: NetworkNodeKind
  focus: string
}

/**
 * Representative network nodes — replace with real office/partner locations before publishing.
 * Coordinates are city-centre approximations for the 3D globe visualisation.
 */
export const HQ: NetworkNode = {
  id: 'kathmandu',
  city: 'Bhaktapur',
  country: 'Nepal',
  region: 'South Asia',
  lat: 27.671,
  lng: 85.4298,
  kind: 'hq',
  focus: 'Headquarters · Web GIS & engineering',
}

export const NETWORK_NODES: NetworkNode[] = [
  HQ,
  {
    id: 'pokhara',
    city: 'Pokhara',
    country: 'Nepal',
    region: 'South Asia',
    lat: 28.2096,
    lng: 83.9856,
    kind: 'branch',
    focus: 'Field survey base · drone mapping & ground truth',
  },
  {
    id: 'dubai',
    city: 'Dubai',
    country: 'United Arab Emirates',
    region: 'Middle East',
    lat: 25.2048,
    lng: 55.2708,
    kind: 'branch',
    focus: 'Gulf delivery hub · enterprise GIS & smart city',
  },
  {
    id: 'london',
    city: 'London',
    country: 'United Kingdom',
    region: 'Europe',
    lat: 51.5074,
    lng: -0.1278,
    kind: 'partner',
    focus: 'UK partnerships · geospatial strategy & ESG',
  },
  {
    id: 'singapore',
    city: 'Singapore',
    country: 'Singapore',
    region: 'APAC',
    lat: 1.3521,
    lng: 103.8198,
    kind: 'branch',
    focus: 'APAC delivery · SaaS & location intelligence',
  },
  {
    id: 'sydney',
    city: 'Sydney',
    country: 'Australia',
    region: 'APAC',
    lat: -33.8688,
    lng: 151.2093,
    kind: 'partner',
    focus: 'Oceania partnerships · climate & land analytics',
  },
  {
    id: 'toronto',
    city: 'Toronto',
    country: 'Canada',
    region: 'North America',
    lat: 43.6532,
    lng: -79.3832,
    kind: 'branch',
    focus: 'North America studio · product engineering',
  },
  {
    id: 'new-york',
    city: 'New York',
    country: 'United States',
    region: 'North America',
    lat: 40.7128,
    lng: -74.006,
    kind: 'partner',
    focus: 'Client partnerships · fintech & urban systems',
  },
]

export const NETWORK_REGIONS: { name: string; count: number; focus: string }[] = [
  {
    name: 'South Asia',
    count: 2,
    focus: 'HQ, field survey and GIS engineering',
  },
  {
    name: 'Middle East',
    count: 1,
    focus: 'Smart city and enterprise delivery',
  },
  {
    name: 'Europe',
    count: 1,
    focus: 'Partnerships and geospatial strategy',
  },
  {
    name: 'APAC',
    count: 2,
    focus: 'SaaS delivery and climate analytics',
  },
  {
    name: 'North America',
    count: 2,
    focus: 'Product engineering and client partnerships',
  },
]

export const NETWORK_STATS: { label: string; value: string }[] = [
  { label: 'Global nodes', value: '08' },
  { label: 'Countries served', value: '07' },
  { label: 'Delivery coverage', value: '5 regions' },
  { label: 'HQ coordinates', value: '27.7172° N · 85.3240° E' },
]
