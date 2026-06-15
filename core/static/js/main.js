document.addEventListener("DOMContentLoaded", function () {
    const appShell = document.getElementById("app-shell");
    const sidebarToggle = document.getElementById("sidebarToggle");

    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", function () {
            if (window.innerWidth <= 1024) {
                appShell.classList.toggle("sidebar-open");
            } else {
                appShell.classList.toggle("sidebar-collapsed");
            }
        });
    }

    function setupDropdown(toggleId, panelId) {
        const toggle = document.getElementById(toggleId);
        const panel = document.getElementById(panelId);
        if (!toggle || !panel) return;
        toggle.addEventListener("click", function (e) {
            e.stopPropagation();
            const isOpen = !panel.classList.contains("hidden");
            document.querySelectorAll(".dropdown-panel").forEach(p => p.classList.add("hidden"));
            panel.classList.toggle("hidden", isOpen);
        });
    }

    setupDropdown("notifBellToggle", "notificationDropdown");
    setupDropdown("userMenuToggle", "userDropdown");

    document.addEventListener("click", function () {
        document.querySelectorAll(".dropdown-panel").forEach(p => p.classList.add("hidden"));
    });

    document.querySelectorAll("[data-modal-target]").forEach(btn => {
        btn.addEventListener("click", function () {
            const modal = document.getElementById(this.dataset.modalTarget);
            if (modal) modal.classList.add("active");
        });
    });

    document.querySelectorAll("[data-modal-close]").forEach(btn => {
        btn.addEventListener("click", function () {
            const modal = document.getElementById(this.dataset.modalClose);
            if (modal) modal.classList.remove("active");
        });
    });

    document.querySelectorAll(".modal-overlay").forEach(overlay => {
        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) overlay.classList.remove("active");
        });
    });

    document.querySelectorAll(".file-upload").forEach(upload => {
        const input = upload.querySelector('input[type="file"]');
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

    // Notification badge polling every 60 seconds
    function pollNotifCount() {
        fetch("/notifications/unread-count/")
            .then(r => r.json())
            .then(data => {
                const dot = document.querySelector(".topbar-icon-btn .badge-dot");
                const sidebarBadge = document.querySelector(".sidebar-link[href*='notifications'] .sidebar-link-badge");
                const count = data.unread_count;
                if (dot) dot.style.display = count > 0 ? "block" : "none";
                if (sidebarBadge) {
                    sidebarBadge.textContent = count;
                    sidebarBadge.style.display = count > 0 ? "inline-flex" : "none";
                }
            })
            .catch(() => {});
    }

    if (document.getElementById("notifBellToggle")) {
        setInterval(pollNotifCount, 60000);
    }
});
