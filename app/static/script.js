document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const controls = document.getElementById('controls');
    const progressBar = document.getElementById('progressBar');
    const progressBarInner = progressBar.querySelector('.progress-bar');
    const currentQuery = document.getElementById('currentQuery');
    const results = document.getElementById('results');
    const downloadBtn = document.getElementById('downloadBtn');
    const startBtn = document.getElementById('startBtn');
    const pauseBtn = document.getElementById('pauseBtn');
    const resumeBtn = document.getElementById('resumeBtn');
    const cancelBtn = document.getElementById('cancelBtn');

    let isRunning = false;
    let currentText = '';
    let currentNumLetters = 1;

    function showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger alert-dismissible fade show';
        errorDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        results.insertBefore(errorDiv, results.firstChild);
    }

    searchForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        currentText = document.getElementById('text').value;
        currentNumLetters = parseInt(document.getElementById('numLetters').value);

        // Show controls and progress bar
        controls.classList.remove('d-none');
        progressBar.classList.remove('d-none');
        startBtn.disabled = true;
        downloadBtn.disabled = true;
        results.innerHTML = ''; // Clear previous results

        try {
            // Start the search
            const response = await fetch('/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `text=${encodeURIComponent(currentText)}&num_letters=${currentNumLetters}`
            });
            
            const data = await response.json();
            console.log('Start response:', data); // Debug log
            
            if (data.error) {
                showError(data.error);
                startBtn.disabled = false;
                return;
            }

            isRunning = true;
            await startSearch();
        } catch (error) {
            console.error('Error starting search:', error);
            showError('Failed to start search. Please try again.');
            startBtn.disabled = false;
        }
    });

    pauseBtn.addEventListener('click', async function() {
        try {
            const response = await fetch('/pause', { method: 'POST' });
            const data = await response.json();
            console.log('Pause response:', data); // Debug log
            
            if (data.status === 'paused') {
                isRunning = false;
                pauseBtn.disabled = true;
                resumeBtn.disabled = false;
            }
        } catch (error) {
            console.error('Error pausing search:', error);
            showError('Failed to pause search. Please try again.');
        }
    });

    resumeBtn.addEventListener('click', async function() {
        try {
            const response = await fetch('/resume', { method: 'POST' });
            const data = await response.json();
            console.log('Resume response:', data); // Debug log
            
            if (data.status === 'resumed') {
                isRunning = true;
                pauseBtn.disabled = false;
                resumeBtn.disabled = true;
                await startSearch();
            }
        } catch (error) {
            console.error('Error resuming search:', error);
            showError('Failed to resume search. Please try again.');
        }
    });

    cancelBtn.addEventListener('click', function() {
        isRunning = false;
        controls.classList.add('d-none');
        progressBar.classList.add('d-none');
        startBtn.disabled = false;
        pauseBtn.disabled = false;
        resumeBtn.disabled = false;
        results.innerHTML = '';
        currentQuery.textContent = '-';
        progressBarInner.style.width = '0%';
    });

    downloadBtn.addEventListener('click', function() {
        window.location.href = '/download';
    });

    async function startSearch() {
        if (!isRunning) return;

        try {
            console.log('Fetching suggestions for:', currentText); // Debug log
            const response = await fetch(`/fetch_suggestions?text=${encodeURIComponent(currentText)}&num_letters=${currentNumLetters}`);
            const data = await response.json();
            console.log('Fetch response:', data); // Debug log

            if (data.error) {
                showError(data.error);
                isRunning = false;
                startBtn.disabled = false;
                return;
            }

            if (data.status === 'stopped') {
                console.log('Search stopped, restarting...'); // Debug log
                isRunning = true;
                setTimeout(startSearch, 1000);
                return;
            }

            currentQuery.textContent = data.current;
            progressBarInner.style.width = `${(data.progress / data.total) * 100}%`;

            if (data.suggestions_data && data.suggestions_data.length > 0) {
                const resultItem = document.createElement('div');
                resultItem.className = 'list-group-item mb-3';
                
                let suggestionsHtml = '';
                for (const suggestionData of data.suggestions_data) {
                    suggestionsHtml += `
                        <div class="suggestion-item mb-3">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <h6 class="mb-0">${suggestionData.suggestion}</h6>
                                <span class="badge bg-primary">Volume: ${suggestionData.volume}</span>
                            </div>
                            <div class="search-results">
                                ${suggestionData.clusters.map(cluster => `
                                    <div class="cluster mb-3">
                                        <div class="cluster-header d-flex justify-content-between align-items-center mb-2">
                                            <h6 class="mb-0">Domain: ${cluster.domain}</h6>
                                            <span class="badge bg-info">Cluster Size: ${cluster.cluster_size}</span>
                                        </div>
                                        ${cluster.results.map(result => `
                                            <div class="search-result mb-2">
                                                <a href="${result.link}" target="_blank" class="text-decoration-none">
                                                    <h6 class="mb-1">${result.title}</h6>
                                                </a>
                                                <p class="mb-0 small text-muted">${result.snippet}</p>
                                            </div>
                                        `).join('')}
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }
                
                resultItem.innerHTML = `
                    <h5 class="mb-3">Query: ${data.current}</h5>
                    ${suggestionsHtml}
                `;
                results.insertBefore(resultItem, results.firstChild);
            }

            if (data.status === 'complete') {
                isRunning = false;
                pauseBtn.disabled = true;
                resumeBtn.disabled = true;
                downloadBtn.disabled = false;
                startBtn.disabled = false;
            } else if (isRunning) {
                setTimeout(startSearch, 1000); // Add delay to avoid rate limiting
            }
        } catch (error) {
            console.error('Error:', error);
            showError('An error occurred while fetching suggestions. Please try again.');
            isRunning = false;
            startBtn.disabled = false;
        }
    }
}); 