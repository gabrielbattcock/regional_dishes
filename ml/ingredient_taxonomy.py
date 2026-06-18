"""
ingredient_taxonomy.py
======================

Ingredient normalisation and a 3-level hierarchy, built for a recipe-clustering
exercise (corpus skews Italian / British / Scottish).

Two layers, kept deliberately separate:

1. ALIASES        regex  -> canonical    (collapses synonyms, cuts, spellings)
2. HIERARCHY      group  -> subgroup -> [canonical]   (the taxonomy)

From the hierarchy we derive CANONICAL_TO_NODE (canonical -> (subgroup, group)),
so a single recipe ingredient can be featurised at three resolutions:

    "guanciale"  ->  canonical "cured pork"  ->  subgroup "cured meat"  ->  group "meat"

That lets you cluster on fine tokens, or coarsen to "does this recipe lean
dairy / meat / vegetable?" without re-tagging anything.

Design choices worth knowing (single-parent taxonomy, so each canonical has
exactly ONE subgroup and ONE group):
  * butter is filed under DAIRY (it is a dairy product); non-dairy fats
    (lard, suet, dripping, oils) live under FAT & OIL. If you would rather
    cluster all cooking fats together, coarsen via FAT_LIKE below.
  * eggs are their own group (not biologically dairy).
  * potato sits under VEGETABLE (root & tuber). If you cluster by carbohydrate
    role, treat it as a starch via STARCH_LIKE below.
  * tomato is a culinary vegetable; tomato *paste/purée* is a separate
    canonical filed as a condiment (concentrated flavouring, not the veg).

Matching rule: first pattern that matches wins, so order matters. Curated
patterns are ordered longest-alternative-first; a small OVERRIDES block sits at
the very top to beat generic single words that appear later (e.g. "chicken
stock" must resolve to stock, not chicken). An auto-generated tail then matches
any remaining canonical by its own name, so every canonical is reachable from
text even without a hand-written synonym.

Apply normalisation ONCE per ingredient string. (Several canonical values such
as nothing here are self-matching, but treating it as one-shot is the safe
contract.)
"""

import re
from collections import Counter

# ---------------------------------------------------------------------------
# 1. ALIASES : regex -> canonical
#    Within every alternation, list the LONGEST / most specific form first.
# ---------------------------------------------------------------------------

