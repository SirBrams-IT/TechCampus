(function () {

    // ---------- CONFIGURATION ----------
    const LOGOUT_TIME = 5 * 60 * 1000;       // 5 minutes
    const WARNING_TIME = 4.5 * 60 * 1000;    // 4 minutes 30 seconds
    const LOGOUT_URL = "/logout/";           // Change if needed

    let logoutTimer;
    let warningTimer;

    // ---------- RESET TIMERS ----------
    function resetTimers() {
        clearTimeout(logoutTimer);
        clearTimeout(warningTimer);

        warningTimer = setTimeout(showWarningModal, WARNING_TIME);
        logoutTimer = setTimeout(logoutUser, LOGOUT_TIME);
    }

    // ---------- TRIGGER LOGOUT ----------
    function logoutUser() {
        window.location.href = LOGOUT_URL;
    }

    // ---------- SHOW WARNING ----------
    function showWarningModal() {
        const modal = document.getElementById("inactivityWarningModal");
        if (modal) {
            modal.style.display = "flex";
        }
    }

    // ---------- HIDE WARNING ----------
    window.closeInactivityModal = function() {
        const modal = document.getElementById("inactivityWarningModal");
        if (modal) {
            modal.style.display = "none";
        }
        resetTimers();
    }

    // ---------- EVENT LISTENERS ----------
    window.onload = resetTimers;
    document.onmousemove = resetTimers;
    document.onkeypress = resetTimers;
    document.onclick = resetTimers;
    document.onscroll = resetTimers;

})();
