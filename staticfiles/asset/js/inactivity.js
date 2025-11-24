
(function () {

    // ---------- CONFIGURATION ----------
    const LOGOUT_TIME = 3 * 60 * 1000; // 3 minutes
    const LOGOUT_URL = "/logout/";

    let logoutTimer;
    let sessionExpired = false;

    // ---------- TRIGGER LOGOUT ----------
    function logoutUser() {
        if(sessionExpired) return;
        sessionExpired = true;
        alert("⚠ Session expired. Redirecting to login...");
        window.location.href = LOGOUT_URL;
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
    document.addEventListener("click", function() {
        if(sessionExpired){
            alert("⚠ Session expired. Redirecting to login...");
            window.location.href = LOGOUT_URL;
        }
    });
    document.addEventListener("keypress", function() {
        if(sessionExpired){
            alert("⚠ Session expired. Redirecting to login...");
            window.location.href = LOGOUT_URL;
        }
    });

})();