INGREDIENT_ALIASES = {

    # === OVERRIDES =========================================================
    # Multi-word forms whose first word is a generic canonical used later.
    # These MUST be matched before the generic single-word patterns below.
    r"\b((?:chicken|beef|veal|lamb|pork|fish|vegetable|bone) ?(?:stock|broth)|stock cube|stock|broth)\b": "stock",
    r"\b((?:balsamic|red wine|white wine|sherry|cider|rice|malt) vinegar|vinegar)\b": "vinegar",
    r"\b(tomato (?:paste|pur[ée]e|concentrate)|double concentrate)\b": "tomato paste",
    r"\b(spring onions?|scallions?)\b": "spring onion",
    r"\b(butter beans?|lima beans?)\b": "butter bean",
    r"\b(chilli flakes|chili flakes|red pepper flakes|crushed chilli(?:es)?|dried chilli flakes)\b": "chilli flakes",
    r"\b(fennel seeds?)\b": "fennel seed",
    r"\b(coriander seeds?)\b": "coriander seed",

    # === MEAT ==============================================================
    r"\b(skirt(?: steak)?|beef chuck|chuck|beef brisket|brisket|beef shin|shin of beef|oxtail|beef short ribs?|short ribs?|silverside|sirloin|rump|beef mince|minced beef|ground beef|coarse-ground beef|braising steak|stewing beef|beef)\b": "beef",
    r"\b(veal shanks?|osso ?buco|rose veal|veal)\b": "veal",
    r"\b(lamb neck|neck of lamb|lamb shoulder|shoulder of lamb|lamb shanks?|lamb offal|lamb on the bone|lamb chops?|lamb mince|minced lamb|mutton|lamb)\b": "lamb",
    r"\b(pork shoulder|pork belly|pork loin|pork mince|minced pork|ground pork|coarse-ground pork|pork back fat|pork sausagemeat|sausage ?meat|pork)\b": "pork",
    r"\b(chicken breasts?|chicken thighs?|chicken wings?|whole chicken|chicken)\b": "chicken",
    r"\b(turkeys?)\b": "turkey",
    r"\b(ducks?|duck breast|duck legs?)\b": "duck",
    r"\b(goose|goose fat)\b": "goose",
    r"\b(venison)\b": "venison",
    r"\b(rabbits?)\b": "rabbit",
    r"\b(hare)\b": "hare",
    r"\b(pheasants?)\b": "pheasant",
    r"\b(pigeons?|wood ?pigeon)\b": "pigeon",
    r"\b(guanciale|pancetta|bacon|lardo|speck|streaky bacon)\b": "cured pork",
    r"\b(parma ham|prosciutto crudo|prosciutto di parma|prosciutto|cured ham)\b": "prosciutto",
    r"\b(bresaola)\b": "bresaola",
    r"\b('nduja|nduja|salami|cacciatore)\b": "salami",
    r"\b(italian sausages?|salsiccia|luganega|sausages?)\b": "sausage",
    r"\b(chorizo)\b": "chorizo",
    r"\b(black pudding|blood sausage|blood pudding)\b": "black pudding",
    r"\b(chicken livers?|lambs? liver|calves? liver|liver)\b": "liver",
    r"\b(kidneys?)\b": "kidney",
    r"\b(tripe)\b": "tripe",
    r"\b(bone marrow|marrowbones?)\b": "bone marrow",
    r"\b(sweetbreads?)\b": "sweetbread",
    r"\b(lambs? pluck|offal|pluck)\b": "offal",

    # === SEAFOOD ===========================================================
    r"\b(cod|haddock|hake|pollock|coley|fish fillets?|white fish)\b": "white fish",
    r"\b(mackerel|sardines?|herring|pilchards?|oily fish)\b": "oily fish",
    r"\b(anchovy fillets?|anchovies|anchovy)\b": "anchovy",
    r"\b(salmon|smoked salmon)\b": "salmon",
    r"\b(tuna)\b": "tuna",
    r"\b(king prawns?|tiger prawns?|prawns?|shrimps?)\b": "prawn",
    r"\b(mussels?)\b": "mussel",
    r"\b(clams?|vongole)\b": "clam",
    r"\b(squid|calamari)\b": "squid",
    r"\b(octopus|polpo)\b": "octopus",
    r"\b(scallops?)\b": "scallop",
    r"\b(crab(?:meat)?)\b": "crab",
    r"\b(lobster)\b": "lobster",

    # === DAIRY =============================================================
    # cheeses
    r"\b(parmigiano[- ]?reggiano|parmigiano|grana padano|parmesan)\b": "parmesan",
    r"\b(pecorino romano|pecorino sardo|pecorino)\b": "pecorino",
    r"\b(fior di latte|buffalo mozzarella|bocconcini|burrata|mozzarella)\b": "mozzarella",
    r"\b(sheep['’]?s milk ricotta|ricotta)\b": "ricotta",
    r"\b(mascarpone cheese|mascarpone)\b": "mascarpone",
    r"\b(dolcelatte|gorgonzola)\b": "gorgonzola",
    r"\b(taleggio)\b": "taleggio",
    r"\b(fontina)\b": "fontina",
    r"\b(mature cheddar|cheddar)\b": "cheddar",
    r"\b(gruy[èe]re)\b": "gruyere",
    r"\b(stilton)\b": "stilton",
    r"\b(feta)\b": "feta",
    # milk & cream (specifics before bare "cream")
    r"\b(clotted cream)\b": "clotted cream",
    r"\b(cr[èe]me fra[îi]che|creme fraiche)\b": "creme fraiche",
    r"\b(buttermilk)\b": "buttermilk",
    r"\b(greek yo?ghurt|natural yo?ghurt|yo?ghurt|yo?gurt)\b": "yoghurt",
    r"\b(double cream|single cream|whipping cream|heavy cream|pouring cream|cream)\b": "cream",
    r"\b(whole milk|semi-skimmed milk|skimmed milk|full[- ]?fat milk|milk)\b": "milk",
    # butter (filed under dairy)
    r"\b(unsalted butter|salted butter|butter)\b": "butter",

    # === EGG ===============================================================
    r"\b(egg yolks?|egg whites?|eggs?)\b": "egg",

    # === FAT & OIL =========================================================
    r"\b(extra[- ]?virgin (?:ligurian )?olive oil|olive oil)\b": "olive oil",
    r"\b(sunflower oil|rapeseed oil|groundnut oil|vegetable oil)\b": "vegetable oil",
    r"\b(lard or shortening|lard or butter|shortening|lard)\b": "lard",
    r"\b(beef dripping|dripping)\b": "beef dripping",
    r"\b(suet)\b": "suet",
    r"\b(ghee)\b": "ghee",

    # === GRAIN & STARCH ====================================================
    r"\b(strong plain flour|plain flour|type[ .-]?00 ?flour|00 ?flour|strong bread flour|bread flour|all[- ]?purpose flour|flour)\b": "flour",
    r"\b(self[- ]?raising flour)\b": "self-raising flour",
    r"\b(wholemeal flour|wholewheat flour|wholegrain flour)\b": "wholemeal flour",
    r"\b(polenta|cornmeal)\b": "polenta",
    r"\b(semolina)\b": "semolina",
    r"\b(arborio rice|carnaroli rice|arborio|carnaroli|risotto rice)\b": "risotto rice",
    r"\b(basmati rice|long[- ]?grain rice|jasmine rice|rice)\b": "rice",
    r"\b(tonnarelli|spaghetti|tagliatelle|pappardelle|fettuccine|trofie|trenette|rigatoni|penne|bucatini|linguine|lasagn[ea]|macaroni|orecchiette|pasta)\b": "pasta",
    r"\b(gnocchi)\b": "gnocchi",
    r"\b(couscous)\b": "couscous",
    r"\b(stale tuscan bread|stale bread|tuscan bread|day[- ]?old bread)\b": "stale bread",
    r"\b(bread ?crumbs|breadcrumbs|panko)\b": "breadcrumbs",
    r"\b(ciabatta|focaccia|sourdough|crusty bread|bread)\b": "bread",
    r"\b(pinhead oatmeal|porridge oats|rolled oats|oatmeal|oats)\b": "oats",
    r"\b(pearl barley|barley)\b": "barley",
    r"\b(savoiardi|ladyfinger biscuits|lady ?fingers|sponge fingers|sponge biscuits)\b": "sponge biscuits",

    # === VEGETABLE =========================================================
    # soffritto & allium  (spring onion handled in OVERRIDES)
    r"\b(red onions?|white onions?|brown onions?|onions?)\b": "onion",
    r"\b(leeks?)\b": "leek",
    r"\b(garlic cloves?|garlic)\b": "garlic",
    r"\b(shallots?|echalion)\b": "shallot",
    r"\b(celery stalks?|celery sticks?|celery)\b": "celery",
    r"\b(carrots?)\b": "carrot",
    r"\b(fennel bulbs?|fennel)\b": "fennel",
    # root & tuber
    r"\b(floury potatoes|maris piper potatoes|new potatoes|waxy potatoes|potatoes?|potato)\b": "potato",
    r"\b(swede|rutabaga|neeps)\b": "swede",
    r"\b(turnips?)\b": "turnip",
    r"\b(parsnips?)\b": "parsnip",
    r"\b(beetroots?|beets?)\b": "beetroot",
    r"\b(celeriac)\b": "celeriac",
    # brassica & leafy green
    r"\b(cavolo nero|black kale|curly kale|kale)\b": "kale",
    r"\b(savoy cabbage|white cabbage|red cabbage|cabbage)\b": "cabbage",
    r"\b(cauliflower)\b": "cauliflower",
    r"\b(broccoli|tenderstem)\b": "broccoli",
    r"\b(brussels sprouts?|sprouts?)\b": "brussels sprout",
    r"\b(baby spinach|spinach)\b": "spinach",
    r"\b(swiss chard|rainbow chard|chard)\b": "chard",
    # squash & gourd
    r"\b(pumpkin)\b": "pumpkin",
    r"\b(butternut squash|squash)\b": "butternut squash",
    r"\b(courgettes?|zucchini)\b": "courgette",
    r"\b(aubergines?|eggplant)\b": "aubergine",
    # fruiting vegetable  (tomato paste handled in OVERRIDES)
    r"\b(san marzano tomatoes|tinned tomatoes|canned tomatoes|chopped tomatoes|cherry tomatoes|plum tomatoes|passata|tomatoes?|tomato)\b": "tomato",
    r"\b(bell peppers?|sweet peppers?|red peppers?|green peppers?|yellow peppers?|romano peppers?|capsicums?)\b": "sweet pepper",
    r"\b(red chilli(?:es)?|green chilli(?:es)?|chillies|chilli|chili|chile)\b": "chilli",
    # mushroom (chestnut mushroom must beat chestnut the nut -> veg precedes nuts)
    r"\b(chestnut mushrooms?|button mushrooms?|field mushrooms?|mushrooms?)\b": "mushroom",
    r"\b(dried porcini|porcini|ceps?)\b": "porcini",
    # pea & pod
    r"\b(frozen peas|garden peas|petits pois|peas?)\b": "pea",
    r"\b(broad beans?|fava beans?)\b": "broad bean",
    r"\b(green beans?|french beans?|runner beans?)\b": "green bean",

    # === LEGUME ============================================================
    r"\b(cannellini beans?|cannellini)\b": "cannellini bean",
    r"\b(borlotti beans?|borlotti|cranberry beans?)\b": "borlotti bean",
    r"\b(chickpeas?|garbanzos?)\b": "chickpea",
    r"\b(puy lentils|red lentils|green lentils|lentils?)\b": "lentil",
    r"\b(haricot beans?|navy beans?)\b": "haricot bean",

    # === FRUIT =============================================================
    r"\b(fresh raspberries|raspberries?|raspberry)\b": "raspberry",
    r"\b(fresh strawberries|strawberries?|strawberry)\b": "strawberry",
    r"\b(blackberries?|blackberry)\b": "blackberry",
    r"\b(blueberries?|blueberry)\b": "blueberry",
    r"\b(redcurrants?|blackcurrants?|currants?)\b": "currant",
    r"\b(lemon zest|lemon juice|lemons?)\b": "lemon",
    r"\b(orange zest|orange juice|oranges?)\b": "orange",
    r"\b(limes?)\b": "lime",
    r"\b(bramley apples?|apples?)\b": "apple",
    r"\b(pears?)\b": "pear",
    r"\b(peaches?)\b": "peach",
    r"\b(plums?)\b": "plum",
    r"\b(cherries?|cherry)\b": "cherry",
    r"\b(apricots?)\b": "apricot",
    r"\b(figs?)\b": "fig",
    r"\b(grapes?)\b": "grape",
    r"\b(raisins?)\b": "raisin",
    r"\b(sultanas?)\b": "sultana",
    r"\b(prunes?)\b": "prune",
    r"\b(dates?|medjool dates?)\b": "date",
    r"\b(candied orange peel|candied peel|mixed peel|candied fruit)\b": "candied peel",

    # === NUT & SEED ========================================================
    r"\b(ground almonds|flaked almonds|blanched almonds|almond extract|almonds?|almond)\b": "almond",
    r"\b(pine nuts?|pinoli)\b": "pine nut",
    r"\b(walnuts?)\b": "walnut",
    r"\b(hazelnuts?)\b": "hazelnut",
    r"\b(pistachios?)\b": "pistachio",
    r"\b(chestnuts?|marrons?)\b": "chestnut",
    r"\b(sesame seeds?|sesame)\b": "sesame",
    r"\b(poppy seeds?)\b": "poppy seed",
    r"\b(sunflower seeds?)\b": "sunflower seed",
    r"\b(pumpkin seeds?)\b": "pumpkin seed",

    # === HERB ==============================================================
    r"\b(fresh basil leaves?|basil)\b": "basil",
    r"\b(flat[- ]?leaf parsley|fresh parsley|parsley)\b": "parsley",
    r"\b(rosemary)\b": "rosemary",
    r"\b(thyme)\b": "thyme",
    r"\b(sage)\b": "sage",
    r"\b(dried oregano|oregano|marjoram)\b": "oregano",
    r"\b(mint leaves?|mint)\b": "mint",
    r"\b(bay leaves?|bay leaf)\b": "bay leaf",
    r"\b(chives?)\b": "chive",
    r"\b(dill)\b": "dill",
    r"\b(tarragon)\b": "tarragon",
    r"\b(coriander leaves?|cilantro|fresh coriander|coriander)\b": "coriander",

    # === SPICE & SEASONING =================================================
    # spice (fennel/coriander seed handled in OVERRIDES)
    r"\b(grated nutmeg|nutmeg)\b": "nutmeg",
    r"\b(cinnamon sticks?|ground cinnamon|cinnamon)\b": "cinnamon",
    r"\b(whole cloves|ground cloves|cloves?)\b": "clove",
    r"\b(saffron threads?|saffron)\b": "saffron",
    r"\b(smoked paprika|sweet paprika|paprika)\b": "paprika",
    r"\b(ground cumin|cumin)\b": "cumin",
    r"\b(ground ginger|fresh ginger|root ginger|ginger)\b": "ginger",
    r"\b(vanilla extract|vanilla pods?|vanilla bean|vanilla)\b": "vanilla",
    r"\b(juniper berries|juniper)\b": "juniper",
    r"\b(allspice|pimento)\b": "allspice",
    # salt & pepper  (sweet pepper above requires a qualifier, so bare "pepper"
    # falls through to black pepper)
    r"\b(coarsely ground black pepper|ground black pepper|black peppercorns?|black pepper|peppercorns?|pepper)\b": "black pepper",
    r"\b(sea salt|flaky salt|table salt|rock salt|salt)\b": "salt",
    # condiment  (vinegar/tomato paste handled in OVERRIDES)
    r"\b(english mustard|dijon mustard|wholegrain mustard|mustard powder|mustard)\b": "mustard",
    r"\b(worcestershire sauce|worcestershire)\b": "worcestershire",
    r"\b(capers?)\b": "caper",
    r"\b(black olives?|green olives?|kalamata olives?|olives?)\b": "olive",

    # === SWEETENER & CONFECTIONERY =========================================
    r"\b(caster sugar|icing sugar|granulated sugar|cane sugar|sugar)\b": "sugar",
    r"\b(demerara sugar|muscovado sugar|brown sugar)\b": "brown sugar",
    r"\b(heather honey|runny honey|honey)\b": "honey",
    r"\b(golden syrup)\b": "golden syrup",
    r"\b(black treacle|molasses|treacle)\b": "treacle",
    r"\b(maple syrup)\b": "maple syrup",
    r"\b(dark chocolate chips|dark chocolate|milk chocolate|white chocolate|chocolate)\b": "chocolate",
    r"\b(cocoa powder|cacao|cocoa)\b": "cocoa",
    r"\b(raspberry jam|strawberry jam|jam)\b": "jam",
    r"\b(marmalade)\b": "marmalade",

    # === ALCOHOL ===========================================================
    r"\b(marsala wine|marsala)\b": "marsala",
    r"\b(vermouth)\b": "vermouth",
    r"\b(sherry)\b": "sherry",
    r"\b(port)\b": "port",
    r"\b(dry white wine|white wine|red wine|wine)\b": "wine",
    r"\b(scotch whisky|whisky|whiskey)\b": "whisky",
    r"\b(cognac|brandy)\b": "brandy",
    r"\b(rum)\b": "rum",
    r"\b(dark ale|stout|ale|lager|beer)\b": "beer",

    # === LIQUID & BASE  (stock handled in OVERRIDES) =======================
    r"\b(strong espresso|espresso|coffee)\b": "coffee",
    r"\b(tea)\b": "tea",

    # === LEAVENING =========================================================
    r"\b(fast[- ]?action yeast|dried yeast|fresh yeast|yeast)\b": "yeast",
    r"\b(baking powder)\b": "baking powder",
    r"\b(bicarbonate of soda|baking soda|bicarb)\b": "bicarbonate of soda",

    # === OTHER =============================================================
    r"\b(sheep['’]?s stomach|natural hog casings|hog casings|artificial casing|casings?)\b": "casing",
    r"\b(leaf gelatine|gelatine|gelatin)\b": "gelatine",
}

