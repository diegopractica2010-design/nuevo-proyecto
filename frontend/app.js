const STORAGE_KEYS = {
  favorites: "radar-precios-favorites-v2",
  history: "radar-precios-history-v2",
};

const QUICK_QUERIES = [
  "leche",
  "arroz",
  "cafe",
  "detergente",
  "papel higienico",
  "aceite",
];

const DEFAULT_FILTERS = {
  sort: "price-asc",
  minPrice: "",
  maxPrice: "",
  onlyOffers: false,
  onlyInStock: false,
  onlyFavorites: false,
  brand: "",
  category: "",
};

const DEFAULT_SOURCE_URL = "https://super.lider.cl";

const state = {
  query: "",
  appliedQuery: "",
  results: [],
  facets: {
    brands: [],
    categories: [],
    price_range: { min: null, max: null },
  },
  stats: {
    min_price: null,
    max_price: null,
    average_price: null,
    offer_count: 0,
    in_stock_count: 0,
  },
  suggestions: [],
  fetchedAt: "",
  sourceUrl: DEFAULT_SOURCE_URL,
  strategy: "",
  cached: false,
  loading: false,
  error: "",
  warning: "",
  filters: { ...DEFAULT_FILTERS },
  favorites: loadJSON(STORAGE_KEYS.favorites, {}),
  history: loadJSON(STORAGE_KEYS.history, []),
  requestToken: 0,
  abortController: null,
  store: "lider",  // Nueva propiedad para la tienda seleccionada
  currentBasket: null,
  baskets: [],
};

const currencyFormatter = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
  maximumFractionDigits: 0,
});

const elements = {
  form: document.getElementById("search-form"),
  input: document.getElementById("search-input"),
  storeSelect: document.getElementById("store-select"),
  quickTags: document.getElementById("quick-tags"),
  heroResultsCount: document.getElementById("hero-results-count"),
  heroCheapest: document.getElementById("hero-cheapest"),
  favoritesCount: document.getElementById("favorites-count"),
  historyCount: document.getElementById("history-count"),
  sortSelect: document.getElementById("sort-select"),
  minPriceInput: document.getElementById("min-price-input"),
  maxPriceInput: document.getElementById("max-price-input"),
  offersToggle: document.getElementById("offers-toggle"),
  stockToggle: document.getElementById("stock-toggle"),
  favoritesToggle: document.getElementById("favorites-toggle"),
  clearFiltersButton: document.getElementById("clear-filters-button"),
  clearFavoritesButton: document.getElementById("clear-favorites-button"),
  clearHistoryButton: document.getElementById("clear-history-button"),
  brandFilters: document.getElementById("brand-filters"),
  categoryFilters: document.getElementById("category-filters"),
  favoritesList: document.getElementById("favorites-list"),
  historyList: document.getElementById("history-list"),
  resultsTitle: document.getElementById("results-title"),
  resultsSubtitle: document.getElementById("results-subtitle"),
  statusPill: document.getElementById("status-pill"),
  sourcePill: document.getElementById("source-pill"),
  feedback: document.getElementById("feedback"),
  suggestions: document.getElementById("suggestions"),
  summaryCards: document.getElementById("summary-cards"),
  visibleCount: document.getElementById("visible-count"),
  activeFiltersLabel: document.getElementById("active-filters-label"),
  sourceLink: document.getElementById("source-link"),
  resultsGrid: document.getElementById("results-grid"),
  // Elementos de canastas
  basketsLink: document.getElementById("baskets-link"),
  basketsSection: document.getElementById("baskets-section"),
  newBasketBtn: document.getElementById("new-basket-btn"),
  basketsList: document.getElementById("baskets-list"),
  basketDetail: document.getElementById("basket-detail"),
  basketTitle: document.getElementById("basket-title"),
  backToBaskets: document.getElementById("back-to-baskets"),
  basketItems: document.getElementById("basket-items"),
  basketTotal: document.getElementById("basket-total"),
};

initialize();

