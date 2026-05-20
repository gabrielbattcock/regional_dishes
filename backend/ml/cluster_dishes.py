"""
Dish Clustering Pipeline
========================
Clusters regional dishes using TF-IDF on ingredient text + one-hot encoded
cooking methods. Outputs clusters.json to backend/data/ with:
  - cluster assignments for each dish
  - t-SNE 2D coordinates for visualisation
  - top dish-to-dish similarity connections (cosine similarity)
  - cluster labels (auto-generated from shared features)

Usage:
  python cluster_dishes.py
  (run from the backend/ directory, or update DATA_DIR below)
"""

import json
import os
import re
import numpy as np
from pathlib import Path

# ── Dependencies ────────────────────────────────────────────────────────────
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import OneHotEncoder, normalize
    from sklearn.cluster import KMeans
    from sklearn.manifold import TSNE
    from sklearn.metrics.pairwise import cosine_similarity
    import scipy.sparse as sp
except ImportError as e:
    raise SystemExit(
        f"Missing dependency: {e}\n"
        "Run:  pip install scikit-learn scipy --break-system-packages"
    )

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR   = SCRIPT_DIR.parent / "data"
INPUT_FILE = DATA_DIR / "recipes.json"
OUTPUT_FILE = DATA_DIR / "clusters.json"

# ── Config ───────────────────────────────────────────────────────────────────
N_CLUSTERS = 6          # number of k-means clusters
TOP_CONNECTIONS = 4     # max similar dishes per dish to store as edges
SIM_THRESHOLD = 0.12    # minimum cosine similarity to include a connection
TSNE_PERPLEXITY = 5     # keep low for small datasets (< 30 items)
RANDOM_STATE = 42

# ── Ingredient normalisation helpers ─────────────────────────────────────────
INGREDIENT_ALIASES = {
    # proteins
    r"\b(skirt beef|beef chuck|beef brisket|beef mince|coarse-ground beef)\b": "beef",
    r"\b(ground pork|pork mince|coarse-ground pork|pork shoulder|pork back fat|pork belly)\b": "pork",
    r"\b(lamb neck|lamb shoulder|lamb offal|lamb on the bone)\b": "lamb",
    r"\b(veal shank|veal shanks)\b": "veal",
    r"\b(cod|haddock|fish fillet)\b": "white fish",
    r"\b(sheep.s milk ricotta|ricotta)\b": "ricotta",
    r"\b(fior di latte|buffalo mozzarella|mozzarella)\b": "mozzarella",
    r"\b(parmigiano.reggiano|parmigiano|parmesan)\b": "parmesan",
    r"\b(pecorino romano|pecorino sardo|pecorino)\b": "pecorino",
    r"\b(mascarpone cheese|mascarpone)\b": "mascarpone",
    r"\b(guanciale|pancetta|bacon)\b": "cured pork",
    # carbs
    r"\b(strong plain flour|plain flour|type.00.flour|strong bread flour|bread flour)\b": "flour",
    r"\b(floury potatoes|maris piper potatoes|potato|potatoes)\b": "potato",
    r"\b(arborio rice|carnaroli rice|arborio|carnaroli)\b": "risotto rice",
    r"\b(pearl barley|pinhead oatmeal|oatmeal|oats)\b": "oats or barley",
    r"\b(savoiardi|ladyfinger biscuits)\b": "sponge biscuits",
    r"\b(tonnarelli|spaghetti|tagliatelle|trofie|trenette|pasta)\b": "pasta",
    r"\b(stale tuscan bread|stale bread|tuscan bread)\b": "stale bread",
    # dairy/fat
    r"\b(double cream|whipping cream)\b": "cream",
    r"\b(unsalted butter|butter|lard or shortening|lard or butter|lard)\b": "butter or lard",
    r"\b(whole milk)\b": "milk",
    r"\b(extra.virgin olive oil|extra.virgin ligurian olive oil|olive oil)\b": "olive oil",
    r"\b(beef dripping|sunflower oil|vegetable oil|suet)\b": "cooking fat",
    # vegetables
    r"\b(onions?|red onion)\b": "onion",
    r"\b(leeks?)\b": "leek",
    r"\b(carrots?)\b": "carrot",
    r"\b(celery stalks?|celery)\b": "celery",
    r"\b(turnips?|swede)\b": "root vegetable",
    r"\b(parsnips?)\b": "parsnip",
    r"\b(cavolo nero|black kale|kale)\b": "dark leafy greens",
    r"\b(san marzano tomatoes|tinned tomatoes|tomatoes?|tomato paste)\b": "tomato",
    r"\b(garlic cloves?|garlic)\b": "garlic",
    r"\b(fresh raspberries|raspberries?)\b": "raspberry",
    r"\b(fresh strawberries|strawberries?)\b": "strawberry",
    # flavourings
    r"\b(scotch whisky|whisky|marsala wine|dry white wine|dark ale|stout|beer)\b": "alcohol",
    r"\b(espresso|strong espresso)\b": "coffee",
    r"\b(saffron threads?|saffron)\b": "saffron",
    r"\b(ground black pepper|black pepper|black peppercorns?|coarsely ground black pepper)\b": "black pepper",
    r"\b(english mustard|mustard)\b": "mustard",
    r"\b(worcestershire sauce)\b": "worcestershire",
    r"\b(caster sugar|icing sugar|cane sugar)\b": "sugar",
    r"\b(eggs?|egg yolks?|egg whites?)\b": "egg",
    r"\b(fresh basil leaves?|basil)\b": "basil",
    r"\b(fresh parsley|flat.leaf parsley|parsley)\b": "parsley",
    r"\b(ground almonds|flaked almonds|almond extract|pine nuts)\b": "nuts or almonds",
    r"\b(raspberry jam)\b": "jam",
    r"\b(cannellini beans)\b": "beans",
    r"\b(frozen peas)\b": "peas",
    r"\b(heather honey|honey)\b": "honey",
    r"\b(candied orange peel)\b": "candied fruit",
    r"\b(dark chocolate chips)\b": "chocolate",
    r"\b(sheep.s stomach|hog casings|natural hog casings|artificial casing)\b": "casing",
}

