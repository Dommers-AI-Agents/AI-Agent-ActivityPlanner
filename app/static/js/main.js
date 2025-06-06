/**
 * Main JavaScript for the AI Group Planner application
 */

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
  // Initialize any components that need JavaScript
  initializeComponents();
  
  // Set up event listeners
  setupEventListeners();
  
  // Handle form restoration after login
  restoreFormDataAfterLogin();
});

/**
 * Initialize all components that need JavaScript
 */
function initializeComponents() {
  // Initialize tooltips if Bootstrap is being used
  if (typeof bootstrap !== 'undefined') {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
  }
  
  // Initialize any dynamic forms
  initDynamicForms();
  
  // Initialize question interface if present
  initQuestionInterface();
}

/**
 * Add event listeners for interactive elements
 */
function setupEventListeners() {
  // Add participant button
  const addParticipantBtn = document.getElementById('add-participant-btn');
  if (addParticipantBtn) {
    addParticipantBtn.addEventListener('click', addParticipantField);
  }
  
  // Submit answers button
  const submitAnswersBtn = document.getElementById('submit-answers-btn');
  if (submitAnswersBtn) {
    submitAnswersBtn.addEventListener('click', submitAnswers);
  }
  
  // Generate plan button
  const generatePlanBtn = document.getElementById('generate-plan-btn');
  if (generatePlanBtn) {
    generatePlanBtn.addEventListener('click', generatePlan);
  }
  
  // Submit feedback form
  const feedbackForm = document.getElementById('feedback-form');
  if (feedbackForm) {
    feedbackForm.addEventListener('submit', handleFeedbackSubmit);
  }
  
  // Finalize plan button
  const finalizePlanBtn = document.getElementById('finalize-plan-btn');
  if (finalizePlanBtn) {
    finalizePlanBtn.addEventListener('click', finalizePlan);
  }
}

/**
 * Initialize dynamic forms (like the add participant form)
 */
function initDynamicForms() {
  // Add first participant field if needed
  const participantsContainer = document.getElementById('participants-container');
  if (participantsContainer && participantsContainer.children.length === 0) {
    addParticipantField();
  }
}

/**
 * Add a new participant field to the form
 */
function addParticipantField() {
  const participantsContainer = document.getElementById('participants-container');
  if (!participantsContainer) return;
  
  const participantIndex = participantsContainer.children.length;
  
  const participantHtml = `
    <div class="participant-entry card mb-3">
      <div class="card-body">
        <div class="row">
          <div class="col-md-4 mb-3">
            <label for="participant_name_${participantIndex}" class="form-label">Name (optional)</label>
            <input type="text" class="form-control" id="participant_name_${participantIndex}" name="participant_name" placeholder="Participant name">
          </div>
          <div class="col-md-4 mb-3">
            <label for="participant_phone_${participantIndex}" class="form-label">Phone Number *</label>
            <input type="tel" class="form-control" id="participant_phone_${participantIndex}" name="participant_phone" placeholder="(555) 123-4567" required>
          </div>
          <div class="col-md-4 mb-3">
            <label for="participant_email_${participantIndex}" class="form-label">Email (optional)</label>
            <input type="email" class="form-control" id="participant_email_${participantIndex}" name="participant_email" placeholder="email@example.com">
          </div>
        </div>
        <button type="button" class="btn btn-sm btn-outline-danger remove-participant-btn">Remove</button>
      </div>
    </div>
  `;
  
  // Create a temporary element to hold our HTML
  const temp = document.createElement('div');
  temp.innerHTML = participantHtml;
  const participantEntry = temp.firstElementChild;
  
  // Add event listener to the remove button
  const removeBtn = participantEntry.querySelector('.remove-participant-btn');
  removeBtn.addEventListener('click', function() {
    participantsContainer.removeChild(participantEntry);
  });
  
  // Add the new participant field to the container
  participantsContainer.appendChild(participantEntry);
}

/**
 * Initialize the question interface
 */
function initQuestionInterface() {
  const questionsContainer = document.getElementById('questions-container');
  if (!questionsContainer) return;
  
  // If we have questions data in the page, render them
  if (window.questionsBatch && Array.isArray(window.questionsBatch)) {
    renderQuestions(window.questionsBatch);
  }
}

