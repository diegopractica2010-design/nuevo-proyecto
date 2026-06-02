import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Product } from "@/types/api";

const mockAddToCart = vi.fn();

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...rest }: React.HTMLAttributes<HTMLDivElement>) => <div {...rest}>{children}</div>,
    button: ({ children, ...rest }: React.ButtonHTMLAttributes<HTMLButtonElement>) => (
      <button {...rest}>{children}</button>
    ),
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock("next/image", () => ({
  default: ({ src, alt }: { src: string; alt: string }) => <img src={src} alt={alt} />,
}));

vi.mock("@/stores/use-app-store", () => ({
  useAppStore: (selector: (s: { addToCart: typeof mockAddToCart }) => unknown) =>
    selector({ addToCart: mockAddToCart }),
}));

vi.mock("@/features/search/components/price-history-chart", () => ({
  PriceHistoryChart: () => <div data-testid="chart" />,
}));

import { ProductCard } from "./product-card";

const mockProduct: Product = {
  id: "prod-1",
  sku: "sku-1",
  name: "Leche entera 1L",
  brand: "Soprole",
  price: 990,
  in_stock: true,
  badges: [],
  is_offer: false,
  currency: "CLP",
  source: "lider",
  category: "Lácteos",
};

describe("ProductCard", () => {
  it("renders product name and brand", () => {
    render(<ProductCard product={mockProduct} index={0} />);
    expect(screen.getByText("Leche entera 1L")).toBeInTheDocument();
    expect(screen.getByText("Soprole")).toBeInTheDocument();
  });

  it("shows 'Oferta' badge when is_offer=true", () => {
    render(<ProductCard product={{ ...mockProduct, is_offer: true }} index={0} />);
    expect(screen.getByText("Oferta")).toBeInTheDocument();
  });

  it("calls addToCart when add button is clicked", async () => {
    mockAddToCart.mockClear();
    const user = userEvent.setup();
    render(<ProductCard product={mockProduct} index={0} />);
    const btn = screen.getByRole("button", { name: /agregar/i });
    await user.click(btn);
    expect(mockAddToCart).toHaveBeenCalledWith(mockProduct);
  });
});