function initialize() {
  renderQuickTags();
  bindEvents();
  syncFilterInputs();
  renderAll();

  const params = new URLSearchParams(window.location.search);
  const initialQuery = params.get("q") || (state.history[0] && state.history[0].query) || "leche";
  elements.input.value = initialQuery;
  performSearch(initialQuery);
}

function bindEvents() {
  elements.form.addEventListener("submit", (event) => {
    event.preventDefault();
    performSearch(elements.input.value);
  });

  elements.storeSelect.addEventListener("change", (event) => {
    state.store = event.target.value;
    // Si hay una búsqueda activa, volver a buscar en la nueva tienda
    if (state.query) {
      performSearch(state.query);
    }
  });

  // Event listeners para canastas
  elements.basketsLink.addEventListener("click", (event) => {
    event.preventDefault();
    showBaskets();
  });

  elements.newBasketBtn.addEventListener("click", () => {
    const name = prompt("Nombre de la canasta:");
    if (name) {
      createBasket(name);
    }
  });

  elements.backToBaskets.addEventListener("click", () => {
    showBaskets();
  });

  elements.sortSelect.addEventListener("change", (event) => {
    state.filters.sort = event.target.value;
    renderResults();
    renderSummary();
  });

  elements.minPriceInput.addEventListener("input", (event) => {
    state.filters.minPrice = event.target.value;
    renderResults();
    renderSummary();
  });

  elements.maxPriceInput.addEventListener("input", (event) => {
    state.filters.maxPrice = event.target.value;
    renderResults();
    renderSummary();
  });

  elements.offersToggle.addEventListener("change", (event) => {
    state.filters.onlyOffers = event.target.checked;
    renderResults();
    renderSummary();
  });

  elements.stockToggle.addEventListener("change", (event) => {
    state.filters.onlyInStock = event.target.checked;
    renderResults();
    renderSummary();
  });

  elements.favoritesToggle.addEventListener("change", (event) => {
    state.filters.onlyFavorites = event.target.checked;
    renderResults();
    renderSummary();
  });

  elements.clearFiltersButton.addEventListener("click", () => {
    state.filters = { ...DEFAULT_FILTERS };
    syncFilterInputs();
    renderFilters();
    renderResults();
    renderSummary();
  });

  elements.clearFavoritesButton.addEventListener("click", () => {
    state.favorites = {};
    persistFavorites();
    renderSidePanels();
    renderResults();
  });

  elements.clearHistoryButton.addEventListener("click", () => {
    state.history = [];
    localStorage.removeItem(STORAGE_KEYS.history);
    renderSidePanels();
  });

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-action]");
    if (!trigger) {
      return;
    }

    const action = trigger.dataset.action;

    if (action === "quick-query" || action === "history-query" || action === "suggestion-query") {
      const query = trigger.dataset.query || "";
      elements.input.value = query;
      performSearch(query);
      return;
    }

    if (action === "toggle-favorite") {
      const key = trigger.dataset.key;
      if (key) {
        toggleFavorite(key);
      }
      return;
    }

    if (action === "remove-favorite") {
      const key = trigger.dataset.key;
      if (key) {
        delete state.favorites[key];
        persistFavorites();
        renderSidePanels();
        renderResults();
      }
      return;
    }

    if (action === "toggle-brand") {
      const brand = trigger.dataset.brand || "";
      state.filters.brand = state.filters.brand === brand ? "" : brand;
      renderFilters();
      renderResults();
      renderSummary();
      return;
    }

    if (action === "toggle-category") {
      const category = trigger.dataset.category || "";
      state.filters.category = state.filters.category === category ? "" : category;
      renderFilters();
      renderResults();
      renderSummary();
      return;
    }

    if (action === "reset-filters") {
      state.filters = { ...DEFAULT_FILTERS };
      syncFilterInputs();
      renderFilters();
      renderResults();
      renderSummary();
    }
  });
}