/**
 * Render questions in the UI
 */
function renderQuestions(questions) {
  const questionsContainer = document.getElementById('questions-container');
  if (!questionsContainer) return;
  
  // Clear existing questions
  questionsContainer.innerHTML = '';
  
  // Render each question
  questions.forEach(question => {
    const questionEl = createQuestionElement(question);
    questionsContainer.appendChild(questionEl);
  });
  
  // Show the submit button
  const submitBtn = document.getElementById('submit-answers-btn');
  if (submitBtn) {
    submitBtn.style.display = 'block';
  }
}

/**
 * Create a DOM element for a question
 */
function createQuestionElement(question) {
  const questionDiv = document.createElement('div');
  questionDiv.className = 'question mb-4';
  questionDiv.dataset.questionId = question.id;
  
  const questionLabel = document.createElement('label');
  questionLabel.className = 'question-text';
  questionLabel.textContent = question.question;
  if (question.required) {
    const requiredSpan = document.createElement('span');
    requiredSpan.className = 'text-danger';
    requiredSpan.textContent = ' *';
    questionLabel.appendChild(requiredSpan);
  }
  
  questionDiv.appendChild(questionLabel);
  
  let inputEl;
  
  switch (question.type) {
    case 'text':
      inputEl = document.createElement('input');
      inputEl.type = 'text';
      inputEl.className = 'form-control';
      inputEl.required = question.required;
      break;
      
    case 'email':
      inputEl = document.createElement('input');
      inputEl.type = 'email';
      inputEl.className = 'form-control';
      inputEl.required = question.required;
      break;
      
    case 'number':
      inputEl = document.createElement('input');
      inputEl.type = 'number';
      inputEl.className = 'form-control';
      inputEl.required = question.required;
      break;
      
    case 'boolean':
      inputEl = document.createElement('div');
      inputEl.className = 'form-check form-switch';
      
      const checkInput = document.createElement('input');
      checkInput.className = 'form-check-input';
      checkInput.type = 'checkbox';
      checkInput.id = `question_${question.id}`;
      
      const checkLabel = document.createElement('label');
      checkLabel.className = 'form-check-label';
      checkLabel.htmlFor = `question_${question.id}`;
      checkLabel.textContent = 'Yes';
      
      inputEl.appendChild(checkInput);
      inputEl.appendChild(checkLabel);
      break;
      
    case 'select':
      inputEl = document.createElement('select');
      inputEl.className = 'form-select';
      inputEl.required = question.required;
      
      // Add placeholder option
      const placeholderOption = document.createElement('option');
      placeholderOption.value = '';
      placeholderOption.textContent = 'Select an option';
      placeholderOption.selected = true;
      placeholderOption.disabled = true;
      inputEl.appendChild(placeholderOption);
      
      // Add options
      if (question.options && Array.isArray(question.options)) {
        question.options.forEach(option => {
          const optionEl = document.createElement('option');
          optionEl.value = option;
          optionEl.textContent = option;
          inputEl.appendChild(optionEl);
        });
      }
      break;
      
    case 'multiselect':
      inputEl = document.createElement('div');
      inputEl.className = 'multiselect-options';
      
      if (question.options && Array.isArray(question.options)) {
        question.options.forEach(option => {
          const optionDiv = document.createElement('div');
          optionDiv.className = 'form-check';
          
          const checkInput = document.createElement('input');
          checkInput.className = 'form-check-input';
          checkInput.type = 'checkbox';
          checkInput.value = option;
          checkInput.id = `option_${question.id}_${option.replace(/\s+/g, '_')}`;
          
          const checkLabel = document.createElement('label');
          checkLabel.className = 'form-check-label';
          checkLabel.htmlFor = `option_${question.id}_${option.replace(/\s+/g, '_')}`;
          checkLabel.textContent = option;
          
          optionDiv.appendChild(checkInput);
          optionDiv.appendChild(checkLabel);
          inputEl.appendChild(optionDiv);
        });
      }
      break;
      
    case 'textarea':
      inputEl = document.createElement('textarea');
      inputEl.className = 'form-control';
      inputEl.rows = 3;
      inputEl.required = question.required;
      break;
      
    default:
      inputEl = document.createElement('input');
      inputEl.type = 'text';
      inputEl.className = 'form-control';
      inputEl.required = question.required;
  }
  
  questionDiv.appendChild(inputEl);
  return questionDiv;
}

