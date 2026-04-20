import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import * as d3 from "d3";
import { fetchRegions, fetchRecipe } from "../../hooks/useApi.js";
import "./MapView.css";

// Fix Leaflet's default marker icon path issue with Vite
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

function MapView({ onRecipeSelect }) {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);
  const [regions, setRegions] = useState([]);

  // Initialise the Leaflet map
  useEffect(() => {
    if (mapInstance.current) return; // already initialised

    mapInstance.current = L.map(mapRef.current, {
      center: [54.0, -2.0], // Centre on UK for the proof of concept
      zoom: 6,
      zoomControl: true,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 18,
    }).addTo(mapInstance.current);

    return () => {
      mapInstance.current?.remove();
      mapInstance.current = null;
    };
  }, []);

  // Load regions from API and add D3-powered markers
  useEffect(() => {
    fetchRegions().then((data) => setRegions(data));
  }, []);

  useEffect(() => {
    if (!mapInstance.current || regions.length === 0) return;

    regions.forEach((region) => {
      region.recipe_ids.forEach(async (recipeId) => {
        const recipe = await fetchRecipe(recipeId);
        if (!recipe) return;

        // Use a custom D3-generated SVG icon for each marker
        const svgIcon = createD3MarkerIcon(recipe.name);

        const marker = L.marker(recipe.coordinates, { icon: svgIcon }).addTo(
          mapInstance.current
        );

        marker.on("click", () => {
          onRecipeSelect(recipe);
          mapInstance.current.flyTo(recipe.coordinates, 9, { duration: 1.2 });
        });

        marker.bindTooltip(recipe.name, { direction: "top", offset: [0, -30] });
      });
    });
  }, [regions, onRecipeSelect]);

  return <div ref={mapRef} className="map-container" />;
}

/**
 * Creates a custom Leaflet icon using an inline SVG generated with D3.
 */
function createD3MarkerIcon(label) {
  const size = 36;
  const color = "#c0392b";

  // Build SVG string — D3 colour scale can be swapped in for multi-country theming
  const scale = d3.scaleOrdinal(d3.schemeTableau10);
  const fill = scale(label);

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 36 36">
      <circle cx="18" cy="18" r="14" fill="${fill}" stroke="white" stroke-width="2.5"/>
      <text x="18" y="23" text-anchor="middle" font-size="14" fill="white">🍽</text>
    </svg>`;

  return L.divIcon({
    html: svg,
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

export default MapView;