async function performSearch(query) {
  const trimmedQuery = (query || "").trim();
  if (!trimmedQuery) {
    state.error = "Escribe un producto para iniciar la comparacion.";
    state.warning = "";
    state.results = [];
    state.fetchedAt = "";
    state.sourceUrl = DEFAULT_SOURCE_URL;
    state.strategy = "";
    state.cached = false;
    renderFeedback();
    renderResults();
    return;
  }

  if (state.abortController) {
    state.abortController.abort();
  }

  const controller = new AbortController();
  const requestToken = state.requestToken + 1;

  state.abortController = controller;
  state.requestToken = requestToken;
  state.query = trimmedQuery;
  state.appliedQuery = trimmedQuery;
  state.loading = true;
  state.error = "";
  state.warning = "";
  state.suggestions = [];
  updateQueryString(trimmedQuery);
  renderAll();

  try {
    const response = await fetch(`/search?query=${encodeURIComponent(trimmedQuery)}&limit=36&store=${state.store}`, {
      signal: controller.signal,
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "No se pudo completar la busqueda.");
    }

    if (state.requestToken !== requestToken) {
      return;
    }

    state.results = Array.isArray(data.results) ? data.results : [];
    state.facets = data.facets || {
      brands: [],
      categories: [],
      price_range: { min: null, max: null },
    };
    state.stats = data.stats || state.stats;
    state.suggestions = Array.isArray(data.suggestions) ? data.suggestions : [];
    state.appliedQuery = data.applied_query || trimmedQuery;
    state.warning = data.warning || "";
    state.fetchedAt = data.fetched_at || "";
    state.sourceUrl = data.source_url || DEFAULT_SOURCE_URL;
    state.strategy = data.strategy || "";
    state.cached = Boolean(data.cached);
    state.error = "";

    synchronizeFavoritesWithResults();
    pushHistory(trimmedQuery, state.results.length);
  } catch (error) {
    if (error.name === "AbortError") {
      return;
    }

    state.results = [];
    state.facets = {
      brands: [],
      categories: [],
      price_range: { min: null, max: null },
    };
    state.stats = {
      min_price: null,
      max_price: null,
      average_price: null,
      offer_count: 0,
      in_stock_count: 0,
    };
    state.suggestions = [];
    state.fetchedAt = "";
    state.sourceUrl = DEFAULT_SOURCE_URL;
    state.strategy = "";
    state.cached = false;
    state.error = error.message || "No se pudo conectar con el backend.";
  } finally {
    if (state.requestToken === requestToken) {
      state.loading = false;
      state.abortController = null;
      renderAll();
    }
  }
}

function renderAll() {
  renderHeroStats();
  renderSidePanels();
  renderFilters();
  renderFeedback();
  renderSuggestions();
  renderSummary();
  renderResults();
}

function renderQuickTags() {
  elements.quickTags.innerHTML = QUICK_QUERIES.map(
    (query) =>
      `<button class="chip" type="button" data-action="quick-query" data-query="${escapeAttribute(query)}">${escapeHtml(query)}</button>`
  ).join("");
}

function renderHeroStats() {
  elements.heroResultsCount.textContent = `${state.results.length}`;
  elements.heroCheapest.textContent =
    state.stats.min_price != null ? formatPrice(state.stats.min_price) : "-";
  elements.favoritesCount.textContent = `${Object.keys(state.favorites).length}`;
  elements.historyCount.textContent = `${state.history.length}`;
}

function renderFeedback() {
  const cards = [];

  if (state.loading) {
    cards.push(`
      <article class="feedback-card">
        <strong>🔍 Buscando precios en Lider.cl</strong>
        <span>Extrayendo datos en tiempo real, aplicando filtros y calculando estadísticas...</span>
      </article>
    `);
  }

  if (!state.loading && state.query && state.appliedQuery && state.appliedQuery !== state.query) {
    cards.push(`
      <article class="feedback-card feedback-card--info">
        <strong>Consulta rescatada</strong>
        <span>La busqueda directa no devolvio coincidencias claras. Mostramos resultados para "${escapeHtml(state.appliedQuery)}".</span>
      </article>
    `);
  }

  if (state.warning) {
    cards.push(`
      <article class="feedback-card feedback-card--warning">
        <strong>Atencion</strong>
        <span>${escapeHtml(state.warning)}</span>
      </article>
    `);
  }

  if (state.error) {
    cards.push(`
      <article class="feedback-card feedback-card--error">
        <strong>No pudimos mostrar resultados</strong>
        <span>${escapeHtml(state.error)}</span>
      </article>
    `);
  }

  elements.feedback.innerHTML = cards.join("");
}

function renderSuggestions() {
  const items = state.suggestions.filter(
    (item) =>
      item &&
      item.toLowerCase() !== state.query.toLowerCase() &&
      item.toLowerCase() !== state.appliedQuery.toLowerCase()
  );

  if (!items.length || state.loading) {
    elements.suggestions.innerHTML = "";
    return;
  }

  elements.suggestions.innerHTML = `
    <div class="suggestions-bar__content">
      <span class="suggestions-bar__label">Prueba tambien</span>
      <div class="chip-row">
        ${items
          .map(
            (item) =>
              `<button class="chip chip--ghost" type="button" data-action="suggestion-query" data-query="${escapeAttribute(item)}">${escapeHtml(item)}</button>`
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderSummary() {
  const visibleResults = getVisibleResults();
  const visibleStats = getComputedStats(visibleResults);

  const summaryCards = [
    {
      label: "Visibles",
      value: `${visibleResults.length}`,
      meta: `${state.results.length} cargados desde la fuente`,
    },
    {
      label: "Mejor precio",
      value: visibleStats.minPrice != null ? formatPrice(visibleStats.minPrice) : "Sin datos",
      meta: state.query ? `Consulta activa: ${state.query}` : "Sin busqueda activa",
    },
    {
      label: "Precio promedio",
      value:
        visibleStats.averagePrice != null ? formatPrice(visibleStats.averagePrice) : "Sin datos",
      meta: "Calculado sobre los productos visibles",
    },
    {
      label: "Ofertas / stock",
      value: `${visibleStats.offerCount} / ${visibleStats.inStockCount}`,
      meta: "Ofertas visibles y productos con stock",
    },
  ];

  elements.summaryCards.innerHTML = summaryCards
    .map(
      (item) => `
        <article class="summary-card">
          <span class="summary-card__label">${escapeHtml(item.label)}</span>
          <strong>${escapeHtml(item.value)}</strong>
          <p class="muted-text">${escapeHtml(item.meta)}</p>
        </article>
      `
    )
    .join("");

  elements.resultsTitle.textContent = state.query
    ? `Resultados para "${state.query}"`
    : "Explorando precios reales";

  const subtitleParts = [];
  if (state.results.length) {
    subtitleParts.push(`${state.results.length} productos cargados`);
  }
  if (state.appliedQuery && state.appliedQuery !== state.query) {
    subtitleParts.push(`coincidencias para ${state.appliedQuery}`);
  }
  if (state.fetchedAt) {
    subtitleParts.push(`actualizado ${formatDateTime(state.fetchedAt)}`);
  }
  if (state.cached) {
    subtitleParts.push("respuesta servida desde cache");
  }
  if (!subtitleParts.length) {
    subtitleParts.push("Busca un producto y compara resultados reales en tarjetas.");
  }
  elements.resultsSubtitle.textContent = subtitleParts.join(" · ");

  if (state.loading) {
    elements.statusPill.textContent = "Buscando...";
  } else if (state.error) {
    elements.statusPill.textContent = "Error";
  } else if (state.results.length) {
    elements.statusPill.textContent = "Precios listos";
  } else {
    elements.statusPill.textContent = "Sin coincidencias";
  }

  elements.sourcePill.textContent = state.cached ? `${state.store.charAt(0).toUpperCase() + state.store.slice(1)} · cache` : `${state.store.charAt(0).toUpperCase() + state.store.slice(1)} · live`;
}

function renderFilters() {
  const brands = state.facets.brands || [];
  const categories = state.facets.categories || [];

  elements.brandFilters.innerHTML = brands.length
    ? brands
        .map((brand) => {
          const active = state.filters.brand === brand.name ? " is-active" : "";
          return `
            <button
              class="chip${active}"
              type="button"
              data-action="toggle-brand"
              data-brand="${escapeAttribute(brand.name)}"
            >
              ${escapeHtml(brand.name)}
              <span>${brand.count}</span>
            </button>
          `;
        })
        .join("")
    : `<span class="saved-empty">Las marcas aparecen cuando la busqueda devuelve resultados.</span>`;

  elements.categoryFilters.innerHTML = categories.length
    ? categories
        .map((category) => {
          const active = state.filters.category === category.name ? " is-active" : "";
          return `
            <button
              class="chip${active}"
              type="button"
              data-action="toggle-category"
              data-category="${escapeAttribute(category.name)}"
            >
              ${escapeHtml(category.name)}
              <span>${category.count}</span>
            </button>
          `;
        })
        .join("")
    : `<span class="saved-empty">Las categorias se activan cuando hay resultados reales.</span>`;
}

function renderSidePanels() {
  const favorites = Object.values(state.favorites);

  elements.favoritesList.innerHTML = favorites.length
    ? favorites
        .slice(0, 8)
        .map(
          (product) => `
            <article class="saved-card">
              <strong>${escapeHtml(product.name)}</strong>
              <span class="saved-card__meta">${escapeHtml(product.brand || "Lider")} · ${formatPrice(product.price)}</span>
              <div class="saved-card__actions">
                <a href="${escapeAttribute(product.url || DEFAULT_SOURCE_URL)}" target="_blank" rel="noreferrer">Ver producto</a>
                <button type="button" data-action="remove-favorite" data-key="${escapeAttribute(getProductKey(product))}">Quitar</button>
              </div>
            </article>
          `
        )
        .join("")
    : `<div class="saved-empty">Marca productos como favoritos para seguirlos luego.</div>`;

  elements.historyList.innerHTML = state.history.length
    ? state.history
        .slice(0, 8)
        .map(
          (entry) => `
            <article class="saved-card">
              <strong>${escapeHtml(entry.query)}</strong>
              <span class="saved-card__meta">${escapeHtml(formatHistoryMeta(entry))}</span>
              <div class="saved-card__actions">
                <button type="button" data-action="history-query" data-query="${escapeAttribute(entry.query)}">Repetir</button>
              </div>
            </article>
          `
        )
        .join("")
    : `<div class="saved-empty">Tu historial reciente aparece automaticamente aqui.</div>`;
}

function renderResults() {
  const visibleResults = getVisibleResults();
  const activeFilters = getActiveFilterLabels();
  const cheapestKey = getCheapestProductKey(visibleResults);

  elements.visibleCount.textContent = `${visibleResults.length} producto${visibleResults.length === 1 ? "" : "s"}`;
  elements.activeFiltersLabel.textContent = activeFilters.length
    ? activeFilters.join(" · ")
    : "Sin filtros activos";

  elements.sourceLink.href = state.sourceUrl || DEFAULT_SOURCE_URL;

  if (state.loading) {
    elements.resultsGrid.innerHTML = Array.from({ length: 8 }, () => '<article class="skeleton-card"></article>').join("");
    return;
  }

  if (!visibleResults.length) {
    const emptyMessage = state.query
      ? `No hay productos visibles para "${state.query}" con los filtros actuales.`
      : "Todavia no hay resultados para mostrar.";

    const suggestions = state.suggestions
      .filter((item) => item.toLowerCase() !== state.query.toLowerCase())
      .slice(0, 4)
      .map(
        (item) =>
          `<button class="chip chip--ghost" type="button" data-action="suggestion-query" data-query="${escapeAttribute(item)}">${escapeHtml(item)}</button>`
      )
      .join("");

    elements.resultsGrid.innerHTML = `
      <article class="empty-state">
        <h3>Sin resultados visibles</h3>
        <p>${escapeHtml(emptyMessage)}</p>
        <div class="empty-state__actions">
          <button class="chip" type="button" data-action="reset-filters">Limpiar filtros</button>
          ${suggestions}
        </div>
      </article>
    `;
    return;
  }

  elements.resultsGrid.innerHTML = visibleResults
    .map((product) => renderProductCard(product, cheapestKey))
    .join("");
}

function renderProductCard(product, cheapestKey) {
  const key = getProductKey(product);
  const isFavorite = Boolean(state.favorites[key]);
  const isCheapest = key === cheapestKey;
  const discount = product.discount_percent ? `-${product.discount_percent}%` : "";

  return `
    <article class="product-card${isCheapest ? " product-card--best" : ""}">
      <button
        class="favorite-button${isFavorite ? " is-active" : ""}"
        type="button"
        data-action="toggle-favorite"
        data-key="${escapeAttribute(key)}"
        aria-label="${isFavorite ? "Quitar de favoritos" : "Agregar a favoritos"}"
      >
        ${isFavorite ? "&#9733;" : "&#9734;"}
      </button>

      <div class="product-card__media">
        ${
          product.image
            ? `<img src="${escapeAttribute(product.image)}" alt="${escapeAttribute(product.name)}" loading="lazy" />`
            : `<div class="product-card__placeholder">Sin imagen</div>`
        }
      </div>

      <div class="product-card__content">
        <div class="badge-row">
          <span class="badge">${escapeHtml(product.seller || "Lider")}</span>
          ${isCheapest ? '<span class="badge badge--best">Mejor precio</span>' : ""}
          ${product.is_offer ? '<span class="badge badge--offer">Oferta</span>' : ""}
          ${product.in_stock ? '<span class="badge badge--stock">En stock</span>' : ""}
          ${discount ? `<span class="badge badge--discount">${escapeHtml(discount)}</span>` : ""}
        </div>

        <div class="product-card__heading">
          <h3>${escapeHtml(product.name)}</h3>
          <p class="product-card__meta">
            ${escapeHtml([product.brand, product.category].filter(Boolean).join(" · ") || "Producto Lider")}
          </p>
        </div>

        <div class="product-card__price">
          <strong>${formatPrice(product.price)}</strong>
          ${
            product.original_price
              ? `<span class="product-card__old-price">${formatPrice(product.original_price)}</span>`
              : ""
          }
        </div>

        <p class="product-card__detail">${escapeHtml(buildPricingMeta(product))}</p>

        <div class="product-card__footer">
          <span class="product-card__availability">${escapeHtml(buildAvailabilityLabel(product))}</span>
          <button onclick="addToBasket(${JSON.stringify(product).replace(/"/g, '&quot;')})" class="btn btn--small">Agregar a canasta</button>
          <a
            class="action-link"
            href="${escapeAttribute(product.url || DEFAULT_SOURCE_URL)}"
            target="_blank"
            rel="noreferrer"
          >
            Ver producto
          </a>
        </div>
      </div>
    </article>
  `;
}

function getVisibleResults() {
  let results = state.results.map((product, index) => ({
    ...product,
    _index: Number.isFinite(product.position) ? product.position : index,
  }));

  const minPrice = Number(state.filters.minPrice);
  const maxPrice = Number(state.filters.maxPrice);

  if (Number.isFinite(minPrice) && state.filters.minPrice !== "") {
    results = results.filter((product) => Number(product.price) >= minPrice);
  }

  if (Number.isFinite(maxPrice) && state.filters.maxPrice !== "") {
    results = results.filter((product) => Number(product.price) <= maxPrice);
  }

  if (state.filters.onlyOffers) {
    results = results.filter((product) => Boolean(product.is_offer));
  }

  if (state.filters.onlyInStock) {
    results = results.filter((product) => hasStockAvailable(product));
  }

  if (state.filters.onlyFavorites) {
    results = results.filter((product) => Boolean(state.favorites[getProductKey(product)]));
  }

  if (state.filters.brand) {
    results = results.filter((product) => product.brand === state.filters.brand);
  }

  if (state.filters.category) {
    results = results.filter((product) => product.category === state.filters.category);
  }

  const sorters = {
    relevance: (a, b) => a._index - b._index,
    "price-asc": (a, b) => Number(a.price) - Number(b.price),
    "price-desc": (a, b) => Number(b.price) - Number(a.price),
    "savings-desc": (a, b) => Number(b.savings_amount || 0) - Number(a.savings_amount || 0),
    "name-asc": (a, b) => String(a.name).localeCompare(String(b.name), "es"),
  };

  results.sort(sorters[state.filters.sort] || sorters["price-asc"]);
  return results;
}

function syncFilterInputs() {
  elements.sortSelect.value = state.filters.sort;
  elements.minPriceInput.value = state.filters.minPrice;
  elements.maxPriceInput.value = state.filters.maxPrice;
  elements.offersToggle.checked = state.filters.onlyOffers;
  elements.stockToggle.checked = state.filters.onlyInStock;
  elements.favoritesToggle.checked = state.filters.onlyFavorites;
}

// Funciones de canastas
async function showBaskets() {
  // Ocultar búsqueda y mostrar canastas
  document.querySelector('.layout').style.display = 'none';
  elements.basketsSection.style.display = 'block';

  // Cargar canastas
  try {
    const response = await fetch('/baskets');
    const baskets = await response.json();
    state.baskets = baskets;
    renderBaskets();
  } catch (error) {
    console.error('Error loading baskets:', error);
  }
}

function renderBaskets() {
  elements.basketsList.innerHTML = state.baskets.map(basket => `
    <article class="basket-card" onclick="viewBasket('${basket.id}')">
      <h3>${escapeHtml(basket.name)}</h3>
      <div class="basket-meta">
        <span>${basket.item_count} productos</span>
        <span>${currencyFormatter.format(basket.total_price)}</span>
        <span>${basket.stores.join(', ')}</span>
      </div>
    </article>
  `).join('');
}

async function createBasket(name) {
  try {
    const response = await fetch('/baskets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name })
    });
    const basket = await response.json();
    state.baskets.unshift(basket);
    renderBaskets();
  } catch (error) {
    console.error('Error creating basket:', error);
  }
}

async function viewBasket(basketId) {
  try {
    const response = await fetch(`/baskets/${basketId}`);
    const basket = await response.json();
    state.currentBasket = basket;
    renderBasketDetail();
  } catch (error) {
    console.error('Error loading basket:', error);
  }
}

function renderBasketDetail() {
  const basket = state.currentBasket;
  if (!basket) return;

  elements.basketTitle.textContent = basket.name;
  elements.basketsList.style.display = 'none';
  elements.basketDetail.style.display = 'block';

  elements.basketItems.innerHTML = basket.items.map(item => `
    <article class="basket-item">
      <div class="basket-item__info">
        <h4>${escapeHtml(item.name)}</h4>
        <span>${item.store} • ${item.quantity} unidades</span>
      </div>
      <div class="basket-item__price">
        <span>${currencyFormatter.format(item.price * item.quantity)}</span>
        <button onclick="removeFromBasket('${basket.id}', '${item.product_id}')" class="btn btn--small">Remover</button>
      </div>
    </article>
  `).join('');

  const total = basket.items.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  elements.basketTotal.innerHTML = `
    <div class="total-summary">
      <strong>Total: ${currencyFormatter.format(total)}</strong>
    </div>
  `;
}

async function removeFromBasket(basketId, productId) {
  try {
    await fetch(`/baskets/${basketId}/items/${productId}`, { method: 'DELETE' });
    // Recargar la canasta
    viewBasket(basketId);
  } catch (error) {
    console.error('Error removing item:', error);
  }
}

// Función para agregar productos a canastas desde los resultados
function addToBasket(product) {
  const basketId = prompt("ID de la canasta (cópialo de la sección Canastas):");
  if (basketId) {
    fetch(`/baskets/${basketId}/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product, quantity: 1 })
    }).then(() => {
      alert('Producto agregado a la canasta');
    }).catch(error => {
      console.error('Error adding to basket:', error);
    });
  }
}

