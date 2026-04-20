import "./RecipeCard.css";

function RecipeCard({ recipe, onClose }) {
  const totalTime = recipe.prep_time_mins + recipe.cook_time_mins;

  return (
    <article className="recipe-card">
      <button className="recipe-card__close" onClick={onClose} aria-label="Close">
        ✕
      </button>

      <header className="recipe-card__header">
        <h2 className="recipe-card__title">{recipe.name}</h2>
        <span className="recipe-card__region">{recipe.region} · {recipe.country}</span>
        <p className="recipe-card__description">{recipe.short_description}</p>
      </header>

      <section className="recipe-card__meta">
        <div className="meta-item">
          <span className="meta-label">Prep</span>
          <span className="meta-value">{recipe.prep_time_mins} min</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Cook</span>
          <span className="meta-value">{recipe.cook_time_mins} min</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Total</span>
          <span className="meta-value">{totalTime} min</span>
        </div>
        <div className="meta-item">
          <span className="meta-label">Serves</span>
          <span className="meta-value">{recipe.serves}</span>
        </div>
      </section>

      <section className="recipe-card__section">
        <h3>History</h3>
        <p className="recipe-card__history">{recipe.history}</p>
      </section>

      <section className="recipe-card__section">
        <h3>Ingredients</h3>
        <ul className="ingredient-list">
          {recipe.ingredients.map((ing, i) => (
            <li key={i} className="ingredient-item">
              <span className="ingredient-amount">
                {ing.amount}{ing.unit ? ` ${ing.unit}` : ""}
              </span>{" "}
              {ing.item}
            </li>
          ))}
        </ul>
      </section>

      <section className="recipe-card__section">
        <h3>Method</h3>
        <ol className="step-list">
          {recipe.steps.map((s) => (
            <li key={s.step} className="step-item">
              {s.instruction}
            </li>
          ))}
        </ol>
      </section>

      {recipe.tags.length > 0 && (
        <footer className="recipe-card__tags">
          {recipe.tags.map((tag) => (
            <span key={tag} className="tag">
              #{tag}
            </span>
          ))}
        </footer>
      )}
    </article>
  );
}

export default RecipeCard;
