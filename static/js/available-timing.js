document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('availabilityForm');
    const scheduleList = document.getElementById('scheduleList');

    // Get CSRF token
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    // Load existing schedule items when page loads
    loadExistingSchedule();

    function loadExistingSchedule() {
        fetch('/get-availability/', {
            method: 'GET',
            headers: {
                'X-CSRFToken': csrfToken,
                'Accept': 'application/json',
            },
            credentials: 'same-origin' // Include cookies for session authentication
        })
        .then(response => {
            // Check if response is ok (status in the range 200-299)
            if (!response.ok) {
                if (response.status === 403) {
                    throw new Error('Authentication required. Please log in again.');
                } else {
                    throw new Error(`Server returned ${response.status}: ${response.statusText}`);
                }
            }
            
            // Check content type to ensure we're getting JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Server did not return JSON. Got: ' + contentType);
            }
            
            return response.json();
        })
        .then(data => {
            // Clear the schedule list first
            scheduleList.innerHTML = '';
            
            if (data.availabilities && data.availabilities.length > 0) {
                // Add each availability to the schedule list
                data.availabilities.forEach(item => {
                    addScheduleItemToDOM(item);
                });
            } else {
                // Show "no slots" message if no items
                scheduleList.innerHTML = `
                    <p class="text-center text-gray-500 dark:text-gray-400 py-4">
                        No availability slots added yet
                    </p>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading schedule:', error);
            scheduleList.innerHTML = `
                <p class="text-center text-error py-4">
                    Error loading schedule: ${error.message}. 
                    <a href="javascript:location.reload()" class="underline">Try refreshing</a>
                </p>
            `;
        });
    }

    function addScheduleItemToDOM(item) {
        const scheduleItem = document.createElement('div');
        scheduleItem.className = 'p-4 border border-lightborder dark:border-darkborder rounded-lg flex justify-between items-center';
        scheduleItem.innerHTML = `
            <div>
                <p class="font-medium">${item.formatted_date}</p>
                <p class="text-sm text-secondarydark dark:text-secondarylight">
                    ${item.formatted_start_time} - ${item.formatted_end_time}
                </p>
                ${item.topic ? `<p class="text-xs text-primary mt-1">${item.topic}</p>` : ''}
            </div>
            <button class="text-error hover:text-opacity-80 delete-btn" data-id="${item.id}">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
            </button>
        `;
        
        // Add the new item to the schedule list
        scheduleList.appendChild(scheduleItem);
    }

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        // Get form values
        const topicSelect = document.getElementById('topic');
        const topic = topicSelect.options[topicSelect.selectedIndex].value;
        const date = document.getElementById('date').value;
        const startTime = document.getElementById('startTime').value;
        const endTime = document.getElementById('endTime').value;

        // Validate form data
        if (!topic || !date || !startTime || !endTime) {
            console.error('All fields are required');
            return;
        }

        // Combine date and time for backend
        const availableFrom = `${date}T${startTime}`;
        const availableTo = `${date}T${endTime}`;

        try {
            const response = await fetch('/add-availability/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    'Accept': 'application/json',
                },
                credentials: 'same-origin', // Include cookies for session authentication
                body: JSON.stringify({
                    topic: topic,
                    available_from: availableFrom,
                    available_to: availableTo,
                })
            });

            // Check if response is ok
            if (!response.ok) {
                if (response.status === 403) {
                    throw new Error('Authentication required. Please log in again.');
                } else {
                    // Try to get error message from response
                    const errorText = await response.text();
                    console.error('Server error response:', errorText);
                    throw new Error(`Server error: ${response.status}`);
                }
            }
            
            // Check content type to ensure we're getting JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                throw new Error('Server did not return JSON');
            }

            const data = await response.json();
            
            // Remove "no slots" message if it exists
            const noSlotsMessage = scheduleList.querySelector('p');
            if (noSlotsMessage) {
                noSlotsMessage.remove();
            }

            // Add the new item using the same function as the initial load
            addScheduleItemToDOM(data);

            // Reset form
            form.reset();
        } catch (error) {
            console.error('Error adding availability:', error);
            alert(`Failed to add availability: ${error.message}`);
        }
    });

    // Delete functionality
    scheduleList.addEventListener('click', async function(e) {
        if (e.target.closest('.delete-btn')) {
            const button = e.target.closest('.delete-btn');
            const id = button.dataset.id;
            
            try {
                const response = await fetch(`/delete-availability/${id}/`, {
                    method: 'DELETE',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Accept': 'application/json',
                    },
                    credentials: 'same-origin' // Include cookies for session authentication
                });

                if (!response.ok) {
                    if (response.status === 403) {
                        throw new Error('Authentication required');
                    } else {
                        throw new Error(`Server error: ${response.status}`);
                    }
                }

                button.closest('.p-4').remove();
                
                // Show "no slots" message if no more slots
                if (scheduleList.children.length === 0) {
                    scheduleList.innerHTML = `
                        <p class="text-center text-gray-500 dark:text-gray-400 py-4">
                            No availability slots added yet
                        </p>
                    `;
                }
            } catch (error) {
                console.error('Error deleting availability:', error);
                alert(`Failed to delete: ${error.message}`);
            }
        }
    });
});