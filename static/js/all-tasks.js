document.addEventListener('DOMContentLoaded', function () {
    const searchInput = document.getElementById('searchInput');
    const taskSearchForm = document.getElementById('taskSearchForm');
    const tableBody = document.querySelector('.table-responsive tbody');

    if (!searchInput || !taskSearchForm || !tableBody) return;

    // Debounce function with immediate option
    function debounce(func, wait, immediate) {
        let timeout;
        return function() {
            const context = this, args = arguments;
            const later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            const callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    }

    // AJAX function to fetch search results
    function fetchSearchResults(searchTerm) {
        const params = new URLSearchParams(window.location.search);
        params.set('search', searchTerm);
        params.set('page', '1');
        
        // Add loading state
        searchInput.classList.add('search-loading');
        tableBody.innerHTML = '<tr><td colspan="14" class="text-center py-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></td></tr>';

        // Fetch results via AJAX
        fetch(`${window.location.pathname}?${params.toString()}&ajax=1`)
            .then(response => response.text())
            .then(html => {
                // Parse the response and extract just the table body
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const newTableBody = doc.querySelector('.table-responsive tbody');
                
                if (newTableBody) {
                    tableBody.innerHTML = newTableBody.innerHTML;
                }
                
                // Update URL without reload
                window.history.pushState({}, '', `?${params.toString()}`);
            })
            .catch(error => {
                console.error('Error:', error);
                tableBody.innerHTML = '<tr><td colspan="14" class="text-center text-danger py-4">Error loading results</td></tr>';
            })
            .finally(() => {
                searchInput.classList.remove('search-loading');
                // Reinitialize tooltips if needed
                if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                    const tooltips = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
                    tooltips.map(tooltip => new bootstrap.Tooltip(tooltip));
                }
            });
    }

    // Debounced search with 400ms delay
    const debouncedSearch = debounce(function() {
        fetchSearchResults(this.value);
    }, 400);

    // Event listeners
    searchInput.addEventListener('input', debouncedSearch);
    searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            debouncedSearch.call(this);
        }
    });

    // Initial focus if search query exists
    if (searchInput.value) {
        searchInput.focus();
    }

    // Handle back/forward navigation
    window.addEventListener('popstate', function() {
        const params = new URLSearchParams(window.location.search);
        searchInput.value = params.get('search') || '';
        fetchSearchResults(searchInput.value);
    });
});


// Toggle columns based on screen size
function adjustTableColumns() {
    const screenWidth = window.innerWidth;
    const tables = document.querySelectorAll('.normal-table, .project-tasks-table');
    
    tables.forEach(table => {
        if (screenWidth < 768) {
            // Mobile view - hide less important columns
            table.querySelectorAll('th:nth-child(4), td:nth-child(4)').forEach(el => el.style.display = 'none');
            table.querySelectorAll('th:nth-child(7), td:nth-child(7)').forEach(el => el.style.display = 'none');
            table.querySelectorAll('th:nth-child(9), td:nth-child(9)').forEach(el => el.style.display = 'none');
        } else if (screenWidth < 992) {
            // Tablet view - show all but hide least important columns
            table.querySelectorAll('th, td').forEach(el => el.style.display = '');
            table.querySelectorAll('th:nth-child(9), td:nth-child(9)').forEach(el => el.style.display = 'none');
        } else {
            // Desktop view - show all columns
            table.querySelectorAll('th, td').forEach(el => el.style.display = '');
        }
    });
}

// Run on load and resize
window.addEventListener('load', adjustTableColumns);
window.addEventListener('resize', adjustTableColumns);

// Make project groups collapsible on mobile
document.querySelectorAll('.project-group-header').forEach(header => {
    header.addEventListener('click', function() {
        if (window.innerWidth < 768) {
            const target = document.querySelector(this.getAttribute('data-bs-target'));
            target.classList.toggle('show');
            const icon = this.querySelector('i');
            icon.classList.toggle('fa-chevron-down');
            icon.classList.toggle('fa-chevron-up');
        }
    });
});