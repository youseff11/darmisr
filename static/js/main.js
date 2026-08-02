(() => {
    "use strict";

    const getCookie = (name) => {
        const value = document.cookie.split(";").map((item) => item.trim()).find((item) => item.startsWith(`${name}=`));
        return value ? decodeURIComponent(value.split("=").slice(1).join("=")) : "";
    };

    const toast = document.querySelector("[data-site-toast]");
    let toastTimer;
    const showToast = (message) => {
        if (!toast || !message) return;
        toast.textContent = message;
        toast.classList.add("show");
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toast.classList.remove("show"), 3200);
    };

    document.querySelectorAll("[data-back-to-top]").forEach((button) => {
        const toggle = () => button.classList.toggle("show", window.scrollY > 500);
        window.addEventListener("scroll", toggle, { passive: true });
        toggle();
        button.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
    });

    document.querySelectorAll("[data-quantity-control]").forEach((control) => {
        const input = control.querySelector("input[type='number']");
        if (!input) return;
        control.querySelectorAll("button[data-step]").forEach((button) => {
            button.addEventListener("click", () => {
                const step = Number(button.dataset.step || 0);
                const min = Number(input.min || 1);
                const max = Number(input.max || 999);
                input.value = Math.min(max, Math.max(min, Number(input.value || min) + step));
                input.dispatchEvent(new Event("change", { bubbles: true }));
            });
        });
    });

    document.querySelectorAll("form[data-ajax-form]").forEach((form) => {
        form.addEventListener("submit", async (event) => {
            if (!window.fetch) return;
            event.preventDefault();
            const submitButton = form.querySelector("button[type='submit']");
            const originalHTML = submitButton ? submitButton.innerHTML : "";
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>';
            }
            try {
                const response = await fetch(form.action, {
                    method: "POST",
                    body: new FormData(form),
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "X-CSRFToken": getCookie("csrftoken"),
                    },
                });
                const data = await response.json();
                if (!response.ok || !data.ok) throw new Error(data.message || "تعذر تنفيذ الطلب.");
                if (typeof data.cart_count !== "undefined") {
                    document.querySelectorAll("[data-cart-count]").forEach((node) => { node.textContent = data.cart_count; });
                }
                if (typeof data.active !== "undefined") {
                    form.querySelectorAll("[data-wishlist-icon]").forEach((icon) => {
                        icon.classList.toggle("bi-heart-fill", data.active);
                        icon.classList.toggle("bi-heart", !data.active);
                    });
                    form.querySelectorAll("[data-wishlist-button]").forEach((button) => button.classList.toggle("active", data.active));
                }
                showToast(data.message);
            } catch (error) {
                showToast(error.message || "حدث خطأ غير متوقع.");
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalHTML;
                }
            }
        });
    });

    const searchInput = document.querySelector("[data-search-input]");
    const suggestions = document.querySelector("[data-search-suggestions]");
    let searchTimer;
    let searchController;
    const closeSuggestions = () => {
        if (suggestions) {
            suggestions.hidden = true;
            suggestions.replaceChildren();
        }
    };
    if (searchInput && suggestions) {
        searchInput.addEventListener("input", () => {
            clearTimeout(searchTimer);
            const query = searchInput.value.trim();
            if (query.length < 2) return closeSuggestions();
            searchTimer = setTimeout(async () => {
                if (searchController) searchController.abort();
                searchController = new AbortController();
                try {
                    const url = new URL(searchInput.dataset.suggestionsUrl, window.location.origin);
                    url.searchParams.set("q", query);
                    const response = await fetch(url, { signal: searchController.signal });
                    const data = await response.json();
                    suggestions.replaceChildren();
                    if (!data.results.length) return closeSuggestions();
                    data.results.forEach((item) => {
                        const link = document.createElement("a");
                        link.className = "suggestion-item";
                        link.href = item.url;
                        const image = document.createElement("span");
                        if (item.cover) {
                            const img = document.createElement("img");
                            img.src = item.cover;
                            img.alt = "";
                            image.appendChild(img);
                        } else {
                            image.className = "book-placeholder";
                            image.textContent = "‹";
                        }
                        const copy = document.createElement("span");
                        const title = document.createElement("strong");
                        title.textContent = item.title;
                        const author = document.createElement("small");
                        author.textContent = item.author;
                        copy.append(title, author);
                        const price = document.createElement("em");
                        price.textContent = `${item.price} ج.م`;
                        link.append(image, copy, price);
                        suggestions.appendChild(link);
                    });
                    suggestions.hidden = false;
                } catch (error) {
                    if (error.name !== "AbortError") closeSuggestions();
                }
            }, 280);
        });
        document.addEventListener("click", (event) => {
            if (!event.target.closest(".site-search")) closeSuggestions();
        });
        searchInput.addEventListener("keydown", (event) => {
            if (event.key === "Escape") closeSuggestions();
        });
    }

    document.querySelectorAll("[data-format-picker]").forEach((picker) => {
        const form = picker.closest("[data-product-purchase]");
        const priceNode = document.querySelector("[data-product-price]");
        const oldPriceNode = document.querySelector("[data-product-old-price]");
        const quantityInput = form ? form.querySelector("input[name='quantity']") : null;
        picker.querySelectorAll("input[name='format']").forEach((radio) => {
            radio.addEventListener("change", () => {
                if (!radio.checked) return;
                if (priceNode) priceNode.textContent = `${radio.dataset.price} ج.م`;
                if (oldPriceNode) {
                    oldPriceNode.textContent = radio.dataset.oldPrice ? `${radio.dataset.oldPrice} ج.م` : "";
                    oldPriceNode.hidden = !radio.dataset.oldPrice;
                }
                if (quantityInput) {
                    const digital = radio.value === "digital";
                    quantityInput.value = 1;
                    quantityInput.disabled = digital;
                    quantityInput.closest("[data-quantity-control]")?.classList.toggle("opacity-50", digital);
                }
            });
        });
    });

    document.querySelectorAll("[data-gallery-thumb]").forEach((thumb) => {
        thumb.addEventListener("click", () => {
            const main = document.querySelector("[data-gallery-main]");
            if (!main) return;
            main.src = thumb.dataset.galleryThumb;
            main.alt = thumb.dataset.galleryAlt || main.alt;
            document.querySelectorAll("[data-gallery-thumb]").forEach((item) => item.closest(".product-thumb")?.classList.remove("active"));
            thumb.closest(".product-thumb")?.classList.add("active");
        });
    });

    document.querySelectorAll("[data-filter-toggle]").forEach((button) => {
        button.addEventListener("click", () => document.querySelector("[data-filter-panel]")?.classList.toggle("show"));
    });

    document.querySelectorAll(".messages-wrap .alert").forEach((alert, index) => {
        setTimeout(() => {
            if (window.bootstrap) bootstrap.Alert.getOrCreateInstance(alert).close();
        }, 5500 + index * 400);
    });
})();