COOKING_METHODS = [
    "baked", "braised", "boiled", "deep-fried", "grilled",
    "simmered", "no-cook"
]

# ── Cluster label hints (used for human-readable names) ──────────────────────
CLUSTER_THEME_MAP = {
    frozenset(["beef", "potato", "flour"]): "Hearty meat & pastry",
    frozenset(["lamb", "onion", "carrot"]): "Slow-cooked lamb broths",
    frozenset(["pasta", "cheese", "egg"]): "Roman pasta classics",
    frozenset(["pasta", "tomato", "beef"]): "Meaty pasta sauces",
    frozenset(["cream", "sugar", "egg"]): "Rich cream desserts",
    frozenset(["flour", "olive oil", "tomato"]): "Baked doughs & breads",
    frozenset(["ricotta", "flour", "alcohol"]): "Sicilian sweets",
    frozenset(["pork", "oats or barley", "black pepper"]): "Cured & spiced meats",
    frozenset(["risotto rice", "parmesan", "saffron"]): "Northern Italian rice",
    frozenset(["stale bread", "tomato", "olive oil"]): "Tuscan bread dishes",
}

# ── Load data ────────────────────────────────────────────────────────────────

def load_recipes(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)


# ── Feature engineering ──────────────────────────────────────────────────────

def normalise_ingredient(raw: str) -> str:
    """Lower-case and apply alias substitutions to a single ingredient string."""
    text = raw.lower()
    for pattern, replacement in INGREDIENT_ALIASES.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def recipe_to_ingredient_doc(recipe: dict) -> str:
    """Return a space-joined string of normalised ingredient tokens for TF-IDF."""
    items = [ing["item"] for ing in recipe.get("ingredients", [])]
    normalised = [normalise_ingredient(item) for item in items]
    # also add tags as weak signals
    tags = recipe.get("tags", [])
    return " ".join(normalised + tags)


