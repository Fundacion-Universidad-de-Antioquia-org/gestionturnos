

const toggleDropdown = (dropdown, menu, isOpen) => {
    console.log("toggleDropdown:", dropdown, "isOpen:", isOpen);
    dropdown.classList.toggle("open", isOpen);
    menu.style.height = isOpen ? `${menu.scrollHeight}px` : 0;
};

const closeAllDropdowns = () => {
    document.querySelectorAll(".dropdown-container.open").forEach(openDropdown => {
        const menu = openDropdown.querySelector(".dropdown-menu");
        if (menu) {
            toggleDropdown(openDropdown, menu, false);
        }
    });
};


document.addEventListener('DOMContentLoaded', function () {
    console.log("JS cargado, iniciando listeners...");

    // Manejo de dropdowns del sidebar
    document.querySelectorAll(".dropdown-toggle").forEach(dropdownToggle => {
        console.log("Dropdown toggle encontrado:", dropdownToggle);

        dropdownToggle.addEventListener("click", e => {
            e.preventDefault();
            console.log("CLICK en .dropdown-toggle:", e.target);

            const sidebar = document.querySelector(".sidebar");
            const isCollapsed = sidebar.classList.contains("collapsed");

            if (isCollapsed) {
                console.log("Sidebar está colapsado. No se abre dropdown.");
                return;
            }

            const dropdownToggleLink = e.currentTarget;
            const dropdown = dropdownToggleLink.closest(".dropdown-container");
            if (!dropdown) {
                console.log("NO SE ENCONTRÓ .dropdown-container");
                return;
            }

            const menu = dropdown.querySelector(".dropdown-menu");
            if (!menu) {
                console.log("NO SE ENCONTRÓ .dropdown-menu");
                return;
            }

            const isOpen = dropdown.classList.contains("open");

            console.log("CLICK en dropdown:", dropdown);
            console.log("Dropdown menu scrollHeight:", menu.scrollHeight);

            closeAllDropdowns(); // Cierra los otros
            toggleDropdown(dropdown, menu, !isOpen); // Abre/cierra este
        });
    });

    // Manejo del botón de colapsar sidebar (si existe)
    const sidebarToggler = document.querySelector(".sidebar-toggler");
    if (sidebarToggler) {
        console.log("Sidebar-toggler encontrado.");
        sidebarToggler.addEventListener("click", function () {
            closeAllDropdowns(); // Cierra menús abiertos
            document.querySelector(".sidebar").classList.toggle("collapsed");
        });
    }
});

/* Filtros - acordeon*/
  document.querySelectorAll(".accordion-title").forEach(title => {
    title.addEventListener("click", () => {
      const content = title.nextElementSibling;
      content.style.display = content.style.display === "block" ? "none" : "block";
    });
  });

 

