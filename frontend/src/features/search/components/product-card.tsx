"use client";

import Image from "next/image";
import { useState } from "react";
import { Heart, ExternalLink, LineChart, PackageCheck, Plus, Trophy } from "lucide-react";
import { PriceHistoryChart } from "@/features/search/components/price-history-chart";
import { formatCurrency, cn } from "@/lib/utils";
import { useAppStore } from "@/stores/use-app-store";
import type { Product, StoreId } from "@/types/api";

// ── Store display info ─────────────────────────────────────────────────────

const STORE_INFO: Record<string, { label: string; color: string; short: string }> = {
  lider:        { label: "Lider",        color: "#00913f", short: "L"  },
  jumbo:        { label: "Jumbo",        color: "#e5002b", short: "J"  },
  santa_isabel: { label: "Santa Isabel", color: "#e5002b", short: "SI" },
  acuenta:      { label: "Acuenta",      color: "#f6a800", short: "A"  },
  tottus:       { label: "Tottus",       color: "#e5002b", short: "T"  },
  unimarc:      { label: "Unimarc",      color: "#003da5", short: "U"  },
};

function StoreChip({ storeId }: { storeId: string }) {
  const info = STORE_INFO[storeId] ?? { label: storeId, color: "#666", short: "?" };
  return (
    <span
      className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold text-white"
      style={{ background: info.color }}
    >
      {info.label}
    </span>
  );
}

// ── Discount percentage ────────────────────────────────────────────────────

function DiscountBadge({ original, current }: { original: number; current: number }) {
  if (!original || original <= current) return null;
  const pct = Math.round(((original - current) / original) * 100);
  if (pct < 1) return null;
  return (
    <span className="inline-flex items-center rounded-full bg-[#00913f] px-2 py-0.5 text-[10px] font-bold text-white">
      ↓{pct}%
    </span>
  );
}

// ── Product card ───────────────────────────────────────────────────────────

export function ProductCard({
  product,
  index,
  isCheapest = false,
}: {
  product: Product;
  index: number;
  isCheapest?: boolean;
}) {
  const addToCart = useAppStore((s) => s.addToCart);
  const [showHistory, setShowHistory] = useState(false);
  const [saved, setSaved] = useState(false);
  const [added, setAdded] = useState(false);

  const productId = product.sku ?? product.id ?? `${product.source}-${product.name}`;
  const storeId: StoreId | null = product.source || null;
  const hasDiscount = !!(product.original_price && product.original_price > product.price);
  const isOffer = product.is_offer || hasDiscount;

  function handleAdd() {
    addToCart(product);
    setAdded(true);
    setTimeout(() => setAdded(false), 1200);
  }

  return (
    <div
      className={cn(
        "group relative flex flex-col overflow-hidden rounded-xl border bg-white transition-all duration-200",
        "hover:-translate-y-0.5 hover:shadow-lg",
        isCheapest
          ? "border-[#00913f]/40 ring-1 ring-[#00913f]/20"
          : "border-[#e8eaed]"
      )}
    >
      {/* ── Top badges ──────────────────────────────────────────── */}
      <div className="absolute left-2 top-2 z-10 flex flex-col gap-1">
        {isCheapest && (
          <span className="flex items-center gap-1 rounded-full bg-[#00913f] px-2 py-0.5 text-[10px] font-bold text-white shadow-sm">
            <Trophy className="h-2.5 w-2.5" />
            Mejor precio
          </span>
        )}
        {isOffer && !isCheapest && (
          <span className="rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-bold text-white shadow-sm">
            Oferta
          </span>
        )}
      </div>

      {/* Save button */}
      <button
        onClick={() => setSaved((v) => !v)}
        aria-label="Guardar producto"
        className="absolute right-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-white/80 shadow-sm backdrop-blur-sm transition-all hover:scale-110"
      >
        <Heart
          className={cn("h-3.5 w-3.5 transition-colors", saved ? "fill-red-500 text-red-500" : "text-gray-400")}
        />
      </button>

      {/* ── Product image ────────────────────────────────────────── */}
      <div className="relative h-44 w-full overflow-hidden bg-[#f8f9fa]">
        {product.image ? (
          <Image
            src={product.image}
            alt={product.name}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
            className="object-contain p-4 transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <PackageCheck className="h-12 w-12 text-[#e8eaed]" />
          </div>
        )}
      </div>

      {/* ── Product info ─────────────────────────────────────────── */}
      <div className="flex flex-1 flex-col p-3">
        {/* Brand */}
        {(product.brand || product.seller) && (
          <p className="truncate text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            {product.brand ?? product.seller}
          </p>
        )}

        {/* Name */}
        <p className="mt-0.5 line-clamp-2 text-sm font-medium leading-snug text-[#1a2332]">
          {product.name}
        </p>

        {/* Prices */}
        <div className="mt-2 flex items-end gap-2">
          <div>
            {product.original_price && product.original_price > product.price && (
              <p className="text-[11px] text-muted-foreground line-through">
                {formatCurrency(product.original_price)}
              </p>
            )}
            <p
              className={cn(
                "text-lg font-bold leading-none",
                isCheapest ? "text-[#00913f]" : "text-[#1a2332]"
              )}
            >
              {formatCurrency(product.price)}
            </p>
            {product.unit_price && (
              <p className="mt-0.5 text-[10px] text-muted-foreground">{product.unit_price}</p>
            )}
          </div>
          {hasDiscount && (
            <DiscountBadge original={product.original_price!} current={product.price} />
          )}
        </div>

        {/* ── Bottom row: store + actions ──────────────────────── */}
        <div className="mt-3 flex items-center justify-between border-t border-[#f0f1f3] pt-2">
          {/* Store chip */}
          <div className="flex items-center gap-1">
            {storeId && <StoreChip storeId={storeId} />}
            {!product.in_stock && (
              <span className="text-[10px] text-muted-foreground">Agotado</span>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-0.5">
            {storeId && productId && (
              <button
                onClick={() => setShowHistory((v) => !v)}
                aria-label="Historial de precio"
                className="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-[#f0f1f3] hover:text-[#1a2332]"
              >
                <LineChart className="h-3.5 w-3.5" />
              </button>
            )}
            {product.url && (
              <a
                href={product.url}
                target="_blank"
                rel="noreferrer"
                aria-label="Ver en tienda"
                className="flex h-7 w-7 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-[#f0f1f3] hover:text-[#1a2332]"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
            <button
              onClick={handleAdd}
              aria-label="Agregar al carro"
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-lg border text-xs font-bold transition-all duration-200",
                added
                  ? "border-[#00913f] bg-[#00913f] text-white"
                  : "border-[#00913f]/30 bg-[#00913f]/5 text-[#00913f] hover:bg-[#00913f] hover:text-white"
              )}
            >
              {added ? "✓" : <Plus className="h-3.5 w-3.5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Price history (expandable) */}
      {showHistory && storeId && productId && (
        <div className="border-t border-[#f0f1f3] px-3 pb-3 pt-2">
          <PriceHistoryChart product_id={productId} store={storeId} />
        </div>
      )}
    </div>
  );
}