def build_feature_matrix(recipes: list[dict]):
    """
    Combine:
      1. TF-IDF of normalised ingredient documents  (weighted 0.7)
      2. One-hot encoded cooking method              (weighted 0.3)
    Returns a dense numpy array and the vectorizers.
    """
    docs = [recipe_to_ingredient_doc(r) for r in recipes]
    methods = [[r.get("cooking_method", "unknown")] for r in recipes]

    # TF-IDF
    tfidf = TfidfVectorizer(
        min_df=1,
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    X_tfidf = tfidf.fit_transform(docs)  # sparse (n_dishes, n_terms)

    # One-hot cooking method
    ohe = OneHotEncoder(
        categories=[COOKING_METHODS + ["unknown"]],
        sparse_output=True,
        handle_unknown="ignore",
    )
    X_method = ohe.fit_transform(methods)  # sparse (n_dishes, n_methods)

    # Weight and hstack
    X_combined = sp.hstack([X_tfidf * 0.70, X_method * 0.30])

    # L2 normalise rows for cosine similarity
    X_norm = normalize(X_combined, norm="l2")

    return X_norm, tfidf, ohe


# ── Clustering ───────────────────────────────────────────────────────────────

def run_kmeans(X, n_clusters: int, random_state: int = RANDOM_STATE):
    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=20)
    labels = km.fit_predict(X)
    return labels, km


def run_tsne(X, perplexity: int = TSNE_PERPLEXITY, random_state: int = RANDOM_STATE):
    """Return 2D t-SNE coordinates as a list of [x, y] pairs."""
    X_dense = X.toarray() if sp.issparse(X) else X
    tsne = TSNE(
        n_components=2,
        perplexity=perplexity,
        random_state=random_state,
        max_iter=2000,
        learning_rate="auto",
        init="pca",
    )
    coords = tsne.fit_transform(X_dense)
    # Normalise to [-1, 1] range for easy frontend use
    for i in range(2):
        mn, mx = coords[:, i].min(), coords[:, i].max()
        coords[:, i] = 2 * (coords[:, i] - mn) / (mx - mn + 1e-9) - 1
    return coords.tolist()


# ── Similarity connections ───────────────────────────────────────────────────

def build_connections(X, recipe_ids: list[str], top_k: int, threshold: float):
    """
    For each dish, find the top_k most similar other dishes above threshold.
    Returns a list of { source, target, similarity } dicts.
    """
    X_dense = X.toarray() if sp.issparse(X) else X
    sim_matrix = cosine_similarity(X_dense)  # (n, n)
    connections = []
    seen = set()
    for i, src_id in enumerate(recipe_ids):
        row = sim_matrix[i].copy()
        row[i] = 0  # exclude self
        top_indices = np.argsort(row)[::-1][:top_k]
        for j in top_indices:
            score = float(row[j])
            if score < threshold:
                continue
            # deduplicate undirected edges
            edge_key = tuple(sorted([src_id, recipe_ids[j]]))
            if edge_key in seen:
                continue
            seen.add(edge_key)
            connections.append({
                "source": src_id,
                "target": recipe_ids[j],
                "similarity": round(score, 4),
            })
    # sort by similarity descending
    connections.sort(key=lambda x: x["similarity"], reverse=True)
    return connections


# ── Cluster label inference ──────────────────────────────────────────────────

