// ===============================
// Role change (all dashboards)
// ===============================
function changeRole(selectElement) {
    const selectedRole = selectElement.value;
    window.location.href = `/?role=${selectedRole}`;
}

// ===============================
// Toast notifications (all roles)
// ===============================
function showToast(msg, type = 'success') {
    const container = document.createElement('div');
    container.className = `toast toast-${type}`;
    container.innerText = msg;
    document.body.appendChild(container);

    setTimeout(() => container.classList.add('show'), 50);

    setTimeout(() => {
        container.classList.remove('show');
        setTimeout(() => container.remove(), 300);
    }, 3000);
}

// ===============================
// Generate report (all roles)
// ===============================
function generateReport() {
    const role = document.querySelector("strong").innerText;
    const language = document.getElementById("language-select").value;

    fetch("/generate_ai_report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ role: role, language: language })
    })
        .then(res => res.json())
        .then(data => {
            document.getElementById("report-output").style.display = "block";
            document.getElementById("timestamp-placeholder").innerText = data.generated_at;
            document.getElementById("report-json").innerText = data.report;

            document.getElementById("export-btn").disabled = false;
        })
        .catch(() => {
            alert("AI report generation failed.");
        });
}

function downloadReportDirectly() {
    const role = document.querySelector("strong").innerText.toLowerCase();
    const language = document.getElementById("language-select").value;
    window.location.href = `/api/generate_report/${role}?language=${language}`;
}

function updateDefectDate(defectId, newDate) {
    if (!newDate) return;

    fetch("/api/update_defect_date", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: defectId, date: newDate })
    })
        .then(res => res.json())
        .then(data => {
            showToast(data.message, data.message.includes("Error") ? 'error' : 'success');
        })
        .catch(() => {
            showToast("Failed to update date.", "error");
        });
}


// ===============================
// Homeowner only: Add remark
// ===============================
function addRemark(defectId) {
    const modal = document.getElementById('remark-modal');
    if (!modal) return; // Safety for other roles

    modal.style.display = 'flex';

    const textarea = document.getElementById('remark-textarea');
    textarea.value = '';
    textarea.style.height = '100px';

    document.getElementById('modal-defect-id').innerText = defectId;

    textarea.oninput = function () {
        this.style.height = '100px';
        this.style.height = Math.min(this.scrollHeight, 300) + 'px';
    };

    document.getElementById('confirm-remark-btn').onclick = function () {
        const note = textarea.value.trim();
        if (!note) {
            showToast('Note cannot be empty', 'error');
            return;
        }

        // Correct ID target
        const remarkBlock = document.getElementById(`remark-${defectId}`);
        if (remarkBlock) {
            remarkBlock.innerText = note;
        }

        showToast(`Note added for defect #${defectId}`, 'success');
        closeRemarkModal();
    };
}

// ===============================
// Close remark modal
// ===============================
function closeRemarkModal() {
    const modal = document.getElementById('remark-modal');
    if (!modal) return;

    modal.style.display = 'none';
    const textarea = document.getElementById('remark-textarea');
    textarea.value = '';
    textarea.style.height = '100px';
}
