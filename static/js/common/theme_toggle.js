(function initThemeToggle() {
    var STORAGE_KEY = "sams-theme";
    var LIGHT = "light";
    var DARK = "dark";
    var THEME_COLOR_MAP = {
        light: "#0f766e",
        dark: "#0b1220",
    };

    function getSavedTheme() {
        try {
            return window.localStorage.getItem(STORAGE_KEY);
        } catch (err) {
            return null;
        }
    }

    function getSystemTheme() {
        return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? DARK : LIGHT;
    }

    function resolveTheme() {
        var saved = getSavedTheme();
        if (saved === DARK || saved === LIGHT) {
            return saved;
        }
        return getSystemTheme();
    }

    function syncMetaThemeColor(theme) {
        var meta = document.querySelector('meta[name="theme-color"]');
        if (meta) {
            meta.setAttribute("content", THEME_COLOR_MAP[theme] || THEME_COLOR_MAP.light);
        }
    }

    function syncToggleUi(theme) {
        var icon = document.getElementById("themeToggleIcon");
        var text = document.getElementById("themeToggleText");
        var isDark = theme === DARK;
        if (icon) {
            icon.textContent = isDark ? "SUN" : "MOON";
        }
        if (text) {
            text.textContent = isDark ? "Light" : "Dark";
        }
    }

    function applyTheme(theme, persist) {
        var nextTheme = theme === DARK ? DARK : LIGHT;
        document.documentElement.setAttribute("data-theme", nextTheme);
        document.documentElement.setAttribute("data-bs-theme", nextTheme);
        syncMetaThemeColor(nextTheme);
        syncToggleUi(nextTheme);

        if (persist) {
            try {
                window.localStorage.setItem(STORAGE_KEY, nextTheme);
            } catch (err) {
                // no-op
            }
        }
    }

    function bindToggle() {
        var btn = document.getElementById("themeToggleBtn");
        if (!btn) {
            return;
        }
        btn.addEventListener("click", function () {
            var current = document.documentElement.getAttribute("data-theme") === DARK ? DARK : LIGHT;
            var nextTheme = current === DARK ? LIGHT : DARK;
            applyTheme(nextTheme, true);
        });
    }

    function setup() {
        applyTheme(resolveTheme(), false);
        bindToggle();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", setup);
    } else {
        setup();
    }
})();
