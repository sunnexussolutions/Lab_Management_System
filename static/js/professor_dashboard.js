document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const main = document.querySelector("main");
  const profileIcon = document.getElementById("profileIcon");
  const sidebarOverlay = document.getElementById("sidebarOverlay");

  // Toggle sidebar
  profileIcon.addEventListener("click", () => {
    sidebar.classList.toggle("show");
    main.classList.toggle("shifted");
    sidebarOverlay.classList.toggle("show");
  });

  document.getElementById("closeSidebar").addEventListener("click", () => {
    sidebar.classList.remove("show");
    main.classList.remove("shifted");
    sidebarOverlay.classList.remove("show");
  });

  sidebarOverlay.addEventListener("click", () => {
    sidebar.classList.remove("show");
    main.classList.remove("shifted");
    sidebarOverlay.classList.remove("show");
  });

  document.addEventListener("click", (e) => {
    // Close sidebar if clicking outside
    if (
      !sidebar.contains(e.target) &&
      !profileIcon.contains(e.target) &&
      !e.target.closest(".sidebar") &&
      !e.target.closest(".modal") // Don't close sidebar if clicking inside a modal
    ) {
      sidebar.classList.remove("show");
      main.classList.remove("shifted");
      sidebarOverlay.classList.remove("show");
    }
  });

  // Close sidebar when clicking any navigation link inside it
  document.querySelectorAll(".sidebar a").forEach((link) => {
    link.addEventListener("click", () => {
      sidebar.classList.remove("show");
      main.classList.remove("shifted");
      sidebarOverlay.classList.remove("show");
    });
  });

  // Edit Profile Modal
  const editProfileModal = new bootstrap.Modal(
    document.getElementById("editProfileModal")
  );
  document
    .getElementById("editProfileBtn")
    .addEventListener("click", () => editProfileModal.show());

  document
    .getElementById("profilePicInput")
    ?.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) {
        document.getElementById("previewPic").src = URL.createObjectURL(file);
        document.getElementById("profileImageDisplay").src = URL.createObjectURL(file);
      }
    });

  // Handle profile form submission
  document.getElementById("editProfileForm")?.addEventListener("submit", (e) => {
    // Form will auto-submit via Django backend
  });

  // Enter Marks Flow
  const selectBatchModal = new bootstrap.Modal(
    document.getElementById("selectDivisionModal")
  );
  const enterMarksModal = new bootstrap.Modal(
    document.getElementById("enterMarksModal")
  );

  async function parseJsonOrThrow(response) {
    const text = await response.text();
    let data;

    try {
      data = JSON.parse(text);
    } catch (err) {
      if (response.redirected && response.url.includes("/login/")) {
        throw new Error("Your session expired. Please login again.");
      }
      const snippet = (text || "").replace(/\s+/g, " ").trim().slice(0, 180);
      throw new Error(`Unexpected server response (HTTP ${response.status}): ${snippet || "empty body"}`);
    }

    if (!response.ok) {
      throw new Error(data.error || data.message || `Request failed (HTTP ${response.status})`);
    }

    return data;
  }

  async function downloadExcelOrAlert(url, fallbackFilename) {
    try {
      const response = await fetch(url, {
        method: "GET",
        credentials: "same-origin"
      });

      if (!response.ok) {
        const bodyText = await response.text();
        const snippet = (bodyText || "").replace(/\s+/g, " ").trim().slice(0, 200);
        throw new Error(snippet || `Request failed (HTTP ${response.status})`);
      }

      const blob = await response.blob();
      const objectUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = fallbackFilename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
    } catch (error) {
      console.error("Export download failed:", error);
      alert("Export failed: " + (error.message || "Unable to download file."));
    }
  }

  document.getElementById("enterMarksBtn")?.addEventListener("click", (e) => {
    e.preventDefault();
    selectBatchModal.show();
  });

  // Enter Marks Modal Logic
  const marksLabSelect = document.getElementById("marksLabSelect");
  const marksDivisionSection = document.getElementById("marksDivisionSection");
  const divisionForMarks = document.getElementById("divisionForMarks");

  if (marksLabSelect && marksDivisionSection && divisionForMarks) {
    marksLabSelect.addEventListener("change", () => {
      if (marksLabSelect.value) {
        marksDivisionSection.style.display = "block";
        divisionForMarks.value = ""; // Reset
      } else {
        marksDivisionSection.style.display = "none";
      }
    });
  }

  document.getElementById("showMarksTableBtn").addEventListener("click", () => {
    const labId = marksLabSelect.value;
    const batch = divisionForMarks.value;
    console.log(`DEBUG: Showing marks table for Lab ${labId}, Batch ${batch}`);
    if (!labId) {
      alert("Please select a lab first!");
      return;
    }
    if (!batch) {
      alert("Please select a division first!");
      return;
    }

    const divisionName = divisionForMarks.options[divisionForMarks.selectedIndex].text;

    document.getElementById("selectedDivision").textContent = divisionName;
    document.getElementById("selectedDivisionHeader").textContent = divisionName;
    document.getElementById("selectedDivision").dataset.division = batch;
    document.getElementById("selectedDivision").dataset.labId = labId; // Store labId
    
    populateMarksTable(labId, batch);
    selectBatchModal.hide();
    enterMarksModal.show();
  });

  // Download Marks Excel
  document.getElementById("downloadMarksExcelBtn").addEventListener("click", () => {
    const division = (document.getElementById("selectedDivision").dataset.division || "").trim();
    const labId = (document.getElementById("selectedDivision").dataset.labId || "").trim();
    if (!division || !labId) {
      alert("Missing division or lab information!");
      return;
    }

    const params = new URLSearchParams({ division, lab_id: labId });
    const url = `/professor/download-marks-excel/?${params.toString()}`;
    downloadExcelOrAlert(url, `marks_${division}_lab_${labId}.xlsx`);
  });

  // Download Total Marks Excel (totals only, no breakdown)
  document.getElementById("downloadTotalMarksBtn").addEventListener("click", () => {
    const division = (document.getElementById("selectedDivision").dataset.division || "").trim();
    const labId = (document.getElementById("selectedDivision").dataset.labId || "").trim();
    if (!division || !labId) {
      alert("Missing division or lab information!");
      return;
    }

    const params = new URLSearchParams({ division, lab_id: labId });
    const url = `/professor/download-total-marks-excel/?${params.toString()}`;
    downloadExcelOrAlert(url, `total_marks_${division}_lab_${labId}.xlsx`);
  });

  // Save Marks Function
  window.saveMarks = function () {
    const division = document.getElementById("selectedDivision").dataset.division;
    const labId = document.getElementById("selectedDivision").dataset.labId;
    if (!division || !labId) {
      alert("Missing division or lab information!");
      return;
    }

    const marksData = collectMarksData();
    if (marksData.length === 0) {
      alert("No marks data to save!");
      return;
    }

    fetch("/professor/save-marks/", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
      },
      body: JSON.stringify({
        division: division,
        lab_id: labId,
        marks_data: marksData
      })
    })
      .then(parseJsonOrThrow)
      .then(data => {
        if (data.success) {
          alert("Marks saved successfully!");
        } else {
          alert("Error: " + data.error);
        }
      })
      .catch(error => {
        console.error("Error:", error);
        alert("Error while saving marks: " + (error.message || "Unknown error"));
      });
  };

  // Send Report to Email Function
  window.sendReportToEmail = function () {
    const division = document.getElementById("selectedDivision").dataset.division;
    const labId = document.getElementById("selectedDivision").dataset.labId;
    if (!division || !labId) {
      alert("Missing division or lab information!");
      return;
    }

    const btn = document.getElementById("reportToEmailBtn");
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="bi bi-hourglass me-2"></i>Sending...';
    btn.disabled = true;

    fetch("/professor/send-marks-report/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
      },
      body: JSON.stringify({
        division: division,
        lab_id: labId
      })
    })
      .then(response => response.json())
      .then(data => {
        if (data.success) {
          alert("Report sent to your email successfully!");
        } else {
          alert("Error: " + data.error);
        }
      })
      .catch(error => {
        console.error("Error:", error);
        alert("An error occurred while sending the report.");
      })
      .finally(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
      });
  };

  function collectMarksData() {
    const marksData = [];
    const rows = document.querySelectorAll("#marksTableBody tr");

    rows.forEach(row => {
      const studentPrn = row.querySelector('.exp-viva').getAttribute('data-student');
      const studentData = {
        prn: studentPrn,
        experiments: []
      };

      for (let exp = 1; exp <= 10; exp++) {
        const viva = parseFloat(row.querySelector(`.exp-viva[data-exp="${exp}"]`).value) || 0;
        const marks = parseFloat(row.querySelector(`.exp-marks[data-exp="${exp}"]`).value) || 0;
        const writing = parseFloat(row.querySelector(`.exp-writing[data-exp="${exp}"]`).value) || 0;

        studentData.experiments.push({
          experiment_number: exp,
          viva_marks: viva,
          experiment_marks: marks,
          writeup_marks: writing
        });
      }

      marksData.push(studentData);
    });

    return marksData;
  }

  function populateMarksTable(labId, division) {
    const tbody = document.getElementById("marksTableBody");
    const thead = document.getElementById("marksTableHead");
    tbody.innerHTML = '<tr><td colspan="43" class="text-center py-4"><i class="bi bi-hourglass me-2"></i>Loading students...</td></tr>';

    console.log(`DEBUG: Fetching students for Division ${division}, Lab ${labId}`);
    fetch(`/professor/get-students-for-division/?division=${division}&lab_id=${labId}`)
      .then(response => response.json())
      .then(data => {
        console.log(`DEBUG: Received ${data.students ? data.students.length : 0} students`);
        tbody.innerHTML = "";
        populateMarksTableWithData(data.students, division);
      })
      .catch(error => {
        console.error("Error fetching students:", error);
        tbody.innerHTML = '<tr><td colspan="43" class="text-center text-danger py-4">Error loading students. Please try again.</td></tr>';
      });
  }

  function populateMarksTableWithData(students, division) {
    const tbody = document.getElementById("marksTableBody");
    const thead = document.getElementById("marksTableHead");

    let headHTML = `
      <tr>
        <th>Student Name</th>
        <th>PRN</th>
    `;
    for (let exp = 1; exp <= 10; exp++) {
      headHTML += `
        <th>Exp ${exp} Viva (5)</th>
        <th>Exp ${exp} Exp Marks (5)</th>
        <th>Exp ${exp} Writing (5)</th>
        <th>Exp ${exp} Total (15)</th>
      `;
    }
    headHTML += `
        <th>Total Marks</th>
        <th>Average Marks</th>
      </tr>
    `;
    thead.innerHTML = headHTML;

    if (!students || students.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="44" class="text-center text-muted py-4">No students found for this division.</td></tr>';
      document.getElementById("classAvgSection").classList.add("d-none");
      return;
    }

    students.forEach((student) => {
      const tr = document.createElement("tr");
      let html = `<td>${student.name}</td><td>${student.prn}</td>`;

      for (let exp = 1; exp <= 10; exp++) {
        // Ensure we check both number and string keys from the marks object
        const expMarks = (student.marks && (student.marks[exp] || student.marks[exp.toString()])) || { viva: 0, marks: 0, writing: 0 };
        html += `
          <td><input type="number" id="viva_${student.prn}_${exp}" name="viva_${student.prn}_${exp}" value="${expMarks.viva}" class="form-control exp-viva" data-exp="${exp}" data-student="${student.prn}"></td>
          <td><input type="number" id="marks_${student.prn}_${exp}" name="marks_${student.prn}_${exp}" value="${expMarks.marks}" class="form-control exp-marks" data-exp="${exp}" data-student="${student.prn}"></td>
          <td><input type="number" id="writing_${student.prn}_${exp}" name="writing_${student.prn}_${exp}" value="${expMarks.writing}" class="form-control exp-writing" data-exp="${exp}" data-student="${student.prn}"></td>
          <td><input type="number" id="total_${student.prn}_${exp}" name="total_${student.prn}_${exp}" value="0" class="form-control exp-total" readonly data-student="${student.prn}"></td>
        `;
      }

      html += `
        <td><input type="number" id="grand_total_${student.prn}" name="grand_total_${student.prn}" value="0" class="form-control total-marks" readonly data-student="${student.prn}"></td>
        <td><input type="number" id="avg_${student.prn}" name="avg_${student.prn}" value="0" class="form-control avg-marks" readonly data-student="${student.prn}"></td>
      `;
      tr.innerHTML = html;
      tbody.appendChild(tr);
      attachRowCalculations(tr);
    });

    document.getElementById("classAvgSection").classList.remove("d-none");
    document.getElementById("classOverallAvg").textContent = "0.00";
  }

  function attachRowCalculations(tr) {
    const studentPrn = tr.querySelector('td:nth-child(2)').textContent;
    const vivaInputs = tr.querySelectorAll(".exp-viva");
    const marksInputs = tr.querySelectorAll(".exp-marks");
    const writingInputs = tr.querySelectorAll(".exp-writing");
    const expTotals = tr.querySelectorAll(".exp-total");
    const totalMarksInput = tr.querySelector(".total-marks");
    const avgMarksInput = tr.querySelector(".avg-marks");

    const calculateRow = () => {
      console.log(`DEBUG: [${studentPrn}] Recalculating totals...`);
      let grandTotal = 0;
      
      for (let i = 0; i < 10; i++) {
        // More robust parsing to ensure we handle any empty strings or invalid values
        const v = parseFloat(vivaInputs[i].value) || 0;
        const m = parseFloat(marksInputs[i].value) || 0;
        const w = parseFloat(writingInputs[i].value) || 0;
        
        const rowExpTotal = v + m + w;
        
        if (expTotals[i]) {
          expTotals[i].value = rowExpTotal.toFixed(1);
          console.log(`DEBUG: [${studentPrn}] Exp ${i+1} Total set to: ${expTotals[i].value}`);
        } else {
          console.warn(`DEBUG: [${studentPrn}] Missing exp-total input for index ${i}`);
        }
        
        grandTotal += rowExpTotal;
      }

      if (totalMarksInput) {
        totalMarksInput.value = grandTotal.toFixed(1);
      }
      if (avgMarksInput) {
        avgMarksInput.value = (grandTotal / 10).toFixed(2);
      }

      console.log(`DEBUG: [${studentPrn}] Grand Total: ${grandTotal.toFixed(1)}, Avg: ${(grandTotal / 10).toFixed(2)}`);
      calculateClassOverallAverage();
    };

    const allInputs = [...vivaInputs, ...marksInputs, ...writingInputs];

    allInputs.forEach((input) => {
      input.addEventListener("input", function() {
        console.log(`DEBUG: [${studentPrn}] Input detected on ${this.className} for exp ${this.dataset.exp}: ${this.value}`);
        
        // Validation: Max 5 marks
        let valString = this.value;
        if (valString !== "") {
          let val = parseFloat(valString);
          if (!isNaN(val)) {
            if (val > 5) {
              console.log(`DEBUG: [${studentPrn}] Capping value from ${val} to 5`);
              alert("Maximum marks allowed is 5. Resetting to 5.");
              this.value = 5;
            } else if (val < 0) {
              console.log(`DEBUG: [${studentPrn}] Setting negative value ${val} to 0`);
              this.value = 0;
            }
          }
        }
        calculateRow();
      });
    });

    // Initial calculation based on loaded/default values
    console.log(`DEBUG: [${studentPrn}] Triggering initial calculation...`);
    calculateRow();
  }

  function calculateClassOverallAverage() {
    const avgInputs = document.querySelectorAll("#marksTableBody .avg-marks");
    let sum = 0,
      count = 0;
    avgInputs.forEach((inp) => {
      const val = parseFloat(inp.value) || 0;
      sum += val;
      count++;
    });
    document.getElementById("classOverallAvg").textContent =
      count > 0 ? (sum / count).toFixed(2) : "0.00";
  }

  // Excel Upload Dynamic Visibility Logic
  const uploadLabSelect = document.getElementById("uploadLabSelect");
  const uploadDivisionSelect = document.getElementById("uploadDivisionSelect");
  const divisionSelectionSection = document.getElementById("divisionSelectionSection");
  const uploadSection = document.getElementById("uploadSection");

  const checkUploadStatus = (labId, division) => {
    if (!labId || !division) return;
    console.log(`DEBUG: Checking upload status for Lab ${labId}, Division ${division}`);
    fetch(`/professor/check-upload-status/?lab_id=${labId}&division=${encodeURIComponent(division)}`)
      .then(response => response.json())
      .then(data => {
        console.log(`DEBUG: Upload exists: ${data.exists}`, data);
        const statusContainer = document.getElementById("uploadStatusContainer");
        const uploadSection = document.getElementById("uploadSection");
        const filenameSpan = document.getElementById("uploadedFilename");
        const uploadedAtSpan = document.getElementById("uploadedAt");

        if (data.exists) {
          if (statusContainer) statusContainer.style.display = "block";
          if (uploadSection) uploadSection.style.display = "none";
          if (filenameSpan) filenameSpan.textContent = data.filename;
          if (uploadedAtSpan) uploadedAtSpan.textContent = data.uploaded_at;
        } else {
          if (statusContainer) statusContainer.style.display = "none";
          if (uploadSection) uploadSection.style.display = "block";
        }
      })
      .catch(err => console.error("Error checking upload status:", err));
  };

  const updateVisibility = () => {
    const statusContainer = document.getElementById("uploadStatusContainer");
    if (uploadLabSelect && uploadLabSelect.value) {
      if (divisionSelectionSection) divisionSelectionSection.style.display = "block";
      if (uploadDivisionSelect && uploadDivisionSelect.value) {
        checkUploadStatus(uploadLabSelect.value, uploadDivisionSelect.value);
      } else {
        if (uploadSection) uploadSection.style.display = "none";
        if (statusContainer) statusContainer.style.display = "none";
      }
    } else {
      if (divisionSelectionSection) divisionSelectionSection.style.display = "none";
      if (uploadSection) uploadSection.style.display = "none";
      if (statusContainer) statusContainer.style.display = "none";
    }
  };

  if (uploadLabSelect && divisionSelectionSection && uploadSection) {
    // Functions moved to outer scope

    document.getElementById("deleteUploadBtn").addEventListener("click", () => {
      const labId = uploadLabSelect.value;
      const division = uploadDivisionSelect.value;

      if (!confirm(`Are you sure you want to delete the student data for division ${division}? THIS WILL ALSO DELETE ALL MARKS ENTERED FOR THIS DIVISION IN THIS LAB. This action cannot be undone.`)) {
        return;
      }

      const btn = document.getElementById("deleteUploadBtn");
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

      fetch("/professor/delete-upload/", {
        method: "POST",
        body: JSON.stringify({ lab_id: labId, division: division }),
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
        }
      })
      .then(response => response.json())
      .then(data => {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-trash3 me-1"></i>Delete';
        if (data.success) {
          alert(data.message);
          checkUploadStatus(labId, division);
          
          // Clear current tables if they were showing this data
          const marksTableBody = document.getElementById("marksTableBody");
          if (marksTableBody) marksTableBody.innerHTML = "";
          const uploadsTableBody = document.querySelector("#viewUploadsModal tbody");
          if (uploadsTableBody) uploadsTableBody.innerHTML = "";
        } else {
          alert("Error: " + data.error);
        }
      })
      .catch(err => {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-trash3 me-1"></i>Delete';
        console.error("Error deleting upload:", err);
      });
    });
    
    uploadLabSelect.addEventListener("change", () => {
      uploadDivisionSelect.value = ""; // Reset division when lab changes
      updateVisibility();
    });
    
    uploadDivisionSelect.addEventListener("change", updateVisibility);
    
    // Initial update
    updateVisibility();
  }

  // Excel Upload Submission
  document.getElementById("uploadExcelBtn").addEventListener("click", () => {
    const fileInput = document.getElementById("studentExcelFile");
    const labSelect = document.getElementById("uploadLabSelect");
    const divisionSelect = document.getElementById("uploadDivisionSelect");
    
    if (!fileInput.files.length) {
      alert("Please select a file to upload.");
      return;
    }
    
    if (!labSelect.value) {
      alert("Please select a lab.");
      return;
    }

    if (!divisionSelect.value) {
      alert("Please select a division.");
      return;
    }

    const formData = new FormData();
    formData.append("excel_file", fileInput.files[0]);
    formData.append("division", divisionSelect.value);
    formData.append("lab_id", labSelect.value);

    // Disable button during upload
    const btn = document.getElementById("uploadExcelBtn");
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="spinner-border spinner-border-sm me-2"></i>Uploading...';
    btn.disabled = true;

    fetch("/professor/upload-student-excel/", {
      method: "POST",
      body: formData,
      headers: {
        "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
      }
    })
    .then(async (response) => {
      const contentType = response.headers.get("content-type") || "";

      if (contentType.includes("application/json")) {
        const data = await response.json();
        if (!response.ok || !data.success) {
          throw new Error(data.error || `Upload failed (HTTP ${response.status}).`);
        }
        return data;
      }

      const bodyText = await response.text();
      throw new Error(
        `Upload failed (HTTP ${response.status}). ${bodyText.slice(0, 200).replace(/\\s+/g, " ")}`
      );
    })
    .then((data) => {
      alert(data.message);
      checkUploadStatus(labSelect.value, divisionSelect.value);
      fileInput.value = ""; // Clear file input
      // Refresh page to update division dropdowns if a new one was added to professor's list
      if (data.division_added) {
        window.location.reload();
      } else {
        document.getElementById("uploadStudentExcelModal").querySelector(".btn-close").click();
      }
    })
    .catch(error => {
      console.error("Error uploading file:", error);
      alert(error.message || "An error occurred during upload.");
    })
    .finally(() => {
      btn.innerHTML = originalText;
      btn.disabled = false;
    });
  });

  // Attendance Feature Flow
  const enterAttendanceBtn = document.getElementById("enterAttendanceBtn");
  const selectAttendanceModal = new bootstrap.Modal(document.getElementById("selectAttendanceModal"));
  const enterAttendanceModal = new bootstrap.Modal(document.getElementById("enterAttendanceModal"));
  
  const attendanceLabSelect = document.getElementById("attendanceLabSelect");
  const attendanceDivisionSelect = document.getElementById("attendanceDivisionSelect");
  const attendanceDivisionSection = document.getElementById("attendanceDivisionSection");
  const attendanceDateSection = document.getElementById("attendanceDateSection");
  const attendanceDateInput = document.getElementById("attendanceDateInput");
  const showAttendanceTableBtn = document.getElementById("showAttendanceTableBtn");

  if (enterAttendanceBtn) {
    enterAttendanceBtn.addEventListener("click", (e) => {
      e.preventDefault();
      selectAttendanceModal.show();
    });
  }

  if (attendanceLabSelect) {
    attendanceLabSelect.addEventListener("change", () => {
      if (attendanceLabSelect.value) {
        attendanceDivisionSection.style.display = "block";
      } else {
        attendanceDivisionSection.style.display = "none";
        attendanceDateSection.style.display = "none";
      }
    });
  }

  const togglePastDatesBtn = document.getElementById("togglePastDatesBtn");
  if (togglePastDatesBtn) {
    togglePastDatesBtn.addEventListener("click", () => {
      const isViewingPrevious = togglePastDatesBtn.classList.contains("active");
      const today = attendanceDateInput.dataset.today;

      if (isViewingPrevious) {
        // Revert back to today only
        attendanceDateInput.min = today;
        attendanceDateInput.max = today;
        attendanceDateInput.value = today;
        togglePastDatesBtn.classList.remove("active");
        togglePastDatesBtn.textContent = "View Previous";
        togglePastDatesBtn.classList.replace("btn-primary", "btn-outline-primary");
      } else {
        // Allow past dates
        attendanceDateInput.removeAttribute("min");
        attendanceDateInput.max = today; // No future dates allowed
        togglePastDatesBtn.classList.add("active");
        togglePastDatesBtn.textContent = "Back to Today";
        togglePastDatesBtn.classList.replace("btn-outline-primary", "btn-primary");
      }
    });
  }

  if (attendanceDivisionSelect) {
    attendanceDivisionSelect.addEventListener("change", () => {
      if (attendanceDivisionSelect.value) {
        attendanceDateSection.style.display = "block";
      } else {
        attendanceDateSection.style.display = "none";
      }
    });
  }

  if (showAttendanceTableBtn) {
    showAttendanceTableBtn.addEventListener("click", () => {
      const labId = attendanceLabSelect.value;
      const division = attendanceDivisionSelect.value;
      const date = attendanceDateInput.value;

      if (!labId || !division || !date) {
        alert("Please select Lab, Division, and Date.");
        return;
      }

      // Populate Header Info
      const labName = attendanceLabSelect.options[attendanceLabSelect.selectedIndex].text;
      document.getElementById("attendanceHeaderInfo").textContent = `| ${labName} | Div: ${division} | Date: ${date}`;
      
      selectAttendanceModal.hide();
      enterAttendanceModal.show();
      loadAttendanceTable(labId, division, date);
    });
  }

  function loadAttendanceTable(labId, division, date) {
    const tableBody = document.getElementById("attendanceTableBody");
    const summaryText = document.getElementById("attendanceSummaryText");
    tableBody.innerHTML = `<tr><td colspan="5" class="text-center py-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Loading students...</p></td></tr>`;
    
    fetch(`/professor/get-students-for-division/?lab_id=${labId}&division=${encodeURIComponent(division)}&date=${date}`)
      .then(response => response.json())
      .then(data => {
        if (data.error) {
          tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">${data.error}</td></tr>`;
          return;
        }

        if (data.students.length === 0) {
          tableBody.innerHTML = `<tr><td colspan="5" class="text-center py-4">No students found for this division and lab.</td></tr>`;
          summaryText.textContent = "0 students found";
          return;
        }

        tableBody.innerHTML = "";
        data.students.forEach((student, index) => {
          const row = document.createElement("tr");
          
          // Determine existing attendance status
          const isPresent = student.attendance === true;
          const isAbsent = student.attendance === false;
          const notMarked = student.attendance === null;

          row.innerHTML = `
            <td class="ps-4 text-muted">${index + 1}</td>
            <td class="text-muted small">${date}</td>
            <td class="fw-medium">${student.name}</td>
            <td class="text-muted small">${student.prn}</td>
            <td class="text-center">
              <div class="form-check d-flex justify-content-center">
                <input class="form-check-input attendance-checkbox present-cb" type="checkbox" 
                       data-student-id="${student.id}" value="present" ${isPresent ? "checked" : ""}>
              </div>
            </td>
            <td class="text-center">
              <div class="form-check d-flex justify-content-center">
                <input class="form-check-input attendance-checkbox absent-cb" type="checkbox" 
                       data-student-id="${student.id}" value="absent" ${isAbsent ? "checked" : ""}>
              </div>
            </td>
          `;
          tableBody.appendChild(row);
        });

        summaryText.textContent = `${data.students.length} students loaded.`;
        setupAttendanceCheckboxLogic();
      })
      .catch(err => {
        console.error("Error loading attendance:", err);
        tableBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">Failed to load students.</td></tr>`;
      });
  }

  function setupAttendanceCheckboxLogic() {
    const checkboxes = document.querySelectorAll(".attendance-checkbox");
    checkboxes.forEach(cb => {
      cb.addEventListener("change", function() {
        const studentId = this.dataset.studentId;
        const isPresentCb = this.classList.contains("present-cb");
        
        if (this.checked) {
          // Uncheck the other one if this one is checked
          const otherCb = document.querySelector(`.attendance-checkbox[data-student-id="${studentId}"].${isPresentCb ? "absent-cb" : "present-cb"}`);
          if (otherCb) otherCb.checked = false;
        }
      });
    });
  }

  const saveAttendanceBtn = document.getElementById("saveAttendanceBtn");
  const attendanceConfirmModal = new bootstrap.Modal(document.getElementById("attendanceConfirmModal"));
  const confirmSaveAttendanceBtn = document.getElementById("confirmSaveAttendanceBtn");
  const editAttendanceBtn = document.getElementById("editAttendanceBtn");

  // Keep pending attendance data available between Modals
  let pendingAttendanceData = null;

  if (saveAttendanceBtn) {
    saveAttendanceBtn.addEventListener("click", () => {
      const labId = attendanceLabSelect.value;
      const division = attendanceDivisionSelect.value;
      const date = attendanceDateInput.value;
      
      const attendanceData = [];
      const presentNames = [];
      const absentNames = [];
      
      const students = [...new Set([...document.querySelectorAll(".attendance-checkbox")].map(cb => cb.dataset.studentId))];
      
      students.forEach(studentId => {
        const presentCb = document.querySelector(`.attendance-checkbox[data-student-id="${studentId}"].present-cb`);
        const absentCb = document.querySelector(`.attendance-checkbox[data-student-id="${studentId}"].absent-cb`);
        const studentRow = presentCb.closest("tr");
        const studentName = studentRow.querySelector("td:nth-child(3)").textContent;
        const studentPrn = studentRow.querySelector("td:nth-child(4)").textContent;
        
        let displayStr = `<div class="d-flex justify-content-between align-items-center"><span class="fw-medium">${studentName}</span><small class="text-muted ms-auto">${studentPrn}</small>`;
        
        if (presentCb.checked) {
          attendanceData.push({ student_id: studentId, present: true });
          presentNames.push(displayStr + `</div>`);
        } else if (absentCb.checked) {
          attendanceData.push({ student_id: studentId, present: false });
          absentNames.push(displayStr + `</div>`);
        } else {
          // Unmarked students automatically default to absent per instructions
          attendanceData.push({ student_id: studentId, present: false });
          absentNames.push(displayStr + `<span class="badge bg-warning text-dark ms-2" style="font-size: 0.65rem">Auto</span></div>`);
        }
      });

      if (attendanceData.length === 0) {
        alert("No attendance marked to process.");
        return;
      }

      // Populate Confirmation Modal Data
      document.getElementById("presentCountBadge").textContent = presentNames.length;
      document.getElementById("absentCountBadge").textContent = absentNames.length;
      
      const presentList = document.getElementById("presentStudentsList");
      presentList.innerHTML = presentNames.length > 0 ? 
        presentNames.map(name => `<li class="list-group-item px-3 py-2 border-0 border-bottom border-light">${name}</li>`).join('') :
        `<li class="list-group-item text-muted fst-italic py-3 text-center border-0">None marked present</li>`;
        
      const absentList = document.getElementById("absentStudentsList");
      absentList.innerHTML = absentNames.length > 0 ? 
        absentNames.map(name => `<li class="list-group-item px-3 py-2 border-0 border-bottom border-light">${name}</li>`).join('') :
        `<li class="list-group-item text-muted fst-italic py-3 text-center border-0">None marked absent</li>`;

      // Store data logic for final submission
      pendingAttendanceData = {
        lab_id: labId,
        division: division,
        date: date,
        attendance: attendanceData
      };

      // Switch Modals
      enterAttendanceModal.hide();
      attendanceConfirmModal.show();
    });
  }

  // Edit Button - Returns to the main entry modal
  if (editAttendanceBtn) {
    editAttendanceBtn.addEventListener("click", () => {
      attendanceConfirmModal.hide();
      enterAttendanceModal.show();
    });
  }

  // Real Database Save Button
  if (confirmSaveAttendanceBtn) {
    confirmSaveAttendanceBtn.addEventListener("click", () => {
      if (!pendingAttendanceData) return;

      confirmSaveAttendanceBtn.disabled = true;
      confirmSaveAttendanceBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span>Saving...`;

      fetch("/professor/save-attendance/", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": document.querySelector('[name=csrfmiddlewaretoken]').value
        },
        body: JSON.stringify(pendingAttendanceData)
      })
      .then(parseJsonOrThrow)
      .then(data => {
        if (data.success) {
          alert(data.message);
          attendanceConfirmModal.hide();
          selectAttendanceModal.show();
        } else {
          alert("Error saving attendance: " + (data.error || "Unknown error"));
        }
      })
      .catch(err => {
        console.error("Error saving attendance:", err);
        alert("Error while saving attendance: " + (err.message || "Unknown error"));
      })
      .finally(() => {
        confirmSaveAttendanceBtn.disabled = false;
        confirmSaveAttendanceBtn.innerHTML = `<i class="bi bi-check2-all me-2"></i>Confirm & Save`;
        pendingAttendanceData = null; // Clear pending data
      });
    });
  }

  // View Submissions/Uploads Flow
  const selectSubjectModalEl = document.getElementById("selectSubjectModal");
  const selectSubjectModal = new bootstrap.Modal(selectSubjectModalEl);
  const viewUploadsModal = new bootstrap.Modal(document.getElementById("viewUploadsModal"));

  const uploadsLabSelect = document.getElementById("uploadsLabSelect");
  const uploadsDivisionSection = document.getElementById("uploadsDivisionSection");
  const uploadsDivisionSelect = document.getElementById("uploadsDivisionSelect");

  if (uploadsLabSelect && uploadsDivisionSection) {
    uploadsLabSelect.addEventListener("change", () => {
      if (uploadsLabSelect.value) {
        uploadsDivisionSection.style.display = "block";
        uploadsDivisionSelect.value = ""; // Reset
      } else {
        uploadsDivisionSection.style.display = "none";
      }
    });
  }

  document.getElementById("viewUploadsNavigationBtn").addEventListener("click", (e) => {
    e.preventDefault();
    selectSubjectModal.show();
  });

  document.getElementById("fetchUploadsBtn").addEventListener("click", () => {
    const labId = uploadsLabSelect.value;
    const divisionId = uploadsDivisionSelect.value;

    if (!labId) {
      alert("Please select a lab first.");
      return;
    }
    if (!divisionId) {
      alert("Please select a division first.");
      return;
    }

    populateUploadsTable(labId, divisionId);
    selectSubjectModal.hide();
    viewUploadsModal.show();
  });

  function populateUploadsTable(labId, division) {
    const tbody = document.getElementById("uploadsTableBody");
    tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4"><i class="bi bi-hourglass me-2"></i>Loading submissions...</td></tr>';

    // Fetch real submissions from database
    fetch(`/professor/get-submissions-for-division/?division=${division}&lab_id=${labId}`)
      .then(response => response.json())
      .then(data => {
        tbody.innerHTML = "";

        if (!data.submissions || data.submissions.length === 0) {
          tbody.innerHTML =
            '<tr><td colspan="7" class="text-center text-muted py-4">No submissions found for this division.</td></tr>';
          return;
        }
        populateUploadsTableWithData(data.submissions);
      })
      .catch(error => {
        console.error("Error fetching submissions:", error);
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger py-4">Error loading submissions. Please try again.</td></tr>';
      });
  }

  function populateUploadsTableWithData(submissions) {
    const tbody = document.getElementById("uploadsTableBody");

    if (submissions.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6" class="text-center text-muted py-4">No submissions found for this division.</td></tr>';
      return;
    }

    submissions.forEach((submission, index) => {
      const codeUrl = submission.code_screenshot || "";
      const outputUrl = submission.output_screenshot || "";
      const codeCell = codeUrl
        ? `<a href="${codeUrl}" target="_blank" rel="noopener" class="btn btn-sm btn-outline-primary">
            <i class="bi bi-eye"></i> View Code
          </a>`
        : `<span class="text-muted small">Missing</span>`;
      const outputCell = outputUrl
        ? `<a href="${outputUrl}" target="_blank" rel="noopener" class="btn btn-sm btn-outline-success">
            <i class="bi bi-eye"></i> View Output
          </a>`
        : `<span class="text-muted small">Missing</span>`;

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${index + 1}</td>
        <td>${submission.student_name}</td>
        <td>${submission.student_prn}</td>
        <td>${submission.experiment_name || submission.experiment_title || '???'}</td>
        <td class="text-center">
          ${codeCell}
        </td>
        <td class="text-center">
          ${outputCell}
        </td>
        <td class="text-center">
          <button class="btn btn-sm btn-primary evaluate-btn" data-submission-id="${submission.id}">
            <i class="bi bi-check-circle"></i> Evaluate
          </button>
        </td>
      `;
      tbody.appendChild(tr);
});

    // Add event listeners for evaluate buttons
    document.querySelectorAll('.evaluate-btn').forEach(btn => {
      btn.addEventListener('click', function () {
        const submissionId = this.getAttribute('data-submission-id');
        evaluateSubmission(submissionId);
      });
    });
  }

  function evaluateSubmission(submissionId) {
    // Open evaluation modal or redirect to evaluation page
    window.location.href = `/professor/evaluate-submission/${submissionId}/`;
  }

  window.handleUpload = (type) => alert(`${type} uploaded successfully!`);

  // ─── Lab Resource (Syllabus / Manual) Management ────────────────────────

  function getCsrfToken() {
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1];
    return cookieValue || '';
  }

  function updateResourceUI(type, data) {
    const statusArea  = document.getElementById(`${type}StatusArea`);
    const uploadArea  = document.getElementById(`${type}UploadArea`);
    const fileNameEl  = document.getElementById(`${type}FileName`);
    const viewBtn     = document.getElementById(`view${type.charAt(0).toUpperCase() + type.slice(1)}Btn`);

    const nameKey = `${type}_name`;
    const urlKey  = `${type}_url`;

    if (data[nameKey]) {
      fileNameEl.textContent = data[nameKey];
      viewBtn.href = data[urlKey];
      statusArea.style.display = 'block';
      uploadArea.style.display = 'none';
    } else {
      statusArea.style.display = 'none';
      uploadArea.style.display = 'block';
    }
  }

  function checkLabResourcesStatus(labId) {
    if (!labId) return;
    fetch(`/professor/check-lab-resources-status/?lab_id=${labId}`)
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          updateResourceUI('syllabus', data);
          updateResourceUI('manual', data);
        }
      })
      .catch(err => console.error('Error checking lab resources:', err));
  }

  const syllabusLabSelect = document.getElementById('syllabusLabSelect');
  const manualLabSelect   = document.getElementById('manualLabSelect');

  if (syllabusLabSelect) {
    syllabusLabSelect.addEventListener('change', () => {
      const labId = syllabusLabSelect.value;
      document.getElementById('syllabusStatusArea').style.display = 'none';
      document.getElementById('syllabusUploadArea').style.display = 'none';
      if (labId) {
        // Sync manual select to same lab for convenience
        if (manualLabSelect) manualLabSelect.value = labId;
        checkLabResourcesStatus(labId);
      }
    });
  }

  if (manualLabSelect) {
    manualLabSelect.addEventListener('change', () => {
      const labId = manualLabSelect.value;
      document.getElementById('manualStatusArea').style.display = 'none';
      document.getElementById('manualUploadArea').style.display = 'none';
      if (labId) {
        if (syllabusLabSelect) syllabusLabSelect.value = labId;
        checkLabResourcesStatus(labId);
      }
    });
  }

  window.handleResourceUpload = (type) => {
    const labId = type === 'syllabus'
      ? document.getElementById('syllabusLabSelect').value
      : document.getElementById('manualLabSelect').value;

    if (!labId) { alert('Please select a lab first.'); return; }

    const inputId = type === 'syllabus' ? 'uploadSyllabusInput' : 'uploadManualInput';
    const fileInput = document.getElementById(inputId);
    if (!fileInput.files.length) { alert('Please select a file to upload.'); return; }

    const formData = new FormData();
    formData.append('lab_id', labId);
    formData.append('resource_type', type);
    formData.append('file', fileInput.files[0]);

    fetch('/professor/upload-lab-resource/', {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrfToken() },
      body: formData
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          checkLabResourcesStatus(labId);
          fileInput.value = '';
        } else {
          alert('Upload failed: ' + data.error);
        }
      })
      .catch(err => alert('Error: ' + err));
  };

  window.handleResourceDelete = (type) => {
    const labId = type === 'syllabus'
      ? document.getElementById('syllabusLabSelect').value
      : document.getElementById('manualLabSelect').value;

    if (!labId) { alert('No lab selected.'); return; }
    if (!confirm(`Are you sure you want to delete this ${type}?`)) return;

    fetch('/professor/delete-lab-resource/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify({ lab_id: labId, resource_type: type })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          checkLabResourcesStatus(labId);
        } else {
          alert('Delete failed: ' + data.error);
        }
      })
      .catch(err => alert('Error: ' + err));
  };


  // ============================================
  // JITSI LIVE VIVA CALL INTEGRATION
  // ============================================
  let currentJitsiApi = null;

  window.startVivaCall = function(studentId, prn, labId, submissionId) {
    console.log(`DEBUG: Starting Viva call for Student PRN: ${prn}, Lab ID: ${labId}, Submission ID: ${submissionId}`);
    
    const jitsiContainer = document.getElementById('professor-jitsi-container');
    const evaluationIframe = document.getElementById('evaluationIframe');
    
    if (!jitsiContainer || !evaluationIframe) {
      console.error("Jitsi container or evaluation iframe missing from DOM.");
      return;
    }

    // Load the evaluation form into the right-side iframe
    evaluationIframe.src = `/professor/evaluate-submission/${submissionId}/`;

    // Clean up any existing call instance
    if (currentJitsiApi) {
      currentJitsiApi.dispose();
      jitsiContainer.innerHTML = '';
    }

    // Generate a unique room name that the student can predictably join
    const roomName = `LabViva_${prn}_${labId}`;
    console.log(`DEBUG: Joining room: ${roomName}`);
    
    // Store current active call info for cleanup
    window.currentVivaStudentId = studentId;
    window.currentVivaSubmissionId = submissionId;

    // 1. Tell backend to activate the session
    fetch('/professor/toggle-viva-session/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify({
        student_id: studentId,
        is_active: true,
        room_name: roomName
      })
    })
    .then(res => res.json())
    .then(data => {
      if(data.success) {
        // 2. Open the Modal & Jitsi Frame
        const callModal = new bootstrap.Modal(document.getElementById('jitsiCallModal'));
        callModal.show();

        const domain = "meet.jit.si";
        const options = {
          roomName: roomName,
          width: "100%",
          height: "100%",
          parentNode: jitsiContainer,
          userInfo: {
            displayName: "Professor"
          },
          configOverwrite: {
            startWithAudioMuted: false,
            startWithVideoMuted: false
          },
          interfaceConfigOverwrite: {
            SHOW_JITSI_WATERMARK: false
          }
        };

        // mounting the iframe
        setTimeout(() => {
          currentJitsiApi = new JitsiMeetExternalAPI(domain, options);
          
          // Listen for the Professor hanging up
          currentJitsiApi.addListener('videoConferenceLeft', () => {
            console.log("DEBUG: Professor hung up the Viva Call. Closing modal.");
            callModal.hide(); // Triggers the hidden.bs.modal event cleanup
          });
          
          // Listen for evaluation submission from iframe
          const messageListener = function(event) {
            if (event.data && event.data.type === 'EVALUATION_SUBMITTED') {
              console.log("DEBUG: Evaluation submitted from iframe. Closing modal.");
              callModal.hide();
              window.removeEventListener('message', messageListener);
            }
          };
          window.addEventListener('message', messageListener);
          
        }, 300);
      } else {
        alert("Could not activate call session: " + data.error);
      }
    })
    .catch(err => {
      console.error("Error toggling Viva session:", err);
      alert("Error starting the call.");
    });
  };

  // Clean up the Jitsi iframe if the professor closes the modal 
  // (Prevents audio from hanging in the background and ends the student's prompt)
  const jitsiModalEl = document.getElementById('jitsiCallModal');
  if (jitsiModalEl) {
    jitsiModalEl.addEventListener('hidden.bs.modal', function () {
      console.log("DEBUG: Viva Call modal closed. Disposing Jitsi instance and notifying backend.");
      
      // Tell backend the session is over
      if (window.currentVivaStudentId) {
        fetch('/professor/toggle-viva-session/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
          },
          body: JSON.stringify({
            student_id: window.currentVivaStudentId,
            is_active: false
          })
        }).catch(err => console.error(err));
        window.currentVivaStudentId = null;
      }

      // Remove the student's entry from the Pending Vivas list in the DOM
      if (window.currentVivaSubmissionId) {
        const studentCard = document.getElementById(`pending-viva-${window.currentVivaSubmissionId}`);
        if (studentCard) {
          studentCard.remove();
          
          // Update the Pending Count badge
          const pendingCountEl = document.getElementById('pendingCount');
          if (pendingCountEl) {
            let currentCount = parseInt(pendingCountEl.innerText) || 0;
            if (currentCount > 0) {
              pendingCountEl.innerText = currentCount - 1;
            }
          }
        }
        window.currentVivaSubmissionId = null;
      }

      // Kill the iframe
      if (currentJitsiApi) {
        currentJitsiApi.dispose();
        currentJitsiApi = null;
      }
      const jitsiContainer = document.getElementById('professor-jitsi-container');
      if (jitsiContainer) jitsiContainer.innerHTML = '';
      
      const evaluationIframe = document.getElementById('evaluationIframe');
      if (evaluationIframe) evaluationIframe.src = '';
    });
  }

});
