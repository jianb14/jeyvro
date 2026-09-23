import { Routes, Route } from "react-router-dom";
import { Home } from "./routes/Home";
import { DesignSystem } from "./routes/DesignSystem";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/design-system" element={<DesignSystem />} />
      <Route path="*" element={<Home />} />
    </Routes>
  );
}

export default App;

