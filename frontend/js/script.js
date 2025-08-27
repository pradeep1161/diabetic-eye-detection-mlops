document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('detectionForm');
    const fundusUpload = document.getElementById('fundusUpload'), fundusInput = document.getElementById('fundusImage'), fundusPreview = document.getElementById('fundusPreview');
    const octUpload = document.getElementById('octUpload'), octInput = document.getElementById('octImage'), octPreview = document.getElementById('octPreview');
    const resultsSection = document.getElementById('results'), loadingState = document.getElementById('loadingState'), resultsContent = document.getElementById('resultsContent');
    const symptomOtherCheck = document.getElementById('symptomOtherCheck'), otherSymptomContainer = document.getElementById('otherSymptomContainer');
    let reportUrl = null;

    setupUploadArea(fundusUpload, fundusInput, fundusPreview);
    setupUploadArea(octUpload, octInput, octPreview);
    symptomOtherCheck.addEventListener('change', () => { otherSymptomContainer.style.display = symptomOtherCheck.checked ? 'block' : 'none'; });
    form.addEventListener('submit', handleFormSubmission);
    setupNavLinks();

    function setupUploadArea(uploadArea, input, preview) {
        uploadArea.addEventListener('click', () => input.click());
        input.addEventListener('change', () => handleImagePreview(input.files[0], preview, uploadArea));
        ['dragover', 'dragleave', 'drop'].forEach(eventName => { uploadArea.addEventListener(eventName, e => { e.preventDefault(); e.stopPropagation(); }, false); });
        uploadArea.addEventListener('dragenter', () => uploadArea.classList.add('dragover'));
        uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('dragover'));
        uploadArea.addEventListener('drop', e => {
            uploadArea.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file) { input.files = e.dataTransfer.files; handleImagePreview(file, preview, uploadArea); }
        });
    }

    function handleImagePreview(file, previewElement, uploadArea) {
        if (!file || !file.type.startsWith('image/')) return;
        const reader = new FileReader();
        reader.onload = e => {
            previewElement.src = e.target.result;
            previewElement.style.display = 'block';
            uploadArea.querySelector('.upload-placeholder').style.display = 'none';
        };
        reader.readAsDataURL(file);
    }

    async function handleFormSubmission(e) {
        e.preventDefault();
        if (!validateForm()) return;
        resultsSection.style.display = 'block';
        loadingState.style.display = 'flex';
        resultsContent.style.display = 'none';
        smoothScroll(resultsSection);
        const formData = new FormData(form);
        if (symptomOtherCheck.checked) {
            const otherText = document.getElementById('otherSymptomText').value.trim();
            if (otherText) formData.append('symptoms[]', `Other: ${otherText}`);
        }
        try {
            const response = await fetch('http://localhost:5000/api/analyze', { method: 'POST', body: formData });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Analysis failed');
            reportUrl = data.report_url;
            displayResults(data);
        } catch (error) {
            showError(error.message || 'Failed to analyze images.');
        } finally {
            loadingState.style.display = 'none';
        }
    }

    function validateForm() {
        for (const id of ['name', 'age', 'gender', 'diabetesType', 'diabetesDuration', 'phone']) {
            const input = document.getElementById(id);
            if (!input.value.trim()) {
                showError(`'${input.previousElementSibling.textContent}' is a required field.`);
                return false;
            }
        }
        if (!fundusInput.files[0]) {
            showError('A Fundus image is required.');
            return false;
        }
        return true;
    }

    function displayResults(data) {
        resultsContent.style.display = 'block';
        const diagnosisDiv = document.getElementById('diagnosisResults');
        const severityDiv = document.getElementById('severityResults');
        const visualEvidenceCard = document.getElementById('visualEvidenceCard');
        const evidenceContainer = document.getElementById('evidenceContainer');
        const aiExplanationCard = document.getElementById('aiExplanationCard');
        const explanationContainer = document.getElementById('explanationContainer');
        
        diagnosisDiv.innerHTML = '<h3><i class="fas fa-diagnoses"></i> Diagnosis</h3>';
        severityDiv.innerHTML = '<h3><i class="fas fa-chart-line"></i> Severity Assessment</h3>';
        evidenceContainer.innerHTML = '';
        explanationContainer.innerHTML = '';
        visualEvidenceCard.style.display = 'none';
        aiExplanationCard.style.display = 'none';
        let hasHeatmap = false;

        if (!data.results.fundus && !data.results.oct) { diagnosisDiv.innerHTML += '<p>No analysis performed.</p>'; return; }

        if (data.results.fundus) {
            const { disease, confidence, severity, heatmap_b64, original_b64 } = data.results.fundus;
            diagnosisDiv.innerHTML += createResultBlock('Fundus Photo', disease, confidence);
            severityDiv.innerHTML += createSeverityBlock('Fundus Assessment', severity);
            if (heatmap_b64 && original_b64) {
                evidenceContainer.innerHTML += createEvidenceBlock('Fundus Analysis', original_b64, heatmap_b64);
                hasHeatmap = true;
            }
        }
        if (data.results.oct) {
            const { disease, confidence, severity, heatmap_b64, original_b64 } = data.results.oct;
            diagnosisDiv.innerHTML += createResultBlock('OCT Scan', disease, confidence);
            severityDiv.innerHTML += createSeverityBlock('OCT Assessment', severity);
            if (heatmap_b64 && original_b64) {
                evidenceContainer.innerHTML += createEvidenceBlock('OCT Analysis', original_b64, heatmap_b64);
                hasHeatmap = true;
            }
        }
        
        if (hasHeatmap) visualEvidenceCard.style.display = 'block';

        document.querySelectorAll('.explain-button').forEach(button => {
            button.addEventListener('click', handleExplainClick);
        });

        document.getElementById('recommendationsContent').innerHTML = `<h3><i class="fas fa-comment-medical"></i> AI Recommendations</h3><div class="recommendations-text">${formatRecommendations(data.recommendations)}</div>`;
        document.getElementById('downloadReport').onclick = () => downloadReport();
    }
    
    async function handleExplainClick(event) {
        const diseaseName = event.target.dataset.disease;
        const aiExplanationCard = document.getElementById('aiExplanationCard');
        const explanationContainer = document.getElementById('explanationContainer');
        aiExplanationCard.style.display = 'block';
        explanationContainer.innerHTML = '<div class="spinner"></div><p>Generating explanation...</p>';
        smoothScroll(aiExplanationCard);
        try {
            const response = await fetch('http://localhost:5000/api/explain', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ disease: diseaseName })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            explanationContainer.innerHTML = `<div class="explanation-content">${formatRecommendations(data.explanation)}</div>`;
        } catch (error) {
            explanationContainer.innerHTML = `<p class="alert alert-danger">Could not load explanation.</p>`;
        }
    }

    function createResultBlock(title, disease, confidence) {
        const explainButton = disease !== 'normal' ? `<button class="explain-button" data-disease="${disease}">✨ Explain</button>` : '';
        return `<div class="result-item"><h4>${title}</h4><p><strong>Condition:</strong> ${disease.replace(/_/g, ' ').replace(/\b\w/g, l=>l.toUpperCase())}${explainButton}</p><div class="confidence-bar-container"><div class="confidence-bar" style="width: ${confidence}%" title="Confidence: ${confidence}%"></div></div></div>`;
    }

    function createEvidenceBlock(title, original_b64, heatmap_b64) {
        return `<div class="evidence-item"><h4>${title}</h4><div class="image-comparison"><div class="image-wrapper"><img src="data:image/jpeg;base64,${original_b64}" alt="Original"><span class="image-label">Original</span></div><div class="image-wrapper"><img src="data:image/jpeg;base64,${heatmap_b64}" alt="Heatmap"><span class="image-label">AI Focus (Heatmap)</span></div></div></div>`;
    }

    function createSeverityBlock(title, severity) { const level = { 'No Disease Detected': 0, 'Mild': 25, 'Early Stage': 25, 'Early': 25, 'Suspected': 20, 'Moderate': 50, 'Severe': 75, 'Advanced': 85, 'Proliferative': 90 }[severity] || 50; return `<div class="result-item"><h4>${title}</h4><p><strong>Level:</strong> ${severity}</p><div class="severity-indicator"><div class="severity-bar"><div class="severity-marker" style="left: ${level}%" title="Severity: ${level}%"></div></div></div></div>`; }
    function formatRecommendations(text) { return text.split('\n').map(line => { line = line.trim(); if (line === '') return ''; if (line.match(/^\d\./) || /^[A-Z\s]+:$/.test(line)) return `<h4>${line}</h4>`; if (line.startsWith('-') || line.startsWith('•')) return `<li>${line.substring(1).trim()}</li>`; return `<p>${line}</p>`; }).join(''); }
    function downloadReport() { if (reportUrl) window.open(`http://localhost:5000${reportUrl}`, '_blank'); else showError('Report not available.'); }
    function setupNavLinks() { document.querySelectorAll('.nav-link, .logo, .cta-button').forEach(anchor => { anchor.addEventListener('click', function (e) { e.preventDefault(); smoothScroll(document.querySelector(this.getAttribute('href'))); }); }); }
    window.resetForm = function() { form.reset(); [fundusPreview, octPreview].forEach(p => p.style.display = 'none'); [fundusUpload, octUpload].forEach(u => u.querySelector('.upload-placeholder').style.display = 'flex'); otherSymptomContainer.style.display = 'none'; resultsSection.style.display = 'none'; window.scrollTo({ top: 0, behavior: 'smooth' }); }
    function showError(message) { const container = document.querySelector('.detection-section .container'); let alert = container.querySelector('.alert'); if (!alert) { alert = document.createElement('div'); alert.className = 'alert alert-danger'; container.insertBefore(alert, form); } alert.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`; setTimeout(() => alert.remove(), 5000); }
    function smoothScroll(element) { if (element) element.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    const style = document.createElement('style');
    style.textContent = `.result-item { margin-bottom: 1.5rem; } .result-item h4 { font-size: 1.1rem; color: var(--primary-dark); margin-bottom: 0.75rem; } .confidence-bar-container { width: 100%; height: 10px; background: #e2e8f0; border-radius: 5px; overflow: hidden; } .confidence-bar { height: 100%; background: var(--accent-color); border-radius: 5px; } .severity-indicator { padding-top: 1rem; } .severity-bar { position: relative; height: 8px; background: linear-gradient(to right, #10b981, #f59e0b, #ef4444); border-radius: 4px; } .severity-marker { position: absolute; top: 50%; width: 18px; height: 18px; background: var(--bg-white); border: 3px solid var(--primary-dark); border-radius: 50%; transform: translate(-50%, -50%); } .recommendations-text h4 { margin: 1.5rem 0 0.5rem; } .recommendations-text li { margin-left: 1.5rem; } .visual-evidence-card h3 { margin-bottom: 0.5rem; } .evidence-desc { color: var(--text-light); font-size: 0.9rem; margin-bottom: 1.5rem; } .evidence-item { margin-bottom: 2rem; } .evidence-item:last-child { margin-bottom: 0; } .evidence-item h4 { font-size: 1.2rem; color: var(--primary-dark); margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid var(--border-color); } .image-comparison { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; } .image-wrapper { text-align: center; } .image-wrapper img { max-width: 100%; border-radius: var(--radius); border: 1px solid var(--border-color); box-shadow: var(--shadow-sm); } .image-label { display: block; margin-top: 0.75rem; font-weight: 500; color: var(--text-dark); }`;
    document.head.appendChild(style);
});
