(function () {
  "use strict";

  /* ------------------------------------------------------------------ */
  /* Theme toggle (persisted in localStorage)                            */
  /* ------------------------------------------------------------------ */
  var THEME_KEY = "statement-ai-docs-theme";
  var root = document.documentElement;
  var themeToggle = document.getElementById("docs-theme-toggle");

  function applyTheme(theme) {
    if (theme === "dark") {
      root.setAttribute("data-theme", "dark");
    } else {
      root.removeAttribute("data-theme");
    }
  }

  function currentTheme() {
    return root.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  try {
    var saved = localStorage.getItem(THEME_KEY);
    if (saved) {
      applyTheme(saved);
    } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      applyTheme("dark");
    }
  } catch (e) {
    /* localStorage unavailable (e.g. private browsing) — ignore */
  }

  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      applyTheme(next);
      try {
        localStorage.setItem(THEME_KEY, next);
      } catch (e) {
        /* ignore */
      }
    });
  }

  /* ------------------------------------------------------------------ */
  /* Mobile sidebar toggle                                               */
  /* ------------------------------------------------------------------ */
  var sidebar = document.getElementById("docs-sidebar");
  var sidebarToggle = document.getElementById("docs-sidebar-toggle");
  var backdrop = document.getElementById("docs-sidebar-backdrop");

  function closeSidebar() {
    if (!sidebar) return;
    sidebar.classList.remove("is-open");
    if (backdrop) backdrop.classList.remove("is-open");
    if (sidebarToggle) sidebarToggle.setAttribute("aria-expanded", "false");
  }

  function toggleSidebar() {
    if (!sidebar) return;
    var isOpen = sidebar.classList.toggle("is-open");
    if (backdrop) backdrop.classList.toggle("is-open", isOpen);
    if (sidebarToggle) sidebarToggle.setAttribute("aria-expanded", String(isOpen));
  }

  if (sidebarToggle) sidebarToggle.addEventListener("click", toggleSidebar);
  if (backdrop) backdrop.addEventListener("click", closeSidebar);

  // Close the mobile sidebar automatically after following a nav link.
  document.querySelectorAll(".docs-nav a").forEach(function (link) {
    link.addEventListener("click", closeSidebar);
  });

  /* ------------------------------------------------------------------ */
  /* Sidebar search filter                                                */
  /* ------------------------------------------------------------------ */
  var searchInput = document.getElementById("docs-search-input");
  var emptyMessage = document.getElementById("docs-search-empty");

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      var query = searchInput.value.trim().toLowerCase();
      var anyVisible = false;

      document.querySelectorAll(".docs-nav-group").forEach(function (group) {
        var groupHasMatch = false;

        group.querySelectorAll("li").forEach(function (li) {
          var text = li.textContent.trim().toLowerCase();
          var matches = query === "" || text.indexOf(query) !== -1;
          li.classList.toggle("docs-nav-hidden", !matches);
          if (matches) groupHasMatch = true;
        });

        group.style.display = groupHasMatch ? "" : "none";
        if (groupHasMatch) anyVisible = true;
      });

      if (emptyMessage) emptyMessage.hidden = anyVisible;
    });
  }

  /* ------------------------------------------------------------------ */
  /* Auto-generated "On this page" TOC with scrollspy                    */
  /* ------------------------------------------------------------------ */
  var content = document.getElementById("docs-content");
  var tocList = document.getElementById("docs-toc-list");
  var tocAside = document.getElementById("docs-toc");

  if (content && tocList) {
    var headings = content.querySelectorAll("h2[id], h3[id]");

    if (headings.length === 0) {
      if (tocAside) tocAside.style.display = "none";
    } else {
      var tocLinks = [];

      headings.forEach(function (heading) {
        var li = document.createElement("li");
        if (heading.tagName === "H3") li.classList.add("docs-toc-h3");

        var a = document.createElement("a");
        a.href = "#" + heading.id;
        a.textContent = heading.textContent;
        li.appendChild(a);
        tocList.appendChild(li);
        tocLinks.push({ link: a, heading: heading });
      });

      var setActive = function (id) {
        tocLinks.forEach(function (entry) {
          entry.link.classList.toggle("active", entry.heading.id === id);
        });
      };

      if ("IntersectionObserver" in window) {
        var observer = new IntersectionObserver(
          function (entries) {
            var visible = entries
              .filter(function (e) {
                return e.isIntersecting;
              })
              .sort(function (a, b) {
                return a.boundingClientRect.top - b.boundingClientRect.top;
              });

            if (visible.length > 0) {
              setActive(visible[0].target.id);
            }
          },
          { rootMargin: "-96px 0px -70% 0px", threshold: 0 }
        );

        headings.forEach(function (heading) {
          observer.observe(heading);
        });
      }
    }
  }
})();