def infer_cluster_label(cluster_id: int, members: list[dict]) -> str:
    """
    Derive a readable cluster label from the most common normalised ingredients
    across the dishes in the cluster.
    """
    all_terms: list[str] = []
    for r in members:
        doc = recipe_to_ingredient_doc(r)
        all_terms.extend(doc.split())

    # Count term frequency
    freq: dict[str, int] = {}
    for t in all_terms:
        freq[t] = freq.get(t, 0) + 1

    # Remove very generic tokens
    STOPWORDS = {
        "to", "taste", "salt", "water", "and", "or", "for", "the",
        "black", "pepper", "oil", "sauce", "ground", "fresh", "dried",
        "large", "medium", "small", "white", "red",
    }
    top = sorted(
        [(k, v) for k, v in freq.items() if k not in STOPWORDS and len(k) > 3],
        key=lambda x: x[1], reverse=True,
    )[:5]
    keywords = [t[0] for t in top]

    # Check theme map
    keyword_set = frozenset(keywords[:3])
    for theme_keys, label in CLUSTER_THEME_MAP.items():
        if len(theme_keys & keyword_set) >= 2:
            return label

    # Fallback: join top 3 keywords
    if keywords:
        return " · ".join(keywords[:3]).title()
    return f"Cluster {cluster_id + 1}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Loading recipes from {INPUT_FILE} …")
    recipes = load_recipes(INPUT_FILE)
    n = len(recipes)
    print(f"  {n} dishes loaded.")

    # Adjust t-SNE perplexity to be < n
    perplexity = min(TSNE_PERPLEXITY, n - 1)

    print("Building feature matrix …")
    X, tfidf, ohe = build_feature_matrix(recipes)

    print(f"Running k-means with {N_CLUSTERS} clusters …")
    labels, km = run_kmeans(X, N_CLUSTERS)

    print("Running t-SNE for 2D layout …")
    coords_2d = run_tsne(X, perplexity=perplexity)

    print(f"Computing dish similarity connections (top {TOP_CONNECTIONS} per dish) …")
    recipe_ids = [r["id"] for r in recipes]
    connections = build_connections(X, recipe_ids, TOP_CONNECTIONS, SIM_THRESHOLD)
    print(f"  {len(connections)} edges found.")

    # ── Assemble per-cluster metadata ────────────────────────────────────────
    cluster_members: dict[int, list[dict]] = {i: [] for i in range(N_CLUSTERS)}
    for recipe, label in zip(recipes, labels):
        cluster_members[int(label)].append(recipe)

    cluster_meta = {}
    for cid, members in cluster_members.items():
        cluster_meta[cid] = {
            "id": cid,
            "label": infer_cluster_label(cid, members),
            "dish_ids": [r["id"] for r in members],
            "size": len(members),
        }

    # ── Assemble per-dish output ──────────────────────────────────────────────
    dishes_out = []
    for i, recipe in enumerate(recipes):
        dishes_out.append({
            "id": recipe["id"],
            "name": recipe["name"],
            "country": recipe["country"],
            "region": recipe["region"],
            "cooking_method": recipe.get("cooking_method", "unknown"),
            "cluster": int(labels[i]),
            "tsne_x": round(coords_2d[i][0], 5),
            "tsne_y": round(coords_2d[i][1], 5),
        })

    output = {
        "meta": {
            "n_dishes": n,
            "n_clusters": N_CLUSTERS,
            "algorithm": "KMeans",
            "features": "TF-IDF ingredients (0.7) + one-hot cooking method (0.3)",
            "layout": "t-SNE 2D (normalised to [-1,1])",
        },
        "clusters": [cluster_meta[i] for i in range(N_CLUSTERS)],
        "dishes": dishes_out,
        "connections": connections,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Saved clusters.json → {OUTPUT_FILE}")

    # ── Human-readable summary ───────────────────────────────────────────────
    print("\n── Cluster Summary ──────────────────────────────────────────────")
    for cid in range(N_CLUSTERS):
        meta = cluster_meta[cid]
        names = [r["name"] for r in cluster_members[cid]]
        print(f"  [{cid}] {meta['label']} ({meta['size']} dishes)")
        for name in names:
            print(f"       • {name}")

    print(f"\n── Top 10 Connections ───────────────────────────────────────────")
    for conn in connections[:10]:
        src = next(r["name"] for r in recipes if r["id"] == conn["source"])
        tgt = next(r["name"] for r in recipes if r["id"] == conn["target"])
        print(f"  {src}  ↔  {tgt}  (sim={conn['similarity']})")


if __name__ == "__main__":
    main()
