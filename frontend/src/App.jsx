import { useState } from "react";
import MapView from "./components/Map/MapView.jsx";
import Sidebar from "./components/Sidebar/Sidebar.jsx";
import "./styles/global.css";

function App() {
  const [selectedRecipe, setSelectedRecipe] = useState(null);

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Regional Dishes</h1>
        <p>Explore traditional recipes from around the world</p>
      </header>

      <main className="app-main">
        <MapView onRecipeSelect={setSelectedRecipe} />
        <Sidebar recipe={selectedRecipe} onClose={() => setSelectedRecipe(null)} />
      </main>
    </div>
  );
}

export default App;