/**
 * Submit answers to the current batch of questions
 */
function submitAnswers() {
  const questionsContainer = document.getElementById('questions-container');
  if (!questionsContainer) {
    console.error('Questions container not found');
    return;
  }
  
  const activityId = document.getElementById('activity-id')?.value;
  if (!activityId) {
    console.error('Activity ID not found');
    return;
  }
  
  console.log('Submitting answers for activity ID:', activityId);
  
  // Collect answers from the form
  const answers = {};
  const questionElements = questionsContainer.querySelectorAll('.question');
  
  console.log('Found', questionElements.length, 'question elements');
  
  questionElements.forEach(questionEl => {
    const questionId = questionEl.dataset.questionId;
    let value;
    
    // Handle different question types
    if (questionEl.querySelector('select')) {
      // Select dropdown
      value = questionEl.querySelector('select').value;
      console.log('Select value for', questionId, ':', value);
    } else if (questionEl.querySelector('.multiselect-options')) {
      // Multiselect checkboxes
      const checkedOptions = questionEl.querySelectorAll('input[type="checkbox"]:checked');
      value = Array.from(checkedOptions).map(option => option.value);
      console.log('Multiselect value for', questionId, ':', value);
    } else if (questionEl.querySelector('.form-check-input[type="checkbox"]')) {
      // Boolean (yes/no) question
      value = questionEl.querySelector('.form-check-input').checked;
      console.log('Boolean value for', questionId, ':', value);
    } else if (questionEl.querySelector('textarea')) {
      // Textarea
      value = questionEl.querySelector('textarea').value;
      console.log('Textarea value for', questionId, ':', value);
    } else if (questionEl.querySelector('input')) {
      // Text, email, number inputs
      value = questionEl.querySelector('input').value;
      console.log('Input value for', questionId, ':', value);
    } else {
      console.warn('Could not find input element for question', questionId);
    }
    
    answers[questionId] = value;
  });
  
  console.log('Submitting answers:', answers);
  
  // Show loading state
  const submitBtn = document.getElementById('submit-answers-btn');
  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Submitting...';
  }
  
  // Send answers to the server
  fetch(`/activity/${activityId}/submit-answers`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ answers }),
  })
  .then(response => {
    console.log('Response status:', response.status);
    if (!response.ok) {
      throw new Error('Network response was not ok: ' + response.status);
    }
    return response.json();
  })
  .then(data => {
    console.log('Server response:', data);
    
    // Reset button state
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Continue';
    }
    
    if (data.complete) {
      console.log('All questions completed');
      // All questions have been answered
      showCompletionMessage();
    } else if (data.next_questions) {
      console.log('Rendering next batch of questions:', data.next_questions);
      // Show the next batch of questions
      renderQuestions(data.next_questions);
      
      // Scroll to the top of the questions container
      questionsContainer.scrollIntoView({ behavior: 'smooth' });
    } else {
      console.warn('No next_questions in response');
      alert('No more questions available. Please refresh the page.');
    }
  })
  .catch(error => {
    console.error('Error submitting answers:', error);
    
    // Reset button state
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Try Again';
    }
    
    alert('There was a problem submitting your answers: ' + error.message);
  });
}

/**
 * Show completion message when all questions are answered
 */
function showCompletionMessage() {
  const questionsContainer = document.getElementById('questions-container');
  if (!questionsContainer) return;
  
  // Clear the questions container
  questionsContainer.innerHTML = '';
  
  // Create completion message
  const completionDiv = document.createElement('div');
  completionDiv.className = 'alert alert-success text-center';
  completionDiv.innerHTML = `
    <h4 class="alert-heading">Thank you!</h4>
    <p>You've answered all the questions. Your preferences have been saved.</p>
    <hr>
    <p class="mb-0">The group activity plan will be created once everyone has provided their input.</p>
  `;
  
  questionsContainer.appendChild(completionDiv);
  
  // Hide submit button
  const submitBtn = document.getElementById('submit-answers-btn');
  if (submitBtn) {
    submitBtn.style.display = 'none';
  }
  
  // Show return to activity button
  const returnBtn = document.createElement('a');
  returnBtn.className = 'btn btn-primary mt-3';
  returnBtn.textContent = 'Return to Activity';
  returnBtn.href = window.location.href.replace('/questions', '');
  
  questionsContainer.appendChild(returnBtn);
}

/**
 * Generate plan for the activity
 */
function generatePlan() {
  const activityId = document.getElementById('activity-id')?.value;
  if (!activityId) {
    console.error('Activity ID not found');
    return;
  }
  
  // Show loading state
  const generateBtn = document.getElementById('generate-plan-btn');
  if (generateBtn) {
    generateBtn.disabled = true;
    generateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
  }
  
  // Redirect to the generate plan route
  window.location.href = `/activity/${activityId}/generate-plan`;
}

/**
 * Handle feedback form submission
 */
function handleFeedbackSubmit(event) {
  // The form will be submitted normally, no need to prevent default
  // This function can be used to add client-side validation if needed
  const feedbackText = document.getElementById('feedback-text')?.value;
  if (!feedbackText || feedbackText.trim() === '') {
    event.preventDefault();
    alert('Please enter your feedback before submitting.');
  }
}

/**
 * Finalize the activity plan
 */
function finalizePlan() {
  const activityId = document.getElementById('activity-id')?.value;
  if (!activityId) {
    console.error('Activity ID not found');
    return;
  }
  
  // Show loading state
  const finalizeBtn = document.getElementById('finalize-plan-btn');
  if (finalizeBtn) {
    finalizeBtn.disabled = true;
    finalizeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Finalizing...';
  }
  
  // Confirm before finalizing
  if (confirm('Are you sure you want to finalize this plan? All participants will be notified and no further changes will be allowed.')) {
    // Redirect to the finalize plan route
    window.location.href = `/activity/${activityId}/finalize`;
  } else {
    // Reset button if canceled
    if (finalizeBtn) {
      finalizeBtn.disabled = false;
      finalizeBtn.innerHTML = 'Finalize Plan';
    }
  }
}

/**
 * Restore form data after login
 */
function restoreFormDataAfterLogin() {
  // Check if we're on the create activity page
  const activityForm = document.getElementById('activity-form');
  if (!activityForm) return;
  
  // Check if we have form data in sessionStorage
  const storedFormData = sessionStorage.getItem('activity_form_data');
  
  // Check if we need to restore data (either from the restore flag or if we have stored data)
  const shouldRestore = document.getElementById('restore_data_after_login') && 
                        document.getElementById('restore_data_after_login').value === 'true';
  
  if (!storedFormData && !shouldRestore) return;
  
  // If the flag is set but no data is found, show a message
  if (shouldRestore && !storedFormData) {
    console.log('Restore flag set but no form data found in sessionStorage');
    return;
  }
  
  console.log('Found stored form data, restoring...');
  
  try {
    // Parse the stored data and check if it's in the new format with timestamp
    const parsedData = JSON.parse(storedFormData);
    
    // Check if we have the new structured format or old direct format
    const formData = parsedData.formData || parsedData;
    
    // Check for expiration - 24 hour expiry
    const timestamp = parsedData.timestamp || 0;
    const now = new Date().getTime();
    const MAX_AGE = 24 * 60 * 60 * 1000; // 24 hours in milliseconds
    
    if (timestamp && (now - timestamp > MAX_AGE)) {
      console.log('Stored form data is too old (>24h), discarding');
      sessionStorage.removeItem('activity_form_data');
      return;
    }
    
    console.log('Successfully parsed form data:', formData);
    
    // Fill in the form fields
    for (const [key, value] of Object.entries(formData)) {
      // Handle arrays (like participant_phone, participant_email, etc.)
      if (Array.isArray(value)) {
        // For participant fields, we need to add the right number of participant entries
        if (key.startsWith('participant_')) {
          const participantsContainer = document.getElementById('participants-container');
          if (participantsContainer) {
            // Clear existing participants
            participantsContainer.innerHTML = '';
            
            // Get all participant data fields
            const participantPhones = formData['participant_phone'] || [];
            const participantEmails = formData['participant_email'] || [];
            const participantNames = formData['participant_name'] || [];
            
            // Add participant entries for each phone number
            for (let i = 0; i < participantPhones.length; i++) {
              addParticipantField();
              
              // Get the newly added fields
              const entries = participantsContainer.querySelectorAll('.participant-entry');
              const lastEntry = entries[entries.length - 1];
              
              if (lastEntry) {
                // Set the values
                if (participantPhones[i]) {
                  lastEntry.querySelector('input[name="participant_phone"]').value = participantPhones[i];
                }
                
                if (i < participantEmails.length && participantEmails[i]) {
                  lastEntry.querySelector('input[name="participant_email"]').value = participantEmails[i];
                }
                
                if (i < participantNames.length && participantNames[i]) {
                  lastEntry.querySelector('input[name="participant_name"]').value = participantNames[i];
                }
              }
            }
          }
        }
      } else {
        // Handle regular form fields
        const field = activityForm.querySelector(`[name="${key}"]`);
        if (field) {
          field.value = value;
        }
      }
    }
    
    // Add a visual indicator that the form was restored
    if (shouldRestore) {
      const formIndicator = document.createElement('div');
      formIndicator.className = 'alert alert-success mb-4';
      formIndicator.innerHTML = '<strong>Your activity information has been restored.</strong> Please review your information and click "Invite Participants" to continue.';
      activityForm.prepend(formIndicator);
      
      // Add a highlight to the Invite Participants button
      const inviteBtn = document.getElementById('invite-btn');
      if (inviteBtn) {
        inviteBtn.classList.add('btn-pulse');
        
        // Add the pulse animation style if not already present
        if (!document.getElementById('btn-pulse-style')) {
          const style = document.createElement('style');
          style.id = 'btn-pulse-style';
          style.textContent = `
            @keyframes btnPulse {
              0% { box-shadow: 0 0 0 0 rgba(13, 110, 253, 0.7); }
              70% { box-shadow: 0 0 0 10px rgba(13, 110, 253, 0); }
              100% { box-shadow: 0 0 0 0 rgba(13, 110, 253, 0); }
            }
            
            .btn-pulse {
              animation: btnPulse 1.5s infinite;
              position: relative;
              box-shadow: 0 0 0 0 rgba(13, 110, 253, 1);
            }
          `;
          document.head.appendChild(style);
        }
      }
      
      // Scroll to top of form
      activityForm.scrollIntoView({ behavior: 'smooth' });
      
      // Highlight important fields
      const importantFields = ['activity_name', 'organizer_name', 'organizer_phone', 'organizer_email'];
      importantFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field && field.value) {
          field.classList.add('restored-field');
        }
      });
      
      // Add style for restored fields if not already there
      if (!document.getElementById('restored-field-style')) {
        const style = document.createElement('style');
        style.id = 'restored-field-style';
        style.textContent = `
          @keyframes highlightRestored {
            0% { background-color: rgba(25, 135, 84, 0.1); }
            50% { background-color: rgba(25, 135, 84, 0.2); }
            100% { background-color: transparent; }
          }
          
          .restored-field {
            animation: highlightRestored 2s ease-in-out;
          }
        `;
        document.head.appendChild(style);
      }
    }
    
    // Keep the data in sessionStorage for now unless auto-submitting
    if (document.getElementById('auto_submit_after_login') && 
        document.getElementById('auto_submit_after_login').value === 'true') {
      // Auto-submit the form
      console.log('Auto-submitting form after login');
      sessionStorage.removeItem('activity_form_data'); // Clear data as it will be submitted
      activityForm.submit();
    }
    
  } catch (error) {
    console.error('Error restoring form data:', error);
    // Don't clear the data on error so the user can try again
  }
}
