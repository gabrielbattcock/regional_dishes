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
| ML | scikit-learn (k-means + t-SNE; notebook compares against GMM, agglomerative & spectral) |

## Project Structure

```
regional-dishes/
├── app.py              # The entire Dash application
├── requirements.txt
├── data/
│   ├── recipes.json    # 133 dishes with history, ingredients & steps
│   ├── regions.json    # 124 regions with coordinates
│   └── clusters.json   # ML output: clusters, t-SNE positions, connections
├── ml/
│   ├── cluster_dishes.py      # Clustering pipeline (regenerates clusters.json)
│   └── ingredient_taxonomy.py # Ingredient hierarchy (group → subgroup → canonical) used for feature engineering
├── notebooks/
│   └── cluster_dishes_test.ipynb  # Standalone exploration comparing clustering algorithms
└── README.md
```


## Coverage

| Country | Regions | Dishes |
|---|---|---|
| 🇬🇧 United Kingdom | 63 (all counties across England, Scotland, Wales & Northern Ireland) | 63 |
| 🇺🇸 United States | 53 (50 states + Guam, Puerto Rico, American Samoa) | 56 |
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
