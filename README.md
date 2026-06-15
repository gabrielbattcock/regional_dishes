# Regional Dishes 🗺️

An interactive map for exploring traditional recipes from different regions of the world - an expansion of some work my dad had done during COVID lockdown, trying to cook one dish from every region in the USA and UK, and for each country. Linked with my current work, I'm also trying to use clustering techniques to find connections between the dishes. 

Click a pin to discover a dish's history, ingredients and method. Switch to the Connections tab to see how dishes across countries cluster together by shared ingredients and cooking technique.

I want the map ultimately be interactive, so anyone can add in forgotten regional dishes, especially from the UK. 

## Tech Stack

| Layer | Technology |
|---|---|
| App | Python / Plotly Dash |
| Maps | Plotly Scattermap (carto-darkmatter tiles) |
| Charts | Plotly Graph Objects |
| Styling | Dash Bootstrap Components (DARKLY theme) |
| Data | JSON flat files |
| ML | scikit-learn (k-means + t-SNE) |

## Project Structure

```
regional-dishes/
├── app.py              # The entire Dash application
├── requirements.txt
├── HOW_IT_WORKS.md     # Code walkthrough and editing guide
├── data/
│   ├── recipes.json    # 28 dishes with history, ingredients & steps
│   ├── regions.json    # 16 regions with coordinates
│   └── clusters.json   # ML output: clusters, t-SNE positions, connections
├── ml/
│   └── cluster_dishes.py   # Clustering pipeline (regenerates clusters.json)
└── README.md
```

## Getting Started

```bash
cd backend
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:8050` in your browser.

## Adding a New Dish

1. Add the recipe object to `backend/data/recipes.json` (follow the existing schema — id, name, region, country, coordinates, short_description, history, ingredients, steps, tags, cooking_method).
2. Add its `id` to the correct region's `recipe_ids` list in `backend/data/regions.json`. If it's a new region, add a region entry too.
3. Regenerate the ML clusters so the new dish appears in the Connections tab:
   ```bash
   python ml/cluster_dishes.py
   ```
4. Restart `app.py` — the pin appears on the map automatically.

## Changing the Number of Clusters

Open `ml/cluster_dishes.py` and change `N_CLUSTERS = 8` to whatever you want, then re-run the script. Restart the app to pick up the new `clusters.json`.

## Coverage

| Country | Regions | Dishes |
|---|---|---|
| 🇬🇧 United Kingdom | Cornwall, Scotland (×2), Yorkshire (×2), Wales (×2), Lancashire (×2), Cumbria, Derbyshire, Berkshire | 14 |
| 🇮🇹 Italy | Campania, Emilia-Romagna, Lombardy (×2), Sicily (×2), Tuscany (×3), Lazio (×2), Liguria (×2), Veneto | 14 |

## Roadmap

- [x] UK proof of concept
- [x] Expand to Italy
- [x] ML clustering — dish connections by ingredient & cooking method
- [x] Plotly Dash app (replaced React + FastAPI)
- [x] Add a third country (USA)
- [ ] Search / filter by ingredient, tag or cooking method
- [ ] Image support per dish
- [ ] User-submitted recipes
