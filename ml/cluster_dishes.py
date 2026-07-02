"""
Dish Clustering Pipeline
========================
Clusters regional dishes using TF-IDF on ingredient text + one-hot encoded
cooking methods and ingredient groups. Outputs clusters.json to data/ with:
  - cluster assignments for each dish
  - t-SNE 2D coordinates for visualisation
  - top dish-to-dish similarity connections (cosine similarity)
  - cluster labels (auto-generated from shared features)

Ingredient normalisation is handled by ingredient_taxonomy.py (same directory),
which provides a 3-level hierarchy: group → subgroup → canonical.
The feature document for each dish includes tokens at all three levels so the
model can cluster on fine detail (canonical) AND coarse character (group).

Usage:
  python cluster_dishes.py
  (run from the ml/ directory, or update DATA_DIR below)
"""

import json
import sys
import numpy as np
from pathlib import Path

# ── Taxonomy import ──────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))   # ensure ml/ is on the path
try:
    from ingredient_taxonomy import (
        normalize as tax_normalize,
        featurize as tax_featurize,
        HIERARCHY,
    )
except ImportError as e:
    raise SystemExit(
        f"Cannot import ingredient_taxonomy: {e}\n"
        "Make sure ingredient_taxonomy.py is in the same directory."
    )

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
DATA_DIR    = SCRIPT_DIR.parent / "data"
INPUT_FILE  = DATA_DIR / "recipes.json"
OUTPUT_FILE = DATA_DIR / "clusters.json"

# ── Config ───────────────────────────────────────────────────────────────────
N_CLUSTERS      = 8      # number of k-means clusters (raised — richer dataset)
TOP_CONNECTIONS = 4      # max similar dishes per dish to store as edges
SIM_THRESHOLD   = 0.12   # minimum cosine similarity to include a connection
TSNE_PERPLEXITY = 10     # raise when dataset grows; kept low for < 50 items
RANDOM_STATE    = 42

# Weighting of the three feature blocks:
W_CANONICAL  = 0.55   # fine-grained TF-IDF over canonical ingredient tokens
W_SUBGROUP   = 0.25   # medium-resolution subgroup presence tokens
W_GROUP      = 0.10   # coarse group presence (one-hot per hierarchy group)
W_METHOD     = 0.10   # one-hot cooking method


  
COOKING_METHODS = [
    "air-fried",
    "baked",
    "barbecued",
    "blanched",
    "boiled",
    "braised",
    "broiled",
    "char-grilled",
    "deep-fried",
    "fried",
    "dry-fried",
    "flash-fried",
    "grilled",
    "griddled",
    "microwaved",
    "no-cook",
    "pan-fried",
    "poached",
    "pressure-cooked",
    "roasted",
    "rotisserie",
    "sauteed",
    "seared",
    "shallow-fried",
    "simmered",
    "slow-cooked",
    "smoked",
    "steam-baked",
    "steamed",
    "stewed",
    "stir-fried",
    "toasted",
    "wood-fired",
    "wok-fried",
      
    # Combined methods often found in recipes
    "bake-fried",
    "grilled-roasted",
    "braised-roasted",
    "smoke-roasted",
    "steam-cooked"
]

# All top-level groups in the hierarchy (used for one-hot group features)
ALL_GROUPS = list(HIERARCHY.keys())

# ── Cluster label hints (updated to taxonomy canonical names) ─────────────────
CLUSTER_THEME_MAP = {
    frozenset(["beef", "potato", "flour"]):            "Hearty meat & pastry",
    frozenset(["lamb", "onion", "carrot"]):            "Slow-cooked lamb broths",
    frozenset(["pasta", "egg", "cured pork"]):         "Roman pasta classics",
    frozenset(["pasta", "tomato", "beef"]):            "Meaty pasta sauces",
    frozenset(["cream", "sugar", "egg"]):              "Rich cream desserts",
    frozenset(["flour", "olive oil", "tomato"]):       "Baked doughs & breads",
    frozenset(["ricotta", "flour", "whisky"]):         "Sicilian sweets",
    frozenset(["pork", "oats", "black pepper"]):       "Cured & spiced meats",
    frozenset(["risotto rice", "parmesan", "saffron"]):"Northern Italian rice",
    frozenset(["stale bread", "tomato", "olive oil"]): "Tuscan bread dishes",
    frozenset(["potato", "leek", "butter"]):           "British comfort food",
    frozenset(["oats", "barley", "lamb"]):             "Scottish & Northern broths",
    frozenset(["flour", "butter", "sugar"]):           "Baked goods & puddings",
    frozenset(["white fish", "potato", "cream"]):      "Fish & seafood dishes",
}

