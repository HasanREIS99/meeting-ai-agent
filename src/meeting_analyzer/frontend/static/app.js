/* Meeting Transcript Analyzer — Frontend (NFR-U-001, NFR-U-002, NFR-U-003) */

(function () {
    'use strict';

    // ── State ──────────────────────────────────────────────────────

    let selectedFile = null;

    // ── DOM refs ───────────────────────────────────────────────────

    const $ = (sel) => document.querySelector(sel);

    const uploadSection   = $('#upload-section');
    const processingSection = $('#processing-section');
    const resultsSection  = $('#results-section');
    const errorSection    = $('#error-section');

    const fileInput = $('#file-input');
    const browseBtn = $('#browse-btn');
    const dropZone  = $('#drop-zone');
    const fileInfo  = $('#file-info');
    const fileName  = $('#file-name');
    const fileSize  = $('#file-size');
    const validateBtn = $('#validate-btn');
    const removeFileBtn = $('#remove-file');
    const validationResult = $('#validation-result');

    const progressFill = $('#progress-fill');
    const statusText   = $('#status-text');

    const markdownOutput = $('#markdown-output');
    const copyBtn        = $('#copy-btn');
    const downloadBtn    = $('#download-btn');
    const newAnalysisBtn = $('#new-analysis-btn');

    const errorMessage = $('#error-message');
    const retryBtn     = $('#retry-btn');
    const newAnalysisErr = $('#new-analysis-error');

    // ── Show / hide sections ───────────────────────────────────────

    function showSection(name) {
        [uploadSection, processingSection, resultsSection, errorSection]
            .forEach((s) => s.classList.add('hidden'));

        const map = {
            upload: uploadSection,
            processing: processingSection,
            results: resultsSection,
            error: errorSection,
        };
        if (map[name]) map[name].classList.remove('hidden');
    }

    // ── File selection ─────────────────────────────────────────────

    browseBtn.addEventListener('click', () => fileInput.click());

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            selectFile(e.target.files[0]);
        }
    });

    // Drag & drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        if (e.dataTransfer.files.length > 0) {
            selectFile(e.dataTransfer.files[0]);
        }
    });

    function selectFile(file) {
        if (!file.name.toLowerCase().endsWith('.txt')) {
            showMessage(validationResult, 'Please select a .txt file.', 'error');
            return;
        }
        selectedFile = file;
        fileName.textContent = file.name;
        fileSize.textContent = formatSize(file.size);
        fileInfo.classList.remove('hidden');
        showMessage(validationResult, '', '');
    }

    removeFileBtn.addEventListener('click', () => {
        selectedFile = null;
        fileInput.value = '';
        fileInfo.classList.add('hidden');
        validationResult.classList.add('hidden');
    });

    // ── Validate & upload ──────────────────────────────────────────

    validateBtn.addEventListener('click', async () => {
        if (!selectedFile) return;

        showSection('processing');
        animateProgress();

        try {
            // Pre-validate
            const formData = new FormData();
            formData.append('file', selectedFile);

            const validateResp = await fetch('/api/v1/validate', {
                method: 'POST',
                body: formData,
            });

            const validateData = await validateResp.json();

            if (!validateData.valid) {
                throw new Error(validateData.errors.join('; '));
            }

            // Upload for analysis
            const analysisForm = new FormData();
            analysisForm.append('file', selectedFile);

            const analysisResp = await fetch('/api/v1/analyze', {
                method: 'POST',
                body: analysisForm,
            });

            if (!analysisResp.ok) {
                const errData = await analysisResp.json();
                throw new Error(errData.detail || 'Analysis failed');
            }

            const result = await analysisResp.json();
            displayResults(result);

        } catch (err) {
            showSection('error');
            errorMessage.textContent = err.message;
            stopProgress();
        }
    });

    // ── Display results ────────────────────────────────────────────

    function displayResults(result) {
        progressFill.style.width = '100%';
        statusText.textContent = 'Analysis complete';

        // Render Markdown (simple client-side rendering)
        markdownOutput.innerHTML = renderMarkdown(result.markdown_content);

        showSection('results');
    }

    function renderMarkdown(md) {
        // Simple Markdown-to-HTML converter (sufficient for our output format)
        return md
            .replace(/^### (.+)$/gm, '<h3>$1</h3>')
            .replace(/^## (.+)$/gm, '<h2>$1</h2>')
            .replace(/^# (.+)$/gm, '<h1>$1</h1>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/^`(.+?)`/gm, '<code>$1</code>')
            .replace(/^---$/gm, '<hr>')
            .replace(/^(⚠️?.+)$/gm, '<blockquote>$1</blockquote>')
            .replace(/\n/g, '<br>');
    }

    // ── Copy / Download ────────────────────────────────────────────

    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(markdownOutput.innerText)
            .then(() => {
                copyBtn.textContent = '✅ Copied!';
                setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
            });
    });

    downloadBtn.addEventListener('click', () => {
        const blob = new Blob([markdownOutput.innerText], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'meeting-analysis.md';
        a.click();
        URL.revokeObjectURL(url);
    });

    // ── New analysis ───────────────────────────────────────────────

    function resetApp() {
        selectedFile = null;
        fileInput.value = '';
        fileInfo.classList.add('hidden');
        validationResult.classList.add('hidden');
        progressFill.style.width = '0%';
        stopProgress();
        showSection('upload');
    }

    newAnalysisBtn.addEventListener('click', resetApp);
    newAnalysisErr.addEventListener('click', resetApp);
    retryBtn.addEventListener('click', () => validateBtn.click());

    // ── Helpers ────────────────────────────────────────────────────

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function showMessage(el, text, type) {
        el.textContent = text;
        el.className = 'message' + (type ? ' message-' + type : '');
        el.classList.toggle('hidden', !text);
    }

    function animateProgress() {
        let width = 0;
        const interval = setInterval(() => {
            if (width >= 80) {
                clearInterval(interval);
                return;
            }
            width += Math.random() * 10;
            progressFill.style.width = Math.min(width, 80) + '%';
        }, 500);
        window._progressInterval = interval;
    }

    function stopProgress() {
        if (window._progressInterval) {
            clearInterval(window._progressInterval);
            window._progressInterval = null;
        }
    }

    // Auto-start on page load (no auth check needed)
    showSection('upload');
})();
