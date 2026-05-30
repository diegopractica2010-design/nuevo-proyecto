import { vi } from "vitest";

export const apiClient = {
  searchProducts: vi.fn(),
  compareShoppingList: vi.fn(),
  getScraperHealth: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  getMe: vi.fn(),
  getPriceHistory: vi.fn(),
  getStores: vi.fn(),
  getBaskets: vi.fn(),
  getBasket: vi.fn(),
  createBasket: vi.fn(),
  addToBasket: vi.fn(),
  updateBasketItem: vi.fn(),
  logout: vi.fn(),
  deleteBasket: vi.fn(),
  deleteBasketItem: vi.fn(),
};

vi.mock("../../services/api-client", () => ({ apiClient }));
