import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("framer-motion", () => ({
  motion: {
    div: ({ children, ...rest }: React.HTMLAttributes<HTMLDivElement>) => <div {...rest}>{children}</div>,
    span: ({ children, ...rest }: React.HTMLAttributes<HTMLSpanElement>) => <span {...rest}>{children}</span>,
  },
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useMotionValue: () => ({ get: () => 0 }),
  useTransform: () => ({ get: () => "CLP 0" }),
  animate: () => ({ stop: () => {} }),
}));

vi.mock("@/hooks/use-shopping-list", () => ({
  useShoppingListCompare: () => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
    data: null,
  }),
}));

import { ShoppingListWorkbench } from "./shopping-list-workbench";

describe("ShoppingListWorkbench", () => {
  it("renders empty state correctly", () => {
    render(<ShoppingListWorkbench />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("adds item on textarea input + button click", async () => {
    const user = userEvent.setup();
    render(<ShoppingListWorkbench />);
    const textarea = screen.getByRole("textbox");
    await user.type(textarea, "arroz 1kg");
    const btn = screen.getByRole("button", { name: /comparar/i });
    await user.click(btn);
  });
});
