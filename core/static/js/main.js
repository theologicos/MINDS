document.addEventListener("DOMContentLoaded", function () {

    // ── Sidebar toggle ──────────────────────────────────────────────────
    const appShell      = document.getElementById("app-shell");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const COLLAPSED_KEY = "sidebar_collapsed";

    if (localStorage.getItem(COLLAPSED_KEY) === "1" && window.innerWidth > 1024) {
        appShell.classList.add("sidebar-collapsed");
    }

    if (!document.getElementById("sidebarBackdrop")) {
        const backdrop = document.createElement("div");
        backdrop.className = "sidebar-backdrop";
        backdrop.id = "sidebarBackdrop";
        appShell.appendChild(backdrop);
        backdrop.addEventListener("click", closeMobileSidebar);
    }

    function closeMobileSidebar() {
        appShell.classList.remove("sidebar-open");
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", function () {
            if (window.innerWidth <= 1024) {
                appShell.classList.toggle("sidebar-open");
            } else {
                const collapsed = appShell.classList.toggle("sidebar-collapsed");
                localStorage.setItem(COLLAPSED_KEY, collapsed ? "1" : "0");
            }
        });
    }

    document.querySelectorAll(".sidebar-link").forEach(link => {
        link.addEventListener("click", () => {
            if (window.innerWidth <= 1024) closeMobileSidebar();
        });
    });

    // ── Dropdowns ──────────────────────────────────────────────────────
    function setupDropdown(toggleId, panelId) {
        const toggle = document.getElementById(toggleId);
        const panel  = document.getElementById(panelId);
        if (!toggle || !panel) return;
        toggle.addEventListener("click", function (e) {
            e.stopPropagation();
            const isOpen = !panel.classList.contains("hidden");
            document.querySelectorAll(".dropdown-panel").forEach(p => p.classList.add("hidden"));
            panel.classList.toggle("hidden", isOpen);
        });
    }
    setupDropdown("notifBellToggle", "notificationDropdown");
    setupDropdown("userMenuToggle",  "userDropdown");
    document.addEventListener("click", () => {
        document.querySelectorAll(".dropdown-panel").forEach(p => p.classList.add("hidden"));
    });

    // ── Modals ─────────────────────────────────────────────────────────
    function initModals(root) {
        root.querySelectorAll("[data-modal-target]").forEach(btn => {
            btn.addEventListener("click", function () {
                const modal = document.getElementById(this.dataset.modalTarget);
                if (modal) modal.classList.add("active");
            });
        });
        root.querySelectorAll("[data-modal-close]").forEach(btn => {
            btn.addEventListener("click", function () {
                const modal = document.getElementById(this.dataset.modalClose);
                if (modal) modal.classList.remove("active");
            });
        });
        root.querySelectorAll(".modal-overlay").forEach(overlay => {
            overlay.addEventListener("click", function (e) {
                if (e.target === overlay) overlay.classList.remove("active");
            });
        });
    }
    initModals(document);

    // ── File upload ────────────────────────────────────────────────────
    document.querySelectorAll(".file-upload").forEach(upload => {
        const input   = upload.querySelector('input[type="file"]');
        const display = upload.parentElement.querySelector(".file-upload-filename");
        if (!input) return;
        upload.addEventListener("click", () => input.click());
        upload.addEventListener("dragover", e => { e.preventDefault(); upload.classList.add("dragover"); });
        upload.addEventListener("dragleave", () => upload.classList.remove("dragover"));
        upload.addEventListener("drop", e => {
            e.preventDefault();
            upload.classList.remove("dragover");
            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                showFilename(e.dataTransfer.files[0].name);
            }
        });
        input.addEventListener("change", () => {
            if (input.files.length) showFilename(input.files[0].name);
        });
        function showFilename(name) {
            if (display) {
                display.classList.remove("hidden");
                const span = display.querySelector("span");
                if (span) span.textContent = name;
            }
        }
    });

    // ── Notification badge polling ──────────────────────────────────────
    function refreshNotifBadge() {
        fetch("/notifications/unread-count/")
            .then(r => r.json())
            .then(data => {
                const dot          = document.querySelector(".topbar-icon-btn .badge-dot");
                const sidebarBadge = document.querySelector(".sidebar-link[href*='notifications'] .sidebar-link-badge");
                const count = data.unread_count;
                if (dot)          dot.style.display         = count > 0 ? "block" : "none";
                if (sidebarBadge) {
                    sidebarBadge.textContent   = count;
                    sidebarBadge.style.display = count > 0 ? "inline-flex" : "none";
                }
            })
            .catch(() => {});
    }
    if (document.getElementById("notifBellToggle")) {
        setInterval(refreshNotifBadge, 4000);
    }

    // ── Page content replacer (shared by auto-refresh + search) ────────
    function replacePageContent(html) {
        const parser     = new DOMParser();
        const newDoc     = parser.parseFromString(html, "text/html");
        const newContent = newDoc.querySelector(".page-content");
        const curContent = document.querySelector(".page-content");
        if (newContent && curContent) {
            curContent.innerHTML = newContent.innerHTML;
            initModals(curContent);   // re-attach modal handlers on new DOM
        }
    }

    // ── Auto-refresh list pages ─────────────────────────────────────────
    // Paused while a search fetch is in flight to avoid races.
    let searchInFlight = false;

    const autoRefreshEl = document.querySelector("[data-auto-refresh]");
    if (autoRefreshEl) {
        const interval = parseInt(autoRefreshEl.dataset.autoRefresh || "5000");
        setInterval(() => {
            // Don't refresh if: modal open, input focused, or search running
            const modalOpen    = document.querySelector(".modal-overlay.active");
            const inputFocused = document.activeElement &&
                ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName);
            if (modalOpen || inputFocused || searchInFlight) return;

            fetch(window.location.href, { headers: { "X-Requested-With": "XMLHttpRequest" } })
                .then(r => r.text())
                .then(html => replacePageContent(html))
                .catch(() => {});
        }, interval);
    }

    // ── Global search — event delegation so it survives DOM replacement ─
    //
    // BUG IN ORIGINAL CODE: listeners were attached directly to the input
    // element. When replacePageContent() swapped innerHTML, that element was
    // removed from the DOM and its listeners died. Every subsequent keystroke
    // was silently ignored.
    //
    // FIX: listen on `document` using event delegation. The topbar search
    // input is OUTSIDE .page-content (it's in .topbar which is never
    // replaced), so it actually never dies — but delegating is still safer
    // and handles any search inputs injected into replaced content too.

    let searchDebounce = null;

    document.addEventListener("input", function (e) {
        const input = e.target;

        // Only handle inputs named "q" inside a .search-bar form
        if (!input.matches(".search-bar input[name='q']")) return;

        // Show spinner, hide magnifying glass
        const form    = input.closest("form");
        const icon    = form && form.querySelector("#searchIcon");
        const spinner = form && form.querySelector("#searchSpinner");
        if (icon)    icon.classList.add("hidden");
        if (spinner) spinner.classList.remove("hidden");

        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => {
            const q = input.value.trim();

            // Restore icon
            if (icon)    icon.classList.remove("hidden");
            if (spinner) spinner.classList.add("hidden");

            // If the form has an explicit action (the global search form),
            // let it navigate normally on Enter — but on input event we do
            // a live AJAX update of .page-content only when already ON the
            // search results page, so the user sees instant filtering.
            const formAction = form ? (form.getAttribute("action") || "") : "";
            const onSearchPage = window.location.pathname.includes("/search/");

            if (onSearchPage) {
                // Live-filter the results page
                const url = new URL(window.location.href);
                url.searchParams.set("q", q);
                if (!q) url.searchParams.delete("q");
                history.replaceState(null, "", url.toString());

                searchInFlight = true;
                fetch(url.toString(), { headers: { "X-Requested-With": "XMLHttpRequest" } })
                    .then(r => r.text())
                    .then(html => replacePageContent(html))
                    .catch(() => {})
                    .finally(() => { searchInFlight = false; });

            } else if (!formAction || formAction === window.location.pathname) {
                // Legacy behaviour: search bar with no action (per-page list filter)
                const url = new URL(window.location.href);
                url.searchParams.set("q", q);
                if (!q) url.searchParams.delete("q");
                history.replaceState(null, "", url.toString());

                searchInFlight = true;
                fetch(url.toString(), { headers: { "X-Requested-With": "XMLHttpRequest" } })
                    .then(r => r.text())
                    .then(html => replacePageContent(html))
                    .catch(() => {})
                    .finally(() => { searchInFlight = false; });
            }
            // If formAction points elsewhere (e.g. /search/) and we're NOT
            // already on that page, do nothing on input — let the form
            // submit naturally on Enter / click.

        }, 350);
    });

    // ── Status filter tabs — live filter without full reload ───────────
    document.addEventListener("click", function (e) {
        const tab = e.target.closest(".status-tab");
        if (!tab || !tab.href) return;
        e.preventDefault();
        const url = new URL(tab.href, window.location.origin);
        history.pushState(null, "", url.toString());
        fetch(url.toString(), { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(r => r.text())
            .then(html => replacePageContent(html))
            .catch(() => {});
    });

    // Handle browser back/forward
    window.addEventListener("popstate", () => {
        fetch(window.location.href, { headers: { "X-Requested-With": "XMLHttpRequest" } })
            .then(r => r.text())
            .then(html => replacePageContent(html))
            .catch(() => {});
    });

});
