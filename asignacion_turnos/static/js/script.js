
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

 
function abrirModalFechasGT() {
  const modal = document.getElementById("modalFechasGT");
  modal.style.display = "block";
  setTimeout(() => {
    modal.classList.add("mostrar");
  }, 10);
}

function cerrarModalFechasGT() {
  const modal = document.getElementById("modalFechasGT");
  modal.classList.remove("mostrar");
  setTimeout(() => {
    modal.style.display = "none";
  }, 300);
}


function cargarFechasGT() {
    
  const fechaInicio = document.getElementById("fechaInicioGT").value;
  const fechaFin = document.getElementById("fechaFinGT").value;

  if (!fechaInicio || !fechaFin) {
     Swal.fire({
                    icon: "warning",
                    title: "Fechas vacias",
                    text: "Debes cargar un rengo valido de fechas",
                    });
  }else{

    const url = `${baseUrlSolicitudesGT}?fecha_inicio=${fechaInicio}&fecha_fin=${fechaFin}`;
    window.location.href = url; 

}
  cerrarModalFechasGT();
}

 
function abrirModalVerificacion() {
  const modal = document.getElementById("modalVerificacion");
  modal.style.display = "block";
  setTimeout(() => {
    modal.classList.add("mostrar");
  }, 10);
}

function cerrarModalVerificacion() {
  const modal = document.getElementById("modalVerificacion");
  modal.classList.remove("mostrar");
  setTimeout(() => {
    modal.style.display = "none";
  }, 300);
}

function cargarVerificacion(){
  const fecha = document.getElementById('fechaVerificacion').value
  const cargo = document.getElementById('cargoVerificacion').value
  
  if(fecha !== "" ){ 
    const url = `${baseUrlVerificacion}?fecha=${fecha}&cargo=${cargo}`
    window.location.href = url;
  }else{
     Swal.fire({
                    icon: "warning",
                    title: "Fecha vacia",
                    text: "Por favor indica un fecha valida",
                    });
      cerrarModalVerificacion();                
    }

  

  

}