# ── Load data ────────────────────────────────────────────────────────────────

def load_recipes(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)


# ── Feature engineering ──────────────────────────────────────────────────────

def recipe_to_ingredient_lines(recipe: dict) -> list[str]:
    """Extract raw ingredient item strings from a recipe."""
    return [ing["item"] for ing in recipe.get("ingredients", [])]


def recipe_to_canonical_doc(recipe: dict) -> str:
    """
    Return a space-joined string of canonical ingredient tokens for TF-IDF.
    Uses ingredient_taxonomy.normalize() — much richer than the old alias dict.
    Unrecognised ingredients are included as-is (lowercased) so no signal is lost.
    Also appends any recipe tags as extra tokens.
    """
    lines = recipe_to_ingredient_lines(recipe)
    tokens = []
    for line in lines:
        canon = tax_normalize(line)
        tokens.append(canon if canon is not None else line.lower())
    tags = recipe.get("tags", [])
    return " ".join(tokens + tags)


def recipe_to_subgroup_doc(recipe: dict) -> str:
    """
    Space-joined string of subgroup tokens (one per recognised ingredient).
    Tokens are repeated proportionally to ingredient count via Counter.
    """
    lines = recipe_to_ingredient_lines(recipe)
    counts = tax_featurize(lines, "subgroup")
    # repeat each subgroup token by its count so TF-IDF sees frequency
    return " ".join(
        token.replace(" ", "_").replace("&", "and")
        for token, cnt in counts.items()
        for _ in range(cnt)
    )


def recipe_group_flags(recipe: dict) -> list[str]:
    """
    Return the list of top-level hierarchy groups present in this recipe.
    Used for one-hot group presence features.
    """
    lines = recipe_to_ingredient_lines(recipe)
    group_counts = tax_featurize(lines, "group")
    return [g for g in ALL_GROUPS if g in group_counts]


def build_feature_matrix(recipes: list[dict]):
    """
    Combine four weighted feature blocks:
      1. TF-IDF of canonical ingredient tokens          (W_CANONICAL)
      2. TF-IDF of subgroup tokens                      (W_SUBGROUP)
      3. Multi-hot group presence (one column per group) (W_GROUP)
      4. One-hot cooking method                          (W_METHOD)

    All blocks are L2-normalised before weighting so weights are comparable.
    Returns the combined L2-normalised sparse matrix.
    """
    canonical_docs  = [recipe_to_canonical_doc(r)  for r in recipes]
    subgroup_docs   = [recipe_to_subgroup_doc(r)   for r in recipes]
    methods         = [[r.get("cooking_method", "unknown")] for r in recipes]

    # ── Block 1: canonical TF-IDF ────────────────────────────────────────────
    tfidf_canon = TfidfVectorizer(min_df=1, ngram_range=(1, 2), sublinear_tf=True)
    X_canon = tfidf_canon.fit_transform(canonical_docs)   # sparse

    # ── Block 2: subgroup TF-IDF ─────────────────────────────────────────────
    tfidf_sub = TfidfVectorizer(min_df=1, ngram_range=(1, 1), sublinear_tf=True)
    X_sub = tfidf_sub.fit_transform(subgroup_docs)         # sparse

    # ── Block 3: group multi-hot ─────────────────────────────────────────────
    # Build a binary matrix: rows = recipes, cols = ALL_GROUPS
    group_matrix = np.zeros((len(recipes), len(ALL_GROUPS)), dtype=np.float32)
    for i, recipe in enumerate(recipes):
        present = set(recipe_group_flags(recipe))
        for j, grp in enumerate(ALL_GROUPS):
            if grp in present:
                group_matrix[i, j] = 1.0
    X_group = sp.csr_matrix(group_matrix)

    # ── Block 4: cooking method one-hot ──────────────────────────────────────
    ohe = OneHotEncoder(
        categories=[COOKING_METHODS + ["unknown"]],
        sparse_output=True,
        handle_unknown="ignore",
    )
    X_method = ohe.fit_transform(methods)

    # ── L2-normalise each block independently, then weight and combine ────────
    def safe_norm(X):
        return normalize(X, norm="l2")

    X_combined = sp.hstack([
        safe_norm(X_canon)  * W_CANONICAL,
        safe_norm(X_sub)    * W_SUBGROUP,
        safe_norm(X_group)  * W_GROUP,
        safe_norm(X_method) * W_METHOD,
    ])

    # Final L2 normalise rows for cosine similarity
    X_norm = normalize(X_combined, norm="l2")
    return X_norm, tfidf_canon, tfidf_sub, ohe


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
    Derive a readable cluster label using the taxonomy hierarchy.

    Strategy:
      1. Aggregate canonical counts across all recipes in the cluster.
      2. Check CLUSTER_THEME_MAP for a ≥2-keyword match.
      3. If no match, fall back to the dominant group name + top 2 canonicals.
    """
    from collections import Counter

    canonical_counts: Counter = Counter()
    group_counts: Counter = Counter()

    for r in members:
        lines = recipe_to_ingredient_lines(r)
        canonical_counts.update(tax_featurize(lines, "canonical"))
        group_counts.update(tax_featurize(lines, "group"))

    # Exclude near-universal seasonings from label generation
    LABEL_STOPWORDS = {"salt", "black pepper", "olive oil", "butter", "egg",
                       "flour", "water", "sugar", "stock"}

    top_canonicals = [
        k for k, _ in canonical_counts.most_common(10)
        if k not in LABEL_STOPWORDS
    ][:5]

    keyword_set = frozenset(top_canonicals[:3])
    for theme_keys, label in CLUSTER_THEME_MAP.items():
        if len(theme_keys & keyword_set) >= 2:
            return label

    # Fallback: dominant group + top 2 distinctive canonicals
    dominant_group = group_counts.most_common(1)[0][0].title() if group_counts else ""
    top2 = " · ".join(top_canonicals[:2]).title()
    if dominant_group and top2:
        return f"{dominant_group}: {top2}"
    if top2:
        return top2
    return f"Cluster {cluster_id + 1}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"Loading recipes from {INPUT_FILE} …")
    recipes = load_recipes(INPUT_FILE)
    n = len(recipes)
    print(f"  {n} dishes loaded.")

    # Adjust t-SNE perplexity to be < n
    perplexity = min(TSNE_PERPLEXITY, n - 1)

    print("Building feature matrix (canonical + subgroup + group + method) …")
    X, tfidf_canon, tfidf_sub, ohe = build_feature_matrix(recipes)

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
        # Compute dominant ingredient groups for the cluster
        from collections import Counter
        grp_counts: Counter = Counter()
        for r in members:
            grp_counts.update(tax_featurize(recipe_to_ingredient_lines(r), "group"))
        top_groups = [g for g, _ in grp_counts.most_common(3)]

        cluster_meta[cid] = {
            "id": cid,
            "label": infer_cluster_label(cid, members),
            "dominant_groups": top_groups,
            "dish_ids": [r["id"] for r in members],
            "size": len(members),
        }

    # ── Assemble per-dish output ──────────────────────────────────────────────
    dishes_out = []
    for i, recipe in enumerate(recipes):
        # Attach taxonomy group flags to each dish for frontend use
        group_flags = recipe_group_flags(recipe)
        dishes_out.append({
            "id": recipe["id"],
            "name": recipe["name"],
            "country": recipe["country"],
            "region": recipe["region"],
            "cooking_method": recipe.get("cooking_method", "unknown"),
            "ingredient_groups": group_flags,
            "cluster": int(labels[i]),
            "tsne_x": round(coords_2d[i][0], 5),
            "tsne_y": round(coords_2d[i][1], 5),
        })

    output = {
        "meta": {
            "n_dishes": n,
            "n_clusters": N_CLUSTERS,
            "algorithm": "KMeans",
            "features": (
                f"TF-IDF canonical ({W_CANONICAL}) + "
                f"TF-IDF subgroup ({W_SUBGROUP}) + "
                f"group multi-hot ({W_GROUP}) + "
                f"one-hot cooking method ({W_METHOD})"
            ),
            "layout": "t-SNE 2D (normalised to [-1,1])",
            "taxonomy": "ingredient_taxonomy.py",
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
        groups_str = ", ".join(meta["dominant_groups"])
        print(f"  [{cid}] {meta['label']} ({meta['size']} dishes)  [{groups_str}]")
        for name in names:
            print(f"       • {name}")

    print(f"\n── Top 10 Connections ───────────────────────────────────────────")
    for conn in connections[:10]:
        src = next(r["name"] for r in recipes if r["id"] == conn["source"])
        tgt = next(r["name"] for r in recipes if r["id"] == conn["target"])
        print(f"  {src}  ↔  {tgt}  (sim={conn['similarity']})")


if __name__ == "__main__":
    main()