function hasStockAvailable(product) {
  return Boolean(product.in_stock) || String(product.availability || "").toUpperCase().includes("STOCK");
}

function buildPricingMeta(product) {
  const parts = [];

  if (product.unit_price) {
    parts.push(product.unit_price);
  }
  if (product.savings_amount) {
    parts.push(`Ahorra ${formatPrice(product.savings_amount)}`);
  }
  if (!parts.length && product.original_price && Number(product.original_price) > Number(product.price)) {
    parts.push(`Antes ${formatPrice(product.original_price)}`);
  }
  if (!parts.length) {
    parts.push("Precio disponible");
  }

  return parts.join(" · ");
}

function buildAvailabilityLabel(product) {
  if (hasStockAvailable(product)) {
    return "Disponible";
  }
  if (product.availability) {
    return String(product.availability).replace(/_/g, " ");
  }
  return "Stock no informado";
}

function getActiveFilterLabels() {
  const labels = [];

  if (state.filters.minPrice) {
    labels.push(`desde ${formatPrice(Number(state.filters.minPrice))}`);
  }
  if (state.filters.maxPrice) {
    labels.push(`hasta ${formatPrice(Number(state.filters.maxPrice))}`);
  }
  if (state.filters.onlyOffers) {
    labels.push("solo ofertas");
  }
  if (state.filters.onlyInStock) {
    labels.push("solo stock");
  }
  if (state.filters.onlyFavorites) {
    labels.push("solo favoritos");
  }
  if (state.filters.brand) {
    labels.push(`marca ${state.filters.brand}`);
  }
  if (state.filters.category) {
    labels.push(`categoria ${state.filters.category}`);
  }

  return labels;
}

function toggleFavorite(key) {
  if (state.favorites[key]) {
    delete state.favorites[key];
  } else {
    const product = state.results.find((item) => getProductKey(item) === key);
    if (!product) {
      return;
    }
    state.favorites[key] = product;
  }

  persistFavorites();
  renderHeroStats();
  renderSidePanels();
  renderResults();
}

function synchronizeFavoritesWithResults() {
  let changed = false;

  state.results.forEach((product) => {
    const key = getProductKey(product);
    if (state.favorites[key]) {
      state.favorites[key] = product;
      changed = true;
    }
  });

  if (changed) {
    persistFavorites();
  }
}

function pushHistory(query, count) {
  const entry = {
    query,
    count,
    timestamp: new Date().toISOString(),
  };

  state.history = [
    entry,
    ...state.history.filter((item) => item.query.toLowerCase() !== query.toLowerCase()),
  ].slice(0, 8);

  localStorage.setItem(STORAGE_KEYS.history, JSON.stringify(state.history));
}

function persistFavorites() {
  localStorage.setItem(STORAGE_KEYS.favorites, JSON.stringify(state.favorites));
}

function updateQueryString(query) {
  const url = new URL(window.location.href);
  url.searchParams.set("q", query);
  window.history.replaceState({}, "", url);
}

