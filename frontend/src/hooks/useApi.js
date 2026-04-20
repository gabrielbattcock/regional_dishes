const API_BASE = "/api";

export async function fetchRegions() {
  const res = await fetch(`${API_BASE}/regions/`);
  if (!res.ok) throw new Error("Failed to fetch regions");
  return res.json();
}

export async function fetchRecipes() {
  const res = await fetch(`${API_BASE}/recipes/`);
  if (!res.ok) throw new Error("Failed to fetch recipes");
  return res.json();
}

export async function fetchRecipe(id) {
  const res = await fetch(`${API_BASE}/recipes/${id}`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchRecipesByRegion(regionId) {
  const res = await fetch(`${API_BASE}/recipes/region/${regionId}`);
  if (!res.ok) return [];
  return res.json();
}
