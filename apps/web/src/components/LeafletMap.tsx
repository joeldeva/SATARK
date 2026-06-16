/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useRef } from 'react';
import L from 'leaflet';

export interface MapMarker {
  id: string;
  lat: number;
  lng: number;
  title: string;
  subtitle?: string;
  badge?: string;
  badgeColor?: string;
}

interface LeafletMapProps {
  center: [number, number];
  zoom: number;
  markers: MapMarker[];
  onMarkerClick?: (markerId: string) => void;
  height?: string;
  offlineTiles?: boolean;
}

export const LeafletMap: React.FC<LeafletMapProps> = ({
  center,
  zoom,
  markers,
  onMarkerClick,
  height = '320px',
  offlineTiles = false,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const baseLayerRef = useRef<L.LayerGroup | null>(null);
  const resizeObserverRef = useRef<ResizeObserver | null>(null);

  const buildBounds = (items: MapMarker[]) => {
    const points = items.length > 0
      ? items.map((marker) => [marker.lat, marker.lng] as [number, number])
      : [center];
    return L.latLngBounds(points).pad(items.length > 1 ? 0.55 : 0.08);
  };

  const extractPincode = (marker: MapMarker) => {
    const match = `${marker.subtitle || ''} ${marker.title}`.match(/\b\d{6}\b/);
    return match?.[0] || marker.badge || 'Field cell';
  };

  useEffect(() => {
    if (!containerRef.current) return;

    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }

    const map = L.map(containerRef.current, {
      center,
      zoom,
      zoomControl: true,
      fadeAnimation: true,
      preferCanvas: true,
      minZoom: 8,
      maxZoom: 15,
    });

    mapRef.current = map;

    if (!offlineTiles) {
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        minZoom: 1,
        crossOrigin: true,
        className: 'satark-osm-tiles',
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(map);
    }

    map.attributionControl.setPrefix(offlineTiles ? 'Offline pincode grid' : 'Leaflet map');

    const baseLayer = L.layerGroup().addTo(map);
    baseLayerRef.current = baseLayer;

    const markersLayer = L.layerGroup().addTo(map);
    markersLayerRef.current = markersLayer;

    const resizeTimeout = window.setTimeout(() => {
      map.invalidateSize();
    }, 150);

    if ('ResizeObserver' in window) {
      resizeObserverRef.current = new ResizeObserver(() => {
        window.setTimeout(() => map.invalidateSize(), 50);
      });
      resizeObserverRef.current.observe(containerRef.current);
    }

    return () => {
      window.clearTimeout(resizeTimeout);
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = null;
      map.remove();
      mapRef.current = null;
      baseLayerRef.current = null;
    };
  }, [center, offlineTiles, zoom]);

  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.setView(center, zoom);
    }
  }, [center, zoom]);

  useEffect(() => {
    if (!mapRef.current || !markersLayerRef.current) return;

    markersLayerRef.current.clearLayers();
    baseLayerRef.current?.clearLayers();

    if (baseLayerRef.current) {
      const bounds = buildBounds(markers);
      const south = bounds.getSouth();
      const north = bounds.getNorth();
      const west = bounds.getWest();
      const east = bounds.getEast();

      L.rectangle(bounds, {
        color: '#9fb2c7',
        weight: 1.5,
        fillColor: '#eef6f8',
        fillOpacity: offlineTiles ? 0.95 : 0.16,
      }).addTo(baseLayerRef.current);

      const latStep = Math.max((north - south) / 5, 0.01);
      const lngStep = Math.max((east - west) / 5, 0.01);
      for (let i = 1; i < 5; i += 1) {
        const lat = south + latStep * i;
        const lng = west + lngStep * i;
        L.polyline([[lat, west], [lat, east]], { color: offlineTiles ? '#d6e0ea' : '#5f7fa5', opacity: offlineTiles ? 1 : 0.38, weight: 1, dashArray: '5 6' }).addTo(baseLayerRef.current);
        L.polyline([[south, lng], [north, lng]], { color: offlineTiles ? '#d6e0ea' : '#5f7fa5', opacity: offlineTiles ? 1 : 0.38, weight: 1, dashArray: '5 6' }).addTo(baseLayerRef.current);
      }

      const uniqueCells = new Map<string, MapMarker>();
      markers.forEach((marker) => uniqueCells.set(extractPincode(marker), marker));
      uniqueCells.forEach((marker, label) => {
        L.circle([marker.lat, marker.lng], {
          radius: 900,
          color: '#5f7fa5',
          weight: 1,
          fillColor: '#d9e9f2',
          fillOpacity: offlineTiles ? 0.55 : 0.26,
        }).addTo(baseLayerRef.current!);

        L.marker([marker.lat + 0.006, marker.lng], {
          interactive: false,
          icon: L.divIcon({
            className: 'satark-map-label',
            html: `<span>${label}</span>`,
            iconSize: [80, 18],
            iconAnchor: [40, 9],
          }),
        }).addTo(baseLayerRef.current!);
      });
    }

    markers.forEach((markerData) => {
      const color = markerData.badgeColor || '#14387F';
      const markerIcon = L.divIcon({
        className: 'custom-leaflet-marker-wrapper',
        html: `
          <div style="width:24px;height:24px;position:relative;display:flex;align-items:center;justify-content:center;">
            <div style="position:absolute;width:24px;height:24px;border-radius:999px;opacity:.24;background:${color};"></div>
            <div style="position:absolute;width:16px;height:16px;border-radius:999px;border:2px solid white;box-shadow:0 8px 16px rgba(15,23,42,.22);cursor:pointer;background:${color};" title="${markerData.title}"></div>
          </div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const marker = L.marker([markerData.lat, markerData.lng], { icon: markerIcon })
        .addTo(markersLayerRef.current!)
        .bindPopup(`
          <div style="font-family:Inter,'Source Sans 3','Noto Sans',sans-serif;font-size:12px;color:#1a1a1a;text-align:left;padding:4px;line-height:1.4;">
            <strong style="color:#0b2e5e;display:block;font-size:13px;margin-bottom:2px;">${markerData.title}</strong>
            ${markerData.subtitle ? `<span style="color:#5a6577;display:block;margin-bottom:6px;">${markerData.subtitle}</span>` : ''}
            ${markerData.badge ? `<span style="display:inline-block;background-color:${color}15;color:${color};font-size:9px;font-weight:600;border:1px solid ${color}35;border-radius:4px;padding:1px 6px;text-transform:uppercase;">${markerData.badge}</span>` : ''}
          </div>
        `);

      if (onMarkerClick) {
        marker.on('click', () => onMarkerClick(markerData.id));
      }
    });

    if (markers.length > 0) {
      mapRef.current.fitBounds(buildBounds(markers), { maxZoom: zoom, animate: true });
      window.setTimeout(() => mapRef.current?.invalidateSize(), 50);
    } else {
      mapRef.current.setView(center, zoom);
    }
  }, [markers, onMarkerClick, center, zoom, offlineTiles]);

  return (
    <div
      className="satark-leaflet-map w-full relative rounded-xl overflow-hidden border border-slate-200 shadow-inner bg-slate-50"
      style={{ height }}
    >
      <div ref={containerRef} className="w-full h-full" />
      {markers.length === 0 && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-slate-50/75 text-[11px] font-bold text-slate-500">
          No mapped records for the selected filter
        </div>
      )}
    </div>
  );
};