# ---------------------------------------------------------------------------
# 2. HIERARCHY : group -> subgroup -> [canonical]   (single source of truth)
# ---------------------------------------------------------------------------

HIERARCHY = {
    "meat": {
        "beef":        ["beef"],
        "veal":        ["veal"],
        "lamb":        ["lamb"],
        "pork":        ["pork"],
        "poultry":     ["chicken", "turkey", "duck", "goose"],
        "game":        ["venison", "rabbit", "hare", "pheasant", "pigeon"],
        "cured meat":  ["cured pork", "prosciutto", "bresaola", "salami"],
        "sausage":     ["sausage", "chorizo", "black pudding"],
        "offal":       ["liver", "kidney", "tripe", "bone marrow", "sweetbread", "offal"],
    },
    "seafood": {
        "white fish":  ["white fish"],
        "oily fish":   ["oily fish", "anchovy", "salmon", "tuna"],
        "shellfish":   ["prawn", "mussel", "clam", "squid", "octopus", "scallop", "crab", "lobster"],
    },
    "dairy": {
        "cheese":      ["parmesan", "pecorino", "mozzarella", "ricotta", "mascarpone",
                        "gorgonzola", "taleggio", "fontina", "cheddar", "gruyere", "stilton", "feta"],
        "milk & cream":["milk", "cream", "buttermilk", "yoghurt", "creme fraiche", "clotted cream"],
        "butter":      ["butter"],
    },
    "egg": {
        "egg":         ["egg"],
    },
    "fat & oil": {
        "oil":         ["olive oil", "vegetable oil"],
        "rendered fat":["lard", "suet", "beef dripping", "ghee"],
    },
    "grain & starch": {
        "flour":              ["flour", "self-raising flour", "wholemeal flour"],
        "polenta & semolina": ["polenta", "semolina"],
        "rice":               ["risotto rice", "rice"],
        "pasta":              ["pasta", "gnocchi", "couscous"],
        "bread":              ["bread", "stale bread", "breadcrumbs"],
        "oats & barley":      ["oats", "barley"],
        "biscuit & sponge":   ["sponge biscuits"],
    },
    "vegetable": {
        "allium & aromatic":   ["onion", "spring onion", "leek", "garlic", "shallot",
                                "celery", "carrot", "fennel"],
        "root & tuber":        ["potato", "swede", "turnip", "parsnip", "beetroot", "celeriac"],
        "brassica & leafy":    ["kale", "cabbage", "cauliflower", "broccoli",
                                "brussels sprout", "spinach", "chard"],
        "squash & gourd":      ["pumpkin", "butternut squash", "courgette", "aubergine"],
        "fruiting vegetable":  ["tomato", "sweet pepper", "chilli"],
        "mushroom":            ["mushroom", "porcini"],
        "pea & pod":           ["pea", "broad bean", "green bean"],
    },
    "legume": {
        "bean & pulse": ["cannellini bean", "borlotti bean", "butter bean",
                         "haricot bean", "chickpea", "lentil"],
    },
    "fruit": {
        "berry":         ["raspberry", "strawberry", "blackberry", "blueberry", "currant"],
        "citrus":        ["lemon", "orange", "lime"],
        "orchard & stone":["apple", "pear", "peach", "plum", "cherry", "apricot", "fig", "grape"],
        "dried fruit":   ["raisin", "sultana", "prune", "date"],
        "candied fruit": ["candied peel"],
    },
    "nut & seed": {
        "nut":  ["almond", "pine nut", "walnut", "hazelnut", "pistachio", "chestnut"],
        "seed": ["sesame", "poppy seed", "sunflower seed", "pumpkin seed"],
    },
    "herb": {
        "fresh herb": ["basil", "parsley", "rosemary", "thyme", "sage", "oregano",
                       "mint", "bay leaf", "chive", "dill", "tarragon", "coriander"],
    },
    "spice & seasoning": {
        "spice":        ["nutmeg", "cinnamon", "clove", "saffron", "paprika", "cumin",
                         "ginger", "vanilla", "juniper", "allspice", "fennel seed",
                         "coriander seed", "chilli flakes"],
        "salt & pepper":["salt", "black pepper"],
        "condiment":    ["mustard", "worcestershire", "caper", "olive", "vinegar", "tomato paste"],
    },
    "sweetener & confectionery": {
        "sugar":            ["sugar", "brown sugar"],
        "syrup & honey":    ["honey", "golden syrup", "treacle", "maple syrup"],
        "chocolate & cocoa":["chocolate", "cocoa"],
        "preserve":         ["jam", "marmalade"],
    },
    "alcohol": {
        "wine & fortified": ["wine", "marsala", "vermouth", "sherry", "port"],
        "spirit":           ["whisky", "brandy", "rum"],
        "beer":             ["beer"],
    },
    "liquid & base": {
        "stock & broth": ["stock"],
        "coffee & tea":  ["coffee", "tea"],
    },
    "leavening": {
        "leavening": ["yeast", "baking powder", "bicarbonate of soda"],
    },
    "other": {
        "other": ["casing", "gelatine"],
    },
}

# Optional coarsening sets for cross-cutting clustering questions.
FAT_LIKE   = {"butter", "olive oil", "vegetable oil", "lard", "suet", "beef dripping", "ghee"}
STARCH_LIKE = {"flour", "self-raising flour", "wholemeal flour", "polenta", "semolina",
               "risotto rice", "rice", "pasta", "gnocchi", "couscous", "bread", "stale bread",
               "breadcrumbs", "oats", "barley", "potato"}

# ---------------------------------------------------------------------------
# Derived lookups + compiled patterns
# ---------------------------------------------------------------------------

def _build_canonical_to_node(hierarchy):
    lookup = {}
    for group, subgroups in hierarchy.items():
        for subgroup, canonicals in subgroups.items():
            for c in canonicals:
                if c in lookup:
                    raise ValueError(f"canonical {c!r} appears in two places")
                lookup[c] = (subgroup, group)
    return lookup

CANONICAL_TO_NODE = _build_canonical_to_node(HIERARCHY)


def _compile_patterns(aliases, lookup):
    """Curated patterns (in dict order) followed by an auto-generated tail that
    matches any remaining canonical by its own name (longest first)."""
    compiled = [(re.compile(rx, re.IGNORECASE), canon) for rx, canon in aliases.items()]
    have_alias = set(aliases.values())
    auto = sorted((c for c in lookup if c not in have_alias), key=len, reverse=True)
    for c in auto:
        token = rf"\b{re.escape(c)}s?\b" if " " not in c else rf"\b{re.escape(c)}\b"
        compiled.append((re.compile(token, re.IGNORECASE), c))
    return compiled

