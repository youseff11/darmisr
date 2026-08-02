(() => {
    "use strict";

    // Get the saved theme from localStorage or use system preference
    const getSavedTheme = () => {
        const saved = localStorage.getItem("theme");
        if (saved) return saved;

        // Check system preference
        if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
            return "dark";
        }
        return "light";
    };

    // Set the theme
    const setTheme = (theme) => {
        const html = document.documentElement;
        html.setAttribute("data-theme", theme);
        localStorage.setItem("theme", theme);

        // Update the toggle button icon
        const toggleBtn = document.querySelector(".theme-toggle");
        if (toggleBtn) {
            const icon = toggleBtn.querySelector("i");
            if (icon) {
                if (theme === "dark") {
                    icon.className = "bi bi-sun-fill";
                    toggleBtn.setAttribute("aria-label", "تبديل إلى الوضع الفاتح");
                } else {
                    icon.className = "bi bi-moon-fill";
                    toggleBtn.setAttribute("aria-label", "تبديل إلى الوضع الداكن");
                }
            }
        }
    };

    // Initialize theme on page load
    const initTheme = () => {
        const theme = getSavedTheme();
        setTheme(theme);
    };

    // Handle theme toggle button click
    const setupToggleButton = () => {
        const toggleBtn = document.querySelector(".theme-toggle");
        if (!toggleBtn) return;

        toggleBtn.addEventListener("click", () => {
            const html = document.documentElement;
            const currentTheme = html.getAttribute("data-theme") || "light";
            const newTheme = currentTheme === "dark" ? "light" : "dark";
            setTheme(newTheme);
        });
    };

    // Listen for system theme changes
    const setupSystemThemeListener = () => {
        if (!window.matchMedia) return;

        const darkModeQuery = window.matchMedia("(prefers-color-scheme: dark)");
        darkModeQuery.addEventListener("change", (e) => {
            const newTheme = e.matches ? "dark" : "light";
            setTheme(newTheme);
        });
    };

    // Initialize when DOM is ready
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", () => {
            initTheme();
            setupToggleButton();
            setupSystemThemeListener();
        });
    } else {
        initTheme();
        setupToggleButton();
        setupSystemThemeListener();
    }
})();
