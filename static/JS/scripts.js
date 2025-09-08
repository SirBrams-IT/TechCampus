document.addEventListener('DOMContentLoaded', function() {
    const courseSelect = document.getElementById('courseSelect');
    const editCourseBtn = document.getElementById('editCourseBtn');
    const deleteCourseBtn = document.getElementById('deleteCourseBtn');
    const addModuleBtn = document.getElementById('addModuleBtn');
    const modulesContainer = document.getElementById('modulesContainer');
    const lessonsContainer = document.getElementById('lessonsContainer');
    const addLessonBtn = document.getElementById('addLessonBtn');
    const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    let currentCourseId = null;
    let currentModuleId = null;
    let topicCounter = 1;

    // Initialize topic management in the new module modal
    initializeTopicManagement();

    // When a course is selected
    courseSelect.addEventListener('change', function() {
        currentCourseId = this.value;
        const selectedOption = this.options[this.selectedIndex];
        
        // Reset buttons state
        editCourseBtn.disabled = !currentCourseId;
        deleteCourseBtn.disabled = !currentCourseId;
        addModuleBtn.disabled = !currentCourseId;
        
        if (currentCourseId) {
            // Set course data for editing
            editCourseBtn.setAttribute('data-course-id', currentCourseId);
            editCourseBtn.setAttribute('data-course-title', selectedOption.getAttribute('data-title'));
            editCourseBtn.setAttribute('data-course-code', selectedOption.getAttribute('data-code'));
            editCourseBtn.setAttribute('data-course-description', selectedOption.getAttribute('data-description'));
            
            // Load modules
            loadModules(currentCourseId);
        } else {
            // Clear modules container if no course selected
            modulesContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>Please select a course to view its modules
                </div>
            `;
        }

        // Reset lessons container
        lessonsContainer.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>Select a module to view and manage its lessons
            </div>
        `;
        addLessonBtn.disabled = true;
        currentModuleId = null;
    });

    // Set up module course ID when add module button is clicked
    addModuleBtn.addEventListener('click', function() {
        if (!currentCourseId) return;
        
        document.getElementById('moduleCourseId').value = currentCourseId;
        // Set the next order number
        const nextOrder = modulesContainer.querySelectorAll('.module-card').length + 1;
        document.getElementById('moduleOrder').value = nextOrder;
    });

    function loadModules(courseId) {
        modulesContainer.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary mb-2"></div>
                <p>Loading modules...</p>
            </div>
        `;

        fetch(`/course/${courseId}/modules/`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch modules');
            }
            return response.text();
        })
        .then(html => {
            modulesContainer.innerHTML = html;
            attachModuleEventListeners();
        })
        .catch(error => {
            console.error('Error loading modules:', error);
            modulesContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load modules. Please try again.
                </div>
            `;
        });
    }

    // Function to attach module button events
    function attachModuleEventListeners() {
        // View lessons buttons
        document.querySelectorAll('.view-lessons-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                currentModuleId = this.getAttribute('data-module-id');
                addLessonBtn.disabled = false;
                loadLessons(currentModuleId);
            });
        });

        // Edit module buttons
        document.querySelectorAll('.edit-module-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const moduleId = this.getAttribute('data-module-id');
                const moduleTitle = this.getAttribute('data-module-title');
                const moduleOrder = this.getAttribute('data-module-order');
                
                // Populate edit form
                document.getElementById('editModuleId').value = moduleId;
                document.getElementById('editModuleTitle').value = moduleTitle;
                document.getElementById('editModuleOrder').value = moduleOrder;
                
                // Set form action
                document.getElementById('editModuleForm').action = `/update_module/${moduleId}/`;
                
                // Show modal
                new bootstrap.Modal(document.getElementById('editModuleModal')).show();
            });
        });

        // Delete module buttons
        document.querySelectorAll('.delete-module-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const moduleId = this.getAttribute('data-module-id');
                
                // Set form action and module ID
                document.getElementById('deleteModuleForm').action = `/delete_module/${moduleId}/`;
                document.getElementById('deleteModuleId').value = moduleId;
                
                // Show modal
                new bootstrap.Modal(document.getElementById('deleteModuleModal')).show();
            });
        });
    }

    function loadLessons(moduleId) {
        lessonsContainer.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary mb-2"></div>
                <p>Loading lessons...</p>
            </div>
        `;

        fetch(`/modules/${moduleId}/lessons/`, {
            method: 'GET',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch lessons');
            }
            return response.text();
        })
        .then(html => {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;
            
            if (tempDiv.querySelector('#lessonsContainer')) {
                lessonsContainer.innerHTML = tempDiv.querySelector('#lessonsContainer').innerHTML;
            } else {
                lessonsContainer.innerHTML = html;
            }
        })
        .catch(error => {
            console.error('Error loading lessons:', error);
            lessonsContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Failed to load lessons. Please try again.
                </div>
            `;
        });
    }

    // ✅ Add lesson button handling (fix for NoReverseMatch)
    if (addLessonBtn) {
        addLessonBtn.addEventListener('click', function() {
            if (!currentModuleId) {
                alert("Please select a module first.");
                return;
            }
            // Dynamically set action of the Add Lesson form
            const form = document.getElementById('addLessonForm');
            if (form) {
                form.action = `/lessons/add/${currentModuleId}/`;
            }
            // Show the modal
            new bootstrap.Modal(document.getElementById('newLessonModal')).show();
        });
    }

    // Topic management functions for the module form
    function initializeTopicManagement() {
        const addTopicBtn = document.getElementById('addTopicBtn');
        if (addTopicBtn) {
            addTopicBtn.addEventListener('click', addTopicEntry);
        }
        
        const topicsContainer = document.getElementById('topicsContainer');
        if (topicsContainer) {
            topicsContainer.addEventListener('click', function(e) {
                if (e.target.classList.contains('remove-topic') || e.target.closest('.remove-topic')) {
                    const removeBtn = e.target.classList.contains('remove-topic') ? e.target : e.target.closest('.remove-topic');
                    removeBtn.closest('.topic-entry').remove();
                    renumberTopics();
                }
                if (e.target.classList.contains('add-subtopic') || e.target.closest('.add-subtopic')) {
                    const addBtn = e.target.classList.contains('add-subtopic') ? e.target : e.target.closest('.add-subtopic');
                    const topicId = addBtn.closest('.topic-entry').dataset.topicId;
                    addSubtopicInput(topicId);
                }
            });
        }
    }

    function addTopicEntry() {
        topicCounter++;
        const topicEntry = document.createElement('div');
        topicEntry.className = 'topic-entry card mb-2';
        topicEntry.dataset.topicId = topicCounter;
        topicEntry.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <h6 class="mb-0">Topic ${topicCounter}</h6>
                    <button type="button" class="btn btn-sm btn-danger remove-topic"><i class="fas fa-times"></i></button>
                </div>
                <input type="text" class="form-control mb-2 topic-title" name="topics[]" placeholder="Topic title" required>
                <div class="subtopics-container">
                    <div class="input-group mb-2">
                        <input type="text" class="form-control subtopic-input" name="subtopics_${topicCounter}[]" placeholder="Subtopic">
                        <button class="btn btn-outline-secondary add-subtopic" type="button"><i class="fas fa-plus"></i></button>
                    </div>
                </div>
            </div>
        `;
        document.getElementById('topicsContainer').appendChild(topicEntry);
    }

    function addSubtopicInput(topicId) {
        const subtopicContainer = document.querySelector(`[data-topic-id="${topicId}"] .subtopics-container`);
        const div = document.createElement('div');
        div.className = 'input-group mb-2';
        div.innerHTML = `
            <input type="text" class="form-control subtopic-input" name="subtopics_${topicId}[]" placeholder="Subtopic">
            <button class="btn btn-outline-secondary add-subtopic" type="button"><i class="fas fa-plus"></i></button>
        `;
        subtopicContainer.appendChild(div);
    }

    function renumberTopics() {
        const topics = document.querySelectorAll('.topic-entry');
        topics.forEach((topic, index) => {
            const topicNumber = index + 1;
            topic.dataset.topicId = topicNumber;
            topic.querySelector('h6').textContent = `Topic ${topicNumber}`;
            
            const subtopicInputs = topic.querySelectorAll('.subtopic-input');
            subtopicInputs.forEach(input => {
                input.name = `subtopics_${topicNumber}[]`;
            });
        });
        topicCounter = topics.length;
    }

    // Handle new module form submission with AJAX
    const newModuleForm = document.getElementById('newModuleForm');
    if (newModuleForm) {
        newModuleForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': csrftoken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('newModuleModal'));
                    if (modal) modal.hide();
                    
                    showToast('Module added successfully');
                    loadModules(currentCourseId);
                    
                    this.reset();
                    document.getElementById('topicsContainer').innerHTML = `
                        <div class="topic-entry card mb-2" data-topic-id="1">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <h6 class="mb-0">Topic 1</h6>
                                    <button type="button" class="btn btn-sm btn-danger remove-topic"><i class="fas fa-times"></i></button>
                                </div>
                                <input type="text" class="form-control mb-2 topic-title" name="topics[]" placeholder="Topic title" required>
                                <div class="subtopics-container">
                                    <div class="input-group mb-2">
                                        <input type="text" class="form-control subtopic-input" name="subtopics_1[]" placeholder="Subtopic">
                                        <button class="btn btn-outline-secondary add-subtopic" type="button"><i class="fas fa-plus"></i></button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                    topicCounter = 1;
                    initializeTopicManagement();
                } else {
                    alert('Error: ' + (data.message || 'Unknown error occurred'));
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while adding the module');
            });
        });
    }

    // Toast notification function
    function showToast(message) {
        const toastElement = document.getElementById('successToast');
        if (toastElement) {
            const toastMessage = document.getElementById('toastMessage');
            if (toastMessage) {
                toastMessage.textContent = message;
            }
            const toast = new bootstrap.Toast(toastElement);
            toast.show();
        }
    }
});
