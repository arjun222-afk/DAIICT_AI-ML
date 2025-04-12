// network_analysis.js - Client-side functionality for network analysis

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tab functionality
    const tabs = document.querySelectorAll('#network-tabs .nav-link');
    
    tabs.forEach(tab => {
        tab.addEventListener('click', function(event) {
            event.preventDefault();
            
            // Remove active class from all tabs
            tabs.forEach(t => {
                t.classList.remove('active');
                t.setAttribute('aria-selected', 'false');
            });
            
            // Add active class to clicked tab
            this.classList.add('active');
            this.setAttribute('aria-selected', 'true');
            
            // Hide all tab panes
            const tabPanes = document.querySelectorAll('.tab-pane');
            tabPanes.forEach(pane => {
                pane.classList.remove('show', 'active');
            });
            
            // Show the selected tab pane
            const targetId = this.getAttribute('data-bs-target').substring(1);
            const targetPane = document.getElementById(targetId);
            targetPane.classList.add('show', 'active');
        });
    });
    
    // Network refresh functionality
    setupNetworkRefresh();
    
    // Load network statistics
    loadNetworkStats();
    
    // Load skill recommendations if on the dashboard or profile page
    if (document.getElementById('skill-recommendations')) {
        loadSkillRecommendations();
    }
});

// Setup network refresh functionality
function setupNetworkRefresh() {
    const refreshButtons = [
        { id: 'refresh-user-network', type: 'user-network' },
        { id: 'refresh-skill-job-network', type: 'skill-job-network' },
        { id: 'refresh-full-network', type: 'full-network' }
    ];
    
    refreshButtons.forEach(button => {
        const element = document.getElementById(button.id);
        if (element) {
            element.addEventListener('click', function() {
                refreshNetwork(button.type);
            });
        }
    });
}

// Function to refresh a network visualization
function refreshNetwork(networkType) {
    // Display loading indicator
    const button = document.querySelector(`[id^="refresh-${networkType.split('-')[0]}"]`);
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...';
    button.disabled = true;
    
    fetch(`/api/refresh_network?type=${networkType}`)
        .then(response => response.json())
        .then(data => {
            // Reset button
            button.innerHTML = originalText;
            button.disabled = false;
            
            if (data.success) {
                // Reload the iframe with cache-busting parameter
                const timestamp = new Date().getTime();
                let frameId;
                
                if (networkType === 'user-network') {
                    frameId = 'user-network-frame';
                } else if (networkType === 'skill-job-network') {
                    frameId = 'skill-job-frame';
                } else if (networkType === 'full-network') {
                    frameId = 'full-network-frame';
                }
                
                if (frameId) {
                    const frame = document.getElementById(frameId);
                    frame.src = `/static/${data.file_path}?t=${timestamp}`;
                }
                
                showToast('Success', 'Network refreshed successfully!');
            } else {
                showToast('Error', 'Error refreshing network: ' + data.error, 'error');
            }
        })
        .catch(error => {
            // Reset button
            button.innerHTML = originalText;
            button.disabled = false;
            
            console.error('Error:', error);
            showToast('Error', 'Failed to refresh network', 'error');
        });
}

// Function to load network statistics
function loadNetworkStats() {
    const statsContainer = document.getElementById('network-stats');
    if (!statsContainer) return;
    
    fetch('/api/network_stats')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update statistics counts
                const counters = {
                    'user-count': data.user_count,
                    'skill-count': data.skill_count,
                    'job-count': data.job_count
                };
                
                for (const [id, count] of Object.entries(counters)) {
                    const element = document.getElementById(id);
                    if (element) {
                        element.textContent = count;
                    }
                }
                
                // Update top skills
                const topSkillsList = document.getElementById('top-skills');
                if (topSkillsList && data.top_skills) {
                    topSkillsList.innerHTML = '';
                    data.top_skills.forEach(skill => {
                        const li = document.createElement('li');
                        li.className = 'list-group-item d-flex justify-content-between align-items-center';
                        li.innerHTML = `
                            ${skill.name}
                            <span class="badge bg-success rounded-pill">${skill.connections}</span>
                        `;
                        topSkillsList.appendChild(li);
                    });
                }
            }
        })
        .catch(error => {
            console.error('Error loading network stats:', error);
        });
}

