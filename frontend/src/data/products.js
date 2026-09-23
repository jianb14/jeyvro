// Mock catalog + async accessors — THE ONLY place the frontend touches data.
// Swap point: when the real API is ready, replace the accessor bodies with
// fetch("/api/...") calls returning the same shapes. Components never change.
// Contract: see .cline/skills/data-layer/SKILL.md

const DELAY = 450; // simulated network latency (ms)

const PRODUCTS = [
  { id: "p1", seed: 0, title: "Handwoven Bamboo Storage Basket - Large", price: 349, originalPrice: 499, discount: 30, rating: 5, sold: 1240, stock: 24, store: "Kalinga Crafts", verified: true, isNew: true, category: "Home & Living" },
  { id: "p2", seed: 1, title: "Organic Barako Coffee Beans 500g", price: 425, rating: 4, sold: 890, stock: 8, store: "Batangas Brew Co.", verified: true, category: "Food" },
  { id: "p3", seed: 2, title: "Minimal Ceramic Dinner Plates (Set of 4)", price: 899, originalPrice: 1200, discount: 25, rating: 5, sold: 432, stock: 0, store: "Mugna Pottery", verified: true, category: "Home & Living" },
  { id: "p4", seed: 3, title: "Abaca Tote Bag - Natural Dye", price: 550, rating: 4, sold: 2100, stock: 15, store: "Bicol Weavers", verified: true, isNew: true, category: "Fashion" },
  { id: "p5", seed: 4, title: "Air-dried Mango 200g Pack of 3", price: 380, originalPrice: 450, discount: 15, rating: 5, sold: 5600, stock: 42, store: "Cebu Delights", category: "Food" },
  { id: "p6", seed: 5, title: "Capiz Shell Wall Decor", price: 1250, rating: 4, sold: 156, stock: 5, store: "Kalinga Crafts", verified: true, category: "Home & Living" },
  { id: "p7", seed: 6, title: "Inabel Woven Throw Blanket", price: 1450, originalPrice: 1899, discount: 24, rating: 5, sold: 320, stock: 12, store: "Ilocos Weavers", verified: true, isNew: true, category: "Home & Living" },
  { id: "p8", seed: 7, title: "Tsokolate Tablea (Pack of 12)", price: 280, rating: 5, sold: 1870, stock: 30, store: "Davao Cacao House", category: "Food" },
];

function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function getProducts({ q = "", store = "" } = {}) {
  await wait(DELAY);
  let items = PRODUCTS;
  if (q) {
    const needle = q.toLowerCase();
    items = items.filter((p) => p.title.toLowerCase().includes(needle));
  }
  if (store) {
    items = items.filter((p) => p.store === store);
  }
  return items;
}

export async function getProductById(id) {
  await wait(DELAY);
  return PRODUCTS.find((p) => p.id === id) ?? null;
}

export function getAllStores() {
  return [...new Set(PRODUCTS.map((p) => p.store))];
}
