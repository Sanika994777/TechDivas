import { useEffect, useRef } from "react";
import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
import L from "leaflet";
import { MapPin } from "lucide-react";
import { BASE_URL } from "@/api/client";

// Fix default icon paths broken by Vite
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({ iconUrl: markerIcon, iconRetinaUrl: markerIcon2x, shadowUrl: markerShadow });

// Custom saffron pin icon
const saffronIcon = new L.Icon({
  iconUrl: `data:image/svg+xml,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="24" height="36">
      <path d="M12 0C5.373 0 0 5.373 0 12c0 9 12 24 12 24s12-15 12-24C24 5.373 18.627 0 12 0z" fill="#FF9933"/>
      <circle cx="12" cy="12" r="5" fill="white"/>
    </svg>
  `)}`,
  iconSize: [24, 36],
  iconAnchor: [12, 36],
  popupAnchor: [0, -36],
});

interface MapPickerProps {
  lat: number;
  lng: number;
  onChange: (lat: number, lng: number, address?: string) => void;
}

// Inner component that listens for map clicks
function ClickHandler({ onChange }: { onChange: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onChange(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

export function MapPicker({ lat, lng, onChange }: MapPickerProps) {
  const markerRef = useRef<L.Marker>(null);

  async function reverseGeocode(la: number, lo: number) {
    try {
      const res = await fetch(
        `${BASE_URL}/api/geo/reverse?lat=${la}&lng=${lo}`,
        { signal: AbortSignal.timeout(5000) }
      );
      const data = await res.json();
      const addr = data.display_name ?? data.address ?? `${la.toFixed(5)}, ${lo.toFixed(5)}`;
      onChange(la, lo, addr);
    } catch {
      onChange(la, lo); // graceful fallback
    }
  }

  return (
    <div className="space-y-2">
      <div className="rounded-card overflow-hidden border border-gray-200 shadow-card" style={{ height: 320 }}>
        <MapContainer
          center={[lat, lng]}
          zoom={15}
          style={{ height: "100%", width: "100%" }}
          scrollWheelZoom={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ClickHandler
            onChange={(la, lo) => {
              reverseGeocode(la, lo);
            }}
          />
          <Marker
            position={[lat, lng]}
            icon={saffronIcon}
            draggable
            ref={markerRef}
            eventHandlers={{
              dragend() {
                const m = markerRef.current;
                if (m) {
                  const { lat: la, lng: lo } = m.getLatLng();
                  reverseGeocode(la, lo);
                }
              },
            }}
          />
        </MapContainer>
      </div>
      <p className="text-xs text-gray-500 flex items-center gap-1">
        <MapPin size={12} className="text-saffron" />
        Tap the map or drag the pin to set the exact location
      </p>
    </div>
  );
}