function getProductKey(product) {
  return product.sku || product.url || `${product.name}-${product.price}`;
}

function getCheapestProductKey(products) {
  if (!products.length) {
    return "";
  }

  const cheapest = products.reduce((best, current) => {
    if (!best || Number(current.price) < Number(best.price)) {
      return current;
    }
    return best;
  }, null);

  return cheapest ? getProductKey(cheapest) : "";
}

function getComputedStats(products) {
  if (!products.length) {
    return {
      minPrice: null,
      maxPrice: null,
      averagePrice: null,
      offerCount: 0,
      inStockCount: 0,
    };
  }

  const prices = products.map((product) => Number(product.price)).filter(Number.isFinite);
  return {
    minPrice: prices.length ? Math.min(...prices) : null,
    maxPrice: prices.length ? Math.max(...prices) : null,
    averagePrice: prices.length
      ? prices.reduce((total, value) => total + value, 0) / prices.length
      : null,
    offerCount: products.filter((product) => product.is_offer).length,
    inStockCount: products.filter((product) => hasStockAvailable(product)).length,
  };
}

function formatHistoryMeta(entry) {
  const count = Number(entry.count || 0);
  return `${count} resultado${count === 1 ? "" : "s"} · ${formatDateTime(entry.timestamp)}`;
}

function formatPrice(value) {
  return currencyFormatter.format(Number(value || 0));
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "recién";
  }

  return new Intl.DateTimeFormat("es-CL", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

function loadJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch (error) {
    return fallback;
  }
}

function escapeHtml(value) {
  return String(value == null ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
