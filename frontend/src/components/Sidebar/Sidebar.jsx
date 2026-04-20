import RecipeCard from "../RecipeCard/RecipeCard.jsx";
import "./Sidebar.css";

function Sidebar({ recipe, onClose }) {
  return (
    <aside className={`sidebar ${recipe ? "sidebar--open" : ""}`}>
      {recipe ? (
        <RecipeCard recipe={recipe} onClose={onClose} />
      ) : (
        <div className="sidebar-placeholder">
          <span className="sidebar-placeholder__icon">🗺️</span>
          <p>Click a pin on the map to discover a regional dish.</p>
        </div>
      )}
    </aside>
  );
}

export default Sidebar;
