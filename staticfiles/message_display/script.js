function bramsShowToast(message, type="success") {
    // create container if not exist
    let container = document.getElementById("brams_toast_container");
    if (!container) {
        container = document.createElement("div");
        container.id = "brams_toast_container";
        document.body.appendChild(container);
    }

    // create toast
    const toast = document.createElement("div");
    toast.className = `brams-toast brams-${type}`;

    toast.innerHTML = `
        ${message}
        <span class="brams-toast-close">&times;</span>
    `;

    container.appendChild(toast);

    // show
    setTimeout(() => toast.classList.add("brams-show"), 100);

    // auto-remove after 4 seconds
    setTimeout(() => {
        toast.classList.remove("brams-show");
        setTimeout(() => toast.remove(), 400);
    }, 5000);

    // close manually
    toast.querySelector(".brams-toast-close").onclick = () => {
        toast.classList.remove("brams-show");
        setTimeout(() => toast.remove(), 400);
    };
}


window.addEventListener("load", function() {
    const loader = document.getElementById("loader-overlay");
    loader.style.transition = "opacity 0.3s ease";
    loader.style.opacity = "0";
    setTimeout(() => loader.style.display = "none", 300);
});