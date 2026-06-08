# Regional Dishes 🗺️

An interactive map website where users can explore traditional recipes from different regions of the world. Click a pin on the map to discover the dish's history and full recipe.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + Vite |
| Mapping | Leaflet.js + D3.js |
| Backend | Python / FastAPI |
| Data | JSON flat files (upgradeable to a database) |

## Project Structure

```
regional-dishes/
├── frontend/               # React application
│   ├── public/
│   └── src/
│       ├── components/
│       │   ├── Map/        # Leaflet + D3 map view
│       │   ├── RecipeCard/ # Recipe detail card
│       │   └── Sidebar/    # Sliding panel
│       ├── hooks/          # API fetching helpers
│       └── styles/
├── backend/                # FastAPI application
│   ├── app/
│   │   ├── api/routes/     # Recipe & region endpoints
│   │   ├── models/         # Pydantic schemas
│   │   └── services/       # Data loading logic
│   ├── data/               # JSON recipe & region data
│   └── tests/
└── README.md
```

## Getting Started

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

App will open at `http://localhost:5173`.

### Running Tests

```bash
cd backend
pytest
```

## Adding a New Recipe

1. Add a region entry to `backend/data/regions.json` (if it's a new region).
2. Add the full recipe object to `backend/data/recipes.json` following the existing schema.
3. The pin will appear on the map automatically — no code changes needed.

## Data Sources

Recipe images and supplementary data are sourced from **[TheMealDB](https://www.themealdb.com/api.php)** — a free, open recipe database and JSON API.

- Free API key `"1"` is used for development / educational use.
- The script `backend/scripts/populate_from_mealdb.py` queries the API and backfills `image_url` (and any other missing fields) into `recipes.json`.
- Run it any time you add new recipes: `python backend/scripts/populate_from_mealdb.py`
- For production use, a paid TheMealDB supporter key is recommended (unlocks full dataset access).

> TheMealDB API: https://www.themealdb.com/api.php  
> License: free at point of access; see [TheMealDB Terms](https://www.themealdb.com/terms_of_use.php).

## Roadmap

- [ ] UK (Cornwall, Scotland) — proof of concept ✅
- [ ] Expand to additional countries
- [ ] Add search / filter by ingredient or tag
- [ ] User-submitted recipes
- [x] Image support via TheMealDB API