// Function to load skill recommendations
function loadSkillRecommendations() {
    const recommendationsContainer = document.getElementById('skill-recommendations');
    if (!recommendationsContainer) return;
    
    fetch('/api/skill_recommendations')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear loading indicator
                recommendationsContainer.innerHTML = '';
                
                if (data.recommendations.length === 0) {
                    recommendationsContainer.innerHTML = '<p>No skill recommendations available. Try to complete more skill assessments.</p>';
                    return;
                }
                
                // Create table
                const table = document.createElement('table');
                table.className = 'table table-striped';
                
                // Create table header
                const thead = document.createElement('thead');
                thead.innerHTML = `
                    <tr>
                        <th scope="col">Skill</th>
                        <th scope="col">Peer Usage</th>
                        <th scope="col">Job Demand</th>
                        <th scope="col">Relevance</th>
                    </tr>
                `;
                table.appendChild(thead);
                
                // Create table body
                const tbody = document.createElement('tbody');
                
                data.recommendations.forEach(rec => {
                    const relevance = calculateRelevance(rec.peer_frequency, rec.job_demand);
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${capitalizeFirstLetter(rec.skill)}</td>
                        <td>${rec.peer_frequency} users</td>
                        <td>${rec.job_demand} jobs</td>
                        <td>
                            <div class="progress">
                                <div class="progress-bar bg-${getRelevanceColor(relevance)}" 
                                     role="progressbar" 
                                     style="width: ${relevance}%" 
                                     aria-valuenow="${relevance}" 
                                     aria-valuemin="0" 
                                     aria-valuemax="100">
                                    ${relevance}%
                                </div>
                            </div>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
                
                table.appendChild(tbody);
                recommendationsContainer.appendChild(table);
            } else {
                recommendationsContainer.innerHTML = `<div class="alert alert-info">${data.error || 'Unable to load skill recommendations'}</div>`;
            }
        })
        .catch(error => {
            console.error('Error loading skill recommendations:', error);
            recommendationsContainer.innerHTML = '<div class="alert alert-danger">Failed to load skill recommendations</div>';
        });
}

// Helper function to calculate relevance score
function calculateRelevance(peerFrequency, jobDemand) {
    // Simple formula that weighs both factors
    // Modify this as needed for better recommendations
    const peerWeight = 0.4;
    const jobWeight = 0.6;
    
    // Normalize values (assuming max frequency is 10 and max demand is 50)
    const normalizedPeer = Math.min(peerFrequency / 10, 1);
    const normalizedJob = Math.min(jobDemand / 50, 1);
    
    // Calculate weighted score
    const score = (normalizedPeer * peerWeight + normalizedJob * jobWeight) * 100;
    
    // Return rounded score
    return Math.round(score);
}

// Helper function to get color based on relevance score
function getRelevanceColor(score) {
    if (score >= 80) return 'success';
    if (score >= 60) return 'info';
    if (score >= 40) return 'primary';
    if (score >= 20) return 'warning';
    return 'danger';
}

// Helper function to capitalize first letter
function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

// Helper function to show toast notifications
function showToast(title, message, type = 'success') {
    // Check if toast container exists, if not create it
    let toastContainer = document.getElementById('toast-container');
    
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toastId = 'toast-' + Date.now();
    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : 'success'}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    // Create toast content
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <strong>${title}</strong>: ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    // Add toast to container
    toastContainer.appendChild(toast);
    
    // Initialize and show toast
    const bsToast = new bootstrap.Toast(toast, { autohide: true, delay: 5000 });
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}