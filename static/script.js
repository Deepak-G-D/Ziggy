(() => {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const fileInfo = document.getElementById("fileInfo");
  const generateBtn = document.getElementById("generateBtn");
  const form = document.querySelector("form");
  const progressContainer = document.getElementById("progressContainer");
  const clearBtn = document.getElementById("clearBtn");
  let file = null;

  // Show loading on submit
  form.addEventListener("submit", () => {
    progressContainer.classList.remove("hidden");
  });

  // Click
  dropzone.addEventListener("click", () => fileInput.click());

  // Keyboard
  dropzone.addEventListener("keydown", (e) => {
    if (e.key === "Enter") fileInput.click();
  });

  // Select
  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
  });

  // Drag
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("dragover");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");

    const droppedFile = e.dataTransfer.files[0];
    if (!droppedFile) return;

    handleFile(droppedFile);
  });
    clearBtn.addEventListener("click", () => {
    // Reset file input
    fileInput.value = "";
    fileInfo.textContent = "";

    // Disable button again
    generateBtn.disabled = true;

    // Easiest: reload page to clear Flask output
    window.location.href = "/";
  });

  function handleFile(f) {
    file = f;
    fileInfo.textContent = `📄 ${f.name} (${(f.size / 1024).toFixed(1)} KB) ✔`;
    generateBtn.disabled = false;
  }

})();