function copyText() {
    const gptResponseEditor = easyMDE.value();

    const tempTextArea = document.createElement('textarea');
    tempTextArea.value = gptResponseEditor;

    document.body.appendChild(tempTextArea);

    tempTextArea.select();

    try {
        document.execCommand('copy');
        showToast('Text copied to clipboard!', 'success');
    } catch (err) {
        showToast('Failed to copy text.', 'danger');
    }

    document.body.removeChild(tempTextArea);
}


function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container');
    const toastId = 'toast-' + Date.now();
    const toastHTML = `
            <div id="${toastId}" class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${message}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
    toastContainer.innerHTML += toastHTML;
    const toastElement = new bootstrap.Toast(document.getElementById(toastId));
    toastElement.show();

    setTimeout(() => {
        toastElement.hide();
    }, 3000);
}

document.addEventListener('DOMContentLoaded', function () {
    const username = document.getElementById('username').value;
    fetchLearningState(username);
});

function fetchLearningState(username) {
    if (username === "") {
        return;
    }
    fetch(`/get_learning_state?username=${username}`)
        .then(response => response.json())
        .then(data => {
            if (data.learning_state) {
                const learningStatusDiv = document.getElementById('learning-status');
                learningStatusDiv.style.display = "block";
                learningStatusDiv.innerHTML = `
                    <h3><i class="fas fa-chart-line"></i> Current learning status</h3>
                    <p>Course: ${data.learning_state.course}</p>
                    <p>Skill Level: ${data.learning_state.level}</p>
                    <p>Learning Goal: ${data.learning_state.goal}</p>
                    <p>Skills acquired: ${data.learning_state.skills}</p>
                `;
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

let myModal;

document.addEventListener('DOMContentLoaded', function () {
    const modalElement = document.getElementById('formModal');
    myModal = new bootstrap.Modal(modalElement);

    // Fetch and display learning state when the document is loaded
    const username = document.getElementById('username').value;
    fetchLearningState(username);

    const viewEditFormBtn = document.getElementById('view-edit-form-btn');
    if (viewEditFormBtn) {
        viewEditFormBtn.addEventListener('click', showForm);
    }

    const closeButton = document.querySelector('[aria-label="Close"]');
    if (closeButton) {
        closeButton.addEventListener('click', function () {
            myModal.hide();
            document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
        });
    }

    // Show modal on page load if no username is provided
    const queryUsername = getQueryParameter('username');
    if (!queryUsername) {
        myModal.show();
    }

    // Initialize EasyMDE editor
    const easyMDE = new EasyMDE({
        element: document.getElementById('gpt-response-editor'),
        renderingConfig: {
            singleLineBreaks: true,
            codeSyntaxHighlighting: true,
        },
        minHeight: "300px",
        maxHeight: "500px",
        status: false,
    });

    // Set global variable for the editor
    window.easyMDE = easyMDE;
});

// Function to save form data
function saveForm() {
    const form = document.getElementById('user-form');
    const fields = [
        {id: 'username', message: 'Please enter your username.'},
        {id: 'course', message: 'Please enter the course name.'},
        {id: 'goal', message: 'Please enter your learning goal.'}
    ];

    let formValid = true;

    fields.forEach(field => {
        const input = document.getElementById(field.id);
        if (input.value.trim() === '') {
            input.setCustomValidity(field.message);
            formValid = false;
        } else {
            input.setCustomValidity('');
        }
    });

    username = document.getElementById('username').value.trim()
    if (formValid && form.checkValidity()) {
        const formData = {
            username: username,
            course: document.getElementById('course').value.trim(),
            level: document.querySelector('input[name="level"]:checked').value,
            goal: document.getElementById('goal').value.trim(),
            skills: document.getElementById('skills').value.trim()
        };

        const previousFormData = JSON.parse(localStorage.getItem('previousFormData'));

        if (previousFormData && JSON.stringify(previousFormData) === JSON.stringify(formData)) {
            showToast('No changes detected. Form not submitted', 'info');
        } else {
            localStorage.setItem('previousFormData', JSON.stringify(formData));

            fetch('/save_form', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(formData)
            })
                .then(response => response.json())
                .then(data => {
                    showToast(data.message, 'success');
                    const username = encodeURIComponent(formData.username);
                    if (username === "") {
                        window.location.href = `?username=${username}`;
                    } else {
                        fetchLearningState(username)
                        fetchKnowledgeGraph(username)
                    }
                });
        }

        // Hide the modal after saving
        myModal.hide();
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());

    } else {
        form.reportValidity();
    }
}

document.addEventListener('DOMContentLoaded', function () {
    const viewEditFormBtn = document.getElementById('view-edit-form-btn');
    viewEditFormBtn.addEventListener('click', showForm);
});

function closeform() {
    const closeButton = document.querySelector('[aria-label="Close"]');

    if (!closeButton) {
        console.error('Close button not found');
        return;
    }

    const modalElement = document.getElementById('formModal');
    if (!modalElement) {
        console.error('Modal element not found');
        return;
    }

    const myModal = new bootstrap.Modal(modalElement);

    closeButton.addEventListener('click', function () {

        console.log('Close button clicked');
        myModal.hide();
        // Manually remove the modal backdrop in case it doesn't disappear
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
    });
}

function showForm() {
    const username = document.getElementById('username').value;
    if (!username) {
        return;
    }

    fetch(`/get_learning_state?username=${encodeURIComponent(username)}`)
        .then(response => response.json())
        .then(data => {
            data = data.learning_state;
            document.getElementById('username').value = data.username || '';
            document.getElementById('course').value = data.course || '';
            const levelRadioButtons = document.getElementsByName('level');
            levelRadioButtons.forEach(button => {
                if (button.value === data.level) {
                    button.checked = true;
                }
            });
            document.getElementById('goal').value = data.goal || '';
            document.getElementById('skills').value = data.skills || '';
        })
        .catch(error => {
            console.error('Error fetching user data:', error);
        });

    // Show the modal after the data is loaded
    myModal.show();
}

function generatePrompt() {
    const userInput = document.getElementById('search-input').value;
    const username = document.getElementById('username').value;

    if (userInput === '') {
        showToast('Please enter your learning goal.', 'warning');
        return;
    }
    document.getElementById('loading-spinner-2').style.display = 'block';

    // 调用服务器拆分关键词并生成提示
    fetch('/generate_prompt', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            input: userInput,
            username: username
        })
    })
        .then(response => response.json())
        .then(data => {
            document.getElementById('loading-spinner-2').style.display = 'none';
            document.getElementById('generated-prompt').innerText = data.prompt;
            document.getElementById('prompt-section').style.display = 'block';
        });
}

document.addEventListener('DOMContentLoaded', function () {
    const easyMDE = new EasyMDE({
        element: document.getElementById('gpt-response-editor'),
        renderingConfig: {
            singleLineBreaks: true,
            codeSyntaxHighlighting: true,
        },
        minHeight: "300px",
        maxHeight: "500px",
        status: false,
    });

    // 在这里设置全局变量
    window.easyMDE = easyMDE;
});


function searchGPT() {
    const prompt = document.getElementById('generated-prompt').innerText;
    const gptResponseSection = document.getElementById('gpt-response-section');
    const username = document.getElementById('username').value;
    const spinner = document.getElementById('loading-spinner');

    spinner.style.display = 'block';

    fetch('/query_gpt', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({prompt: prompt, username: username})
    })
        .then(response => response.json())
        .then(data => {
            const gptResponseEditor = document.getElementById('gpt-response-editor');

            if (typeof easyMDE !== 'undefined' && easyMDE) {
                easyMDE.value(data.response);
            } else {
                gptResponseEditor.value = data.response;
            }

            gptResponseSection.style.display = 'block';
            fetchNextPrompts(data.response, prompt);
        })
        .catch(error => {
            console.error('Error fetching GPT response:', error);
        })
        .finally(() => {
            spinner.style.display = 'none';
        });
}


function handleResponse(type) {
    if (type === "bad") {
        showToast('Feedback received. Please try to regenerate Or We will try to improve the model later.', 'warning');
    } else {
        const username = document.getElementById('username').value;
        const prompt = document.getElementById('search-input').value;
        const response = easyMDE.value();

        fetch(`/handle_response`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({type, prompt, response, username: username})
        })
            .then(response => response.json())
            .then(data => {
                showToast(data.message, 'success');
            });
        fetchLearningState(username)
        fetchKnowledgeGraph(username)
    }
}

function regeneratePrompt() {
    searchGPT()
}

async function fetchNextPrompts(response, previousPrompt) {
    const username = document.getElementById('username').value;

    await fetch(`/next_prompts?username=${encodeURIComponent(username)}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            previous_query_result: response,
            previous_prompt: previousPrompt
        })
    })
        .then(res => res.json())
        .then(data => {
            const nextPromptsContainer = document.getElementById('next-prompts-container');
            if (data.next_prompts) {
                let parsedContent = marked.parse(data.next_prompts);

                // Adjust font size from h3 to a smaller size
                parsedContent = parsedContent.replace(/<h3>/g, '<h5>').replace(/<\/h3>/g, '</h5>');

                document.querySelector('.card-text').innerHTML = parsedContent;
                nextPromptsContainer.style.display = 'block';
            } else {
                nextPromptsContainer.innerHTML = `No further prompts available`;
                nextPromptsContainer.style.display = 'block';
            }
        })
        .catch(error => {
            console.error('Error fetching next prompts:', error);
        });
}

cytoscape.use(cytoscapeDagre);

async function fetchKnowledgeGraph(username) {
    if (username === "") {
        return;
    }
    try {
        const response = await fetch(`/get_knowledge_graph?username=${username}`);
        const data = await response.json();

        console.log("Fetched data:", data);  // Debugging output

        if (!data.nodes || !data.edges) {
            console.error("Knowledge graph data is empty or undefined.");
            return;
        }

        renderKnowledgeGraph(data);
    } catch (error) {
        console.error("Error fetching knowledge graph:", error);
    }
}

function renderKnowledgeGraph(graphData) {
    const cy = cytoscape({
        container: document.getElementById('knowledge-graph'),
        elements: [
            ...graphData.nodes,
            ...graphData.edges
        ],
        style: [
            {
                selector: 'node',
                style: {
                    'background-color': function (ele) {
                        switch (ele.data('id')) {
                            case 'Course':
                                return '#3498db';
                            case 'Level':
                                return '#2ecc71';
                            case 'Goal':
                                return '#e74c3c';
                            case 'Skills':
                                return '#f1c40f';
                            default:
                                return '#9b59b6';
                        }
                    },
                    'label': 'data(label)',
                    'color': '#ffffff',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'font-size': '14px',
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 2,
                    'line-color': '#7f8c8d',
                    'target-arrow-color': '#7f8c8d',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                }
            }
        ],
        layout: {
            name: 'cose',
            directed: true,
            padding: 10
        }
    });
}

username = document.getElementById('username').value;
fetchKnowledgeGraph(username);

document.addEventListener('DOMContentLoaded', function () {
    anime({
        targets: '.fade-in',
        opacity: [0, 1],
        duration: 1000,
        easing: 'easeInOutQuad'
    });
});


function getQueryParameter(name) {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get(name);
}

document.addEventListener('DOMContentLoaded', function () {
    const username = getQueryParameter('username');

    if (!username) {
        myModal.show()
    }
});