_PATTERNS = _compile_patterns(INGREDIENT_ALIASES, CANONICAL_TO_NODE)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def normalize(text):
    """Return the canonical ingredient for a string, or None if unrecognised."""
    for pattern, canon in _PATTERNS:
        if pattern.search(text):
            return canon
    return None


def classify(text):
    """Return {'raw','canonical','subgroup','group'} or None."""
    canon = normalize(text)
    if canon is None:
        return None
    subgroup, group = CANONICAL_TO_NODE[canon]
    return {"raw": text, "canonical": canon, "subgroup": subgroup, "group": group}


def featurize(ingredient_lines, level="canonical"):
    """Counter of a recipe's ingredients at the chosen resolution.

    level: 'canonical' | 'subgroup' | 'group'
    Unrecognised lines are skipped (inspect them to grow the aliases).
    """
    idx = {"canonical": None, "subgroup": 0, "group": 1}
    if level not in idx:
        raise ValueError("level must be canonical, subgroup or group")
    counts = Counter()
    for line in ingredient_lines:
        canon = normalize(line)
        if canon is None:
            continue
        counts[canon if level == "canonical" else CANONICAL_TO_NODE[canon][idx[level]]] += 1
    return counts


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # consistency: every alias target must exist in the hierarchy
    missing = sorted(set(INGREDIENT_ALIASES.values()) - set(CANONICAL_TO_NODE))
    assert not missing, f"alias canonicals missing from HIERARCHY: {missing}"

    n_groups = len(HIERARCHY)
    n_subs = sum(len(s) for s in HIERARCHY.values())
    n_canon = len(CANONICAL_TO_NODE)
    n_alias_rx = len(INGREDIENT_ALIASES)
    no_curated = sorted(c for c in CANONICAL_TO_NODE if c not in set(INGREDIENT_ALIASES.values()))
    print(f"groups={n_groups}  subgroups={n_subs}  canonicals={n_canon}  "
          f"curated_regexes={n_alias_rx}  auto_only={len(no_curated)}")

    # the precedence-sensitive cases from earlier review
    checks = {
        "egg yolks": "egg", "tomato paste": "tomato paste", "san marzano tomatoes": "tomato",
        "chicken stock": "stock", "red wine vinegar": "vinegar", "spring onions": "spring onion",
        "butter beans": "butter bean", "chestnut mushrooms": "mushroom", "black pepper": "black pepper",
        "bell pepper": "sweet pepper", "garlic cloves": "garlic", "chilli flakes": "chilli flakes",
        "fennel seeds": "fennel seed", "marsala wine": "marsala", "pinhead oatmeal": "oats",
        "guanciale": "cured pork", "cavolo nero": "kale", "savoiardi": "sponge biscuits",
        "double cream": "cream", "clotted cream": "clotted cream", "lardo": "cured pork",
    }
    bad = {k: normalize(k) for k, v in checks.items() if normalize(k) != v}
    assert not bad, f"precedence FAILED: {bad}"
    print("precedence checks: all", len(checks), "passed")

    # a tiny clustering-style demo across three resolutions
    carbonara = ["guanciale", "tonnarelli", "pecorino", "egg yolks", "black pepper"]
    ribollita = ["cannellini beans", "cavolo nero", "stale tuscan bread", "carrots",
                 "celery", "onion", "extra-virgin olive oil"]
    print("\ncarbonara @group :", dict(featurize(carbonara, "group")))
    print("ribollita @group :", dict(featurize(ribollita, "group")))
    print("ribollita @subgroup:", dict(featurize(ribollita, "subgroup")))