(function () {

    // ---------- CONFIGURATION ----------
    const LOGOUT_TIME = 3 * 60 * 1000; // 3 minutes
    const LOGOUT_URL = "/logout/";
    const TOAST_DURATION = 3000; // Toast visible for 3 seconds
    const REDIRECT_DELAY = 3500; // Redirect after toast disappears

    let logoutTimer;
    let sessionExpired = false;

    // ---------- CREATE TOAST ----------
    function showToast(message) {
        // Create toast container if not exists
        let container = document.getElementById("toast-container");
        if (!container) {
            container = document.createElement("div");
            container.id = "toast-container";
            container.style.position = "fixed";
            container.style.top = "20px";
            container.style.right = "20px";
            container.style.zIndex = "9999";
            container.style.display = "flex";
            container.style.flexDirection = "column";
            container.style.gap = "10px";
            document.body.appendChild(container);
        }

        // Create toast element
        const toast = document.createElement("div");
        toast.innerText = message;
        toast.style.background = "#f44336"; // red
        toast.style.color = "#fff";
        toast.style.padding = "12px 20px";
        toast.style.borderRadius = "8px";
        toast.style.boxShadow = "0 4px 12px rgba(0,0,0,0.2)";
        toast.style.fontFamily = "Arial, sans-serif";
        toast.style.fontSize = "14px";
        toast.style.opacity = "0";
        toast.style.transform = "translateX(100%)";
        toast.style.transition = "all 0.5s ease";

        container.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.style.opacity = "1";
            toast.style.transform = "translateX(0)";
        }, 50);

        // Animate out & remove after TOAST_DURATION
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(100%)";
            setTimeout(() => toast.remove(), 500);
        }, TOAST_DURATION);
    }

    // ---------- TRIGGER LOGOUT ----------
    function logoutUser() {
        if(sessionExpired) return;
        sessionExpired = true;

        // Show toast
        showToast("⚠ Session expired. Redirecting to login...");

        // Redirect after toast
        setTimeout(() => {
            window.location.href = LOGOUT_URL;
        }, REDIRECT_DELAY);
    }

    // ---------- RESET TIMER ----------
    function resetTimer() {
        if(sessionExpired) return; // stop resetting after logout
        clearTimeout(logoutTimer);
        logoutTimer = setTimeout(logoutUser, LOGOUT_TIME);
    }

    // ---------- EVENT LISTENERS ----------
    window.onload = resetTimer;
    document.onmousemove = resetTimer;
    document.onkeypress = resetTimer;
    document.onclick = resetTimer;
    document.onscroll = resetTimer;

    // ---------- INTERACTION AFTER SESSION EXPIRED ----------
    document.addEventListener("click", resetTimer);
    document.addEventListener("keypress", resetTimer);

})();
