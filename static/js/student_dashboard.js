document.addEventListener("DOMContentLoaded", () => {
    // ── Sidebar Toggle ───────────────────────────────────────
    const profileToggle = document.getElementById("profileToggle");
    const sidebar = document.getElementById("sidebar");
    const sidebarOverlay = document.getElementById("sidebarOverlay");
    const closeSidebarBtn = document.getElementById("closeSidebar");

    function openSidebar() {
        sidebar.classList.add("active");
        sidebarOverlay.classList.add("active");
    }

    function closeSidebar() {
        sidebar.classList.remove("active");
        sidebarOverlay.classList.remove("active");
    }

    profileToggle.addEventListener("click", openSidebar);
    closeSidebarBtn.addEventListener("click", closeSidebar);
    sidebarOverlay.addEventListener("click", closeSidebar);

    // ── Menu Buttons ─────────────────────────────────────────
    const editProfileBtn = document.getElementById("editProfileBtn");
    const attendedLabsBtn = document.getElementById("attendedLabsBtn");
    const labHistoryBtn = document.getElementById("labHistoryBtn");
    const selectLabBtn = document.getElementById("selectLabBtn");

    if (editProfileBtn) {
        editProfileBtn.addEventListener("click", (e) => {
            e.preventDefault();
            closeSidebar();
            new bootstrap.Modal(document.getElementById("editProfileModal")).show();
        });
    }

    if (attendedLabsBtn) {
        attendedLabsBtn.addEventListener("click", (e) => {
            e.preventDefault();
            closeSidebar();
            new bootstrap.Modal(document.getElementById("attendedLabsModal")).show();
        });
    }

    if (labHistoryBtn) {
        labHistoryBtn.addEventListener("click", (e) => {
            e.preventDefault();
            closeSidebar();
            new bootstrap.Modal(document.getElementById("labHistoryModal")).show();
        });
    }

    if (selectLabBtn) {
        selectLabBtn.addEventListener("click", (e) => {
            e.preventDefault();
            closeSidebar();
            document.getElementById("defaultView").classList.add("d-none");
            document.getElementById("selectLabView").classList.remove("d-none");
        });
    }

    // ── Back to Dashboard from Select Lab ────────────────────
    document.getElementById("backToDefault")?.addEventListener("click", () => {
        document.getElementById("selectLabView").classList.add("d-none");
        document.getElementById("defaultView").classList.remove("d-none");
    });

    // ── Show Lab Details (fake / demo) ───────────────────────

    document.getElementById("showLabDetailsBtn")?.addEventListener("click", function () {

        const labId = document.getElementById("subjectSelect").value;
        if (!labId) return;

        fetch(`/student/lab-details/${labId}/`)
            .then(response => response.json())
            .then(data => {

                document.getElementById("labSubjectTitle").textContent = data.name;

                document.querySelector("#labDetailsPlaceholder a:nth-child(1)").href = data.syllabus;
                document.querySelector("#labDetailsPlaceholder a:nth-child(2)").href = data.manual;

                document.getElementById("expListItem").textContent =
                    "Experiments: " + data.experiments;

                document.getElementById("labDetailsPlaceholder").classList.remove("d-none");
            });
    });

    let currentRoom = null;
    window.isCallClosing = false; // Add lockout flag

    function checkActiveCall() {
        if (window.isCallClosing) return; // Prevent ghost UI resurrects during teardown
        
        fetch("/student/check-call/")
            .then(res => res.json())
            .then(data => {
                if (window.isCallClosing) return; // double check

                if (data.active) {
                    currentRoom = data.room_name;
                    
                    // Show a toast or update a banner that a call is incoming
                    const callAlertEl = document.getElementById("incoming-call-box");
                    const jitsiContainer = document.getElementById("jitsi-container");
                    
                    // Don't show the banner if they are ALREADY in the call viewing the container
                    if (callAlertEl && callAlertEl.style.display !== "block" && jitsiContainer.style.display !== "block") {
                        callAlertEl.style.display = "block";
                        console.log("Incoming call detected for room:", currentRoom);
                    }
                    
                    const joinBtn = document.getElementById("joinVivaBtn");
                    if (joinBtn) {
                        joinBtn.setAttribute("onclick", `startCall('${data.room_name}')`);
                    }

                } else {
                    // Call ended from professor side
                    const callAlertEl = document.getElementById("incoming-call-box");
                    const jitsiContainer = document.getElementById("jitsi-container");
                    
                    if (callAlertEl) callAlertEl.style.display = "none";
                    if (jitsiContainer) {
                        jitsiContainer.style.display = "none";
                        jitsiContainer.innerHTML = ''; // Kill iframe
                    }
                    
                    if (typeof currentStudentJitsiApi !== 'undefined' && currentStudentJitsiApi !== null) {
                        currentStudentJitsiApi.dispose();
                        currentStudentJitsiApi = null;
                    }
                    currentRoom = null;
                }
            })
            .catch(err => {
                console.error("Error checking call status:", err);
            });
    }

    // Ping the backend every 5 seconds to see if the Professor started a Viva Session
    setInterval(checkActiveCall, 5000);
});


