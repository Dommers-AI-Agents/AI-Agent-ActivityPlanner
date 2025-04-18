// ai-conversation.js - Interactive AI conversation component
function initializeAIConversation(containerId, callbacks) {
  const container = document.getElementById(containerId);
  if (!container) return;
  
  // Create our conversation interface
  createConversationInterface(container, callbacks);
}

function createConversationInterface(container, callbacks) {
  // Create message container
  const messagesContainer = document.createElement('div');
  messagesContainer.className = 'messages-container flex-grow-1 overflow-auto mb-3';
  messagesContainer.style.height = '350px';
  container.appendChild(messagesContainer);
  
  // Add initial AI message
  addMessage(messagesContainer, 'assistant', "Hi there! I'm your AI Activity Planner. Tell me what kind of activity you have in mind, or I can suggest something based on your group's interests and preferences.");
  
  // Create input area
  const inputContainer = document.createElement('div');
  inputContainer.className = 'input-container d-flex align-items-center mt-auto';
  container.appendChild(inputContainer);
  
  // Add voice button
  const voiceButton = document.createElement('button');
  voiceButton.className = 'btn btn-outline-secondary rounded-circle me-2';
  voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
  voiceButton.title = 'Voice input';
  voiceButton.type = 'button';
  
  let isRecording = false;
  let recognition = null;
  
  // Initialize speech recognition if available
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    
    voiceButton.addEventListener('click', function() {
      if (isRecording) {
        recognition.stop();
        voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
        voiceButton.classList.remove('btn-danger');
        voiceButton.classList.add('btn-outline-secondary');
      } else {
        recognition.start();
        voiceButton.innerHTML = '<i class="fas fa-microphone-slash"></i>';
        voiceButton.classList.remove('btn-outline-secondary');
        voiceButton.classList.add('btn-danger');
      }
      isRecording = !isRecording;
    });
    
    inputContainer.appendChild(voiceButton);
  }
  
  // Add text input
  const textInput = document.createElement('input');
  textInput.type = 'text';
  textInput.className = 'form-control mx-2';
  textInput.placeholder = 'Type your message or speak...';
  inputContainer.appendChild(textInput);
  
  // Add send button
  const sendButton = document.createElement('button');
  sendButton.className = 'btn btn-primary';
  sendButton.innerHTML = '<i class="fas fa-paper-plane"></i>';
  sendButton.type = 'button';
  inputContainer.appendChild(sendButton);
  
  // Initialize state for tracking conversation
  let conversationSummary = '';
  let activityType = '';
  let specialConsiderations = '';
  // Keep track of the conversation history
  let conversationHistory = [];
  
  // Hook up recognition events if available
  if (recognition) {
    recognition.onresult = function(event) {
      const transcript = Array.from(event.results)
        .map(result => result[0])
        .map(result => result.transcript)
        .join('');
        
      textInput.value = transcript;
    };
    
    recognition.onerror = function(event) {
      console.error('Speech recognition error', event.error);
      voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
      voiceButton.classList.remove('btn-danger');
      voiceButton.classList.add('btn-outline-secondary');
      isRecording = false;
    };
  }
  
  // Create a temporary activity for API calls
  let tempActivityId = null;
  
  // Create a temporary activity on first message
  async function createTempActivity() {
    try {
      // Call API to create a temporary activity
      console.log("Creating temporary activity for AI conversation...");
      
      // Just use a dummy activity ID for now - this will be replaced when the actual activity is created
      // In a real implementation, we might create a temporary activity via API
      tempActivityId = 'temp-' + Math.random().toString(36).substring(2, 15);
      return tempActivityId;
    } catch (error) {
      console.error('Error creating temporary activity:', error);
      return null;
    }
  }
  
  // Handle sending messages
  async function handleSendMessage() {
    const message = textInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessage(messagesContainer, 'user', message);
    textInput.value = '';
    
    // Add to conversation history 
    conversationHistory.push({role: 'user', content: message});
    
    // Stop recording if active
    if (isRecording && recognition) {
      recognition.stop();
      voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
      voiceButton.classList.remove('btn-danger');
      voiceButton.classList.add('btn-outline-secondary');
      isRecording = false;
    }
    
    // Show thinking indicator
    const thinkingId = 'thinking-' + Date.now();
    addMessage(messagesContainer, 'assistant', 'Thinking...', 'thinking', thinkingId);
    
    try {
      // Ensure we have an activity ID, even if temporary
      if (!tempActivityId) {
        tempActivityId = await createTempActivity();
      }
      
      let response;
      
      // For real API use, call the backend
      try {
        // First try the real API endpoint
        response = await callBackendApi(tempActivityId, message);
        console.log("API response:", response);
      } catch (apiError) {
        console.error('Error calling backend API, falling back to local processing:', apiError);
        // Fall back to local processing if API call fails
        response = processMessageLocally(message);
      }
      
      // Remove thinking indicator
      const thinkingElem = document.getElementById(thinkingId);
      if (thinkingElem) {
        thinkingElem.remove();
      }
      
      // Display the AI's response
      let displayMessage = "";
      
      if (typeof response === 'string') {
        displayMessage = response;
      } else if (response && typeof response === 'object') {
        if (response.message) {
          // Normal object response
          displayMessage = response.message;
        } else if (response.error) {
          displayMessage = `Error: ${response.error}`;
        }
      }
      
      // Try to handle JSON string if that's what we got
      if (typeof displayMessage === 'string' && displayMessage.trim().startsWith('{')) {
        try {
          const parsed = JSON.parse(displayMessage);
          if (parsed && parsed.message) {
            displayMessage = parsed.message;
            // Update extracted info if available
            if (parsed.extracted_info && !response.extracted_info) {
              response.extracted_info = parsed.extracted_info;
            }
          }
        } catch (e) {
          console.error("Error parsing JSON string:", e);
          // Leave displayMessage as is
        }
      }
      
      // Add message to chat
      addMessage(messagesContainer, 'assistant', displayMessage);
      
      // Add to conversation history
      conversationHistory.push({
        role: 'assistant', 
        content: displayMessage
      });
      
      // Update preferences based on response
      if (response.extracted_info || (response.plan && Object.keys(response.plan).length > 0)) {
        console.log("Extracted info or plan found:", response.extracted_info || response.plan);
        
        // Save activity type if available
        const extractedInfo = response.extracted_info || {};
        
        if (extractedInfo.activity_type) {
          activityType = extractedInfo.activity_type;
          if (callbacks && callbacks.onUpdateActivityType) {
            callbacks.onUpdateActivityType(activityType);
          }
        }
        
        // Save special considerations if available
        if (extractedInfo.special_requirements) {
          specialConsiderations = extractedInfo.special_requirements;
          if (callbacks && callbacks.onUpdateConsiderations) {
            callbacks.onUpdateConsiderations(specialConsiderations);
          }
        }
        
        // Update the activity description using extracted info
        updatePlanDescription(extractedInfo, response.plan);
      }
      
      // If we have a plan, log it and create a visual representation
      if (response.plan) {
        console.log("Plan:", response.plan);
        createPlanVisualization(response.plan);
      }
      
      // Update conversation summary
      updateSummary();
    } catch (error) {
      console.error('Error processing message:', error);
      
      // Remove thinking indicator
      const thinkingElem = document.getElementById(thinkingId);
      if (thinkingElem) {
        thinkingElem.remove();
      }
      
      // Show the specific error message if available
      const errorMessage = error.message || 'Sorry, I encountered an error. Please try again.';
      addMessage(messagesContainer, 'assistant', errorMessage);
    }
  }

  // Helper function to create a visual representation of the plan
  function createPlanVisualization(plan) {
    // Check if we need to create a plan section
    const existingPlanSection = document.getElementById('plan-visualization');
    if (existingPlanSection) {
      existingPlanSection.remove();
    }
    
    // Create plan section
    const planSection = document.createElement('div');
    planSection.id = 'plan-visualization';
    planSection.className = 'card mt-4 mb-4';
    
    // Create plan header
    const planHeader = document.createElement('div');
    planHeader.className = 'card-header';
    planHeader.innerHTML = `<h5 class="mb-0">${plan.title || 'Activity Plan'}</h5>`;
    
    // Create plan body
    const planBody = document.createElement('div');
    planBody.className = 'card-body';
    
    // Add description
    if (plan.description) {
      const descDiv = document.createElement('div');
      descDiv.className = 'mb-3';
      descDiv.innerHTML = plan.description.replace(/\n/g, '<br>');
      planBody.appendChild(descDiv);
    }
    
    // Add schedule if available
    if (plan.schedule && Array.isArray(plan.schedule)) {
      const scheduleDiv = document.createElement('div');
      scheduleDiv.className = 'mt-3';
      scheduleDiv.innerHTML = '<h6>Schedule:</h6>';
      
      const scheduleList = document.createElement('ul');
      scheduleList.className = 'list-group';
      
      plan.schedule.forEach(item => {
        const scheduleItem = document.createElement('li');
        scheduleItem.className = 'list-group-item';
        scheduleItem.innerHTML = `<strong>${item.time}:</strong> ${item.activity}`;
        scheduleList.appendChild(scheduleItem);
      });
      
      scheduleDiv.appendChild(scheduleList);
      planBody.appendChild(scheduleDiv);
    }
    
    // Add considerations if available
    if (plan.considerations) {
      const considerationsDiv = document.createElement('div');
      considerationsDiv.className = 'mt-3';
      considerationsDiv.innerHTML = `<h6>Special Considerations:</h6><p>${plan.considerations}</p>`;
      planBody.appendChild(considerationsDiv);
    }
    
    // Add alternatives if available
    if (plan.alternatives && Array.isArray(plan.alternatives)) {
      const alternativesDiv = document.createElement('div');
      alternativesDiv.className = 'mt-3';
      alternativesDiv.innerHTML = '<h6>Alternative Options:</h6>';
      
      const alternativesList = document.createElement('ul');
      
      plan.alternatives.forEach(alt => {
        const altItem = document.createElement('li');
        altItem.textContent = alt;
        alternativesList.appendChild(altItem);
      });
      
      alternativesDiv.appendChild(alternativesList);
      planBody.appendChild(alternativesDiv);
    }
    
    // Assemble plan section
    planSection.appendChild(planHeader);
    planSection.appendChild(planBody);
    
    // Add to container
    messagesContainer.appendChild(planSection);
    
    // Scroll to the plan
    planSection.scrollIntoView({ behavior: 'smooth' });
  }

  // Helper function to update the activity description based on extracted info
  function updatePlanDescription(extractedInfo, plan) {
    const descriptionField = document.getElementById('activity_description');
    if (!descriptionField) return;
    
    // Start building an informative description
    let description = "";
    
    // Use the plan description if available
    if (plan && plan.description) {
      description = plan.description + "\n\n";
    } else {
      // Build from extracted info
      if (extractedInfo.activity_type) {
        description += `# ${extractedInfo.activity_type}\n\n`;
      } else {
        description += "# Group Activity Plan\n\n";
      }
      
      if (extractedInfo.group_size || extractedInfo.group_composition) {
        description += `**Group:** ${extractedInfo.group_composition || extractedInfo.group_size || ''}\n\n`;
      }
      
      if (extractedInfo.location) {
        description += `**Location:** ${extractedInfo.location}\n\n`;
      }
      
      if (extractedInfo.timing || extractedInfo.duration) {
        description += `**Timing:** ${extractedInfo.timing || ''} ${extractedInfo.duration ? `(${extractedInfo.duration})` : ''}\n\n`;
      }
      
      if (extractedInfo.transportation) {
        description += `**Transportation:** ${extractedInfo.transportation}\n\n`;
      }
      
      if (extractedInfo.budget) {
        description += `**Budget:** ${extractedInfo.budget}\n\n`;
      }
      
      if (extractedInfo.meals) {
        description += `**Meals:** ${extractedInfo.meals}\n\n`;
      }
      
      if (extractedInfo.special_requirements) {
        description += `**Special Considerations:** ${extractedInfo.special_requirements}\n\n`;
      }
    }
    
    // If we have plan schedule, add it
    if (plan && plan.schedule && Array.isArray(plan.schedule)) {
      description += "## Schedule\n\n";
      
      plan.schedule.forEach(item => {
        description += `**${item.time}:** ${item.activity}\n\n`;
      });
    }
    
    // Update the field
    descriptionField.value = description;
  }

  // Function to call the backend API
  async function callBackendApi(activityId, message) {
    // We'll try to use the conversation API endpoint if it exists
    const url = `/api/ai/planner/converse`;
    
    console.log("Calling backend API with URL:", url);
    console.log("Message:", message);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ 
        input: message,
        conversation_history: conversationHistory
      }),
    });
    
    if (!response.ok) {
      if (response.status === 503) {
        // Service unavailable (Claude not available)
        const errorData = await response.json();
        throw new Error(errorData.message || "Claude AI is currently unavailable");
      }
      throw new Error(`API request failed with status ${response.status}`);
    }
    
    // Get the response JSON
    let data;
    try {
      data = await response.json();
      console.log("API response data:", data);
    } catch (e) {
      console.error("Failed to parse API response as JSON:", e);
      const text = await response.text();
      return {
        message: text,
        extracted_info: {}
      };
    }
    
    // Check if we have a message field
    if (data && data.message) {
      // Check if the message itself is a JSON string
      if (typeof data.message === 'string' && data.message.trim().startsWith('{')) {
        try {
          const parsedMsg = JSON.parse(data.message);
          if (parsedMsg && parsedMsg.message) {
            // Replace the message with the parsed inner message
            data.message = parsedMsg.message;
            
            // Update extracted_info if available in the nested JSON
            if (parsedMsg.extracted_info) {
              data.extracted_info = parsedMsg.extracted_info;
            }
          }
        } catch (e) {
          console.error("Failed to parse nested JSON in message:", e);
          // Keep the original message
        }
      }
      
      // Return the clean data
      return {
        message: data.message,
        extracted_info: data.extracted_info || {},
        plan: data.plan || null
      };
    } else if (data.error) {
      throw new Error(data.error);
    } else {
      throw new Error('Invalid API response format');
    }
  }
  
  // Function to update summary based on conversation
  function updateSummary() {
    console.log("Updating summary with conversation history:", conversationHistory);
    
    // Create a structured itinerary based on extracted info
    let activityItinerary = '';
    
    // Extract relevant information from conversation history
    let location = '';
    let dateTime = '';
    let groupSize = '';
    let duration = '';
    let transportationInfo = '';
    let mealInfo = '';
    let budget = '';
    let fullItinerary = null;
    
    // First, check the last response for complete information
    if (conversationHistory.length > 0) {
      // Get the last assistant message
      const lastMessages = conversationHistory.filter(msg => msg.role === 'assistant');
      if (lastMessages.length > 0) {
        const lastMsg = lastMessages[lastMessages.length - 1];
        
        // Check if it has extracted_info
        if (lastMsg.extracted_info) {
          const info = lastMsg.extracted_info;
          console.log("Last message extracted info:", info);
          
          // Update activity type if available
          if (info.activity_type && info.activity_type !== "null") {
            activityType = info.activity_type;
          }
          
          // Check if the response has a detailed itinerary paragraph
          if (lastMsg.content && lastMsg.content.includes("Depart") && 
              lastMsg.content.includes("Arrive") && 
              lastMsg.content.length > 200) {
            fullItinerary = lastMsg.content;
          }
          
          // Update all fields from the extracted info
          if (info.activity_type && info.activity_type !== "null") activityType = info.activity_type;
          if (info.location && info.location !== "null") location = info.location;
          if (info.timing && info.timing !== "null") dateTime = info.timing;
          if (info.group_size && info.group_size !== "null") groupSize = info.group_size;
          if (info.group_composition && info.group_composition !== "null") {
            if (groupSize === '') groupSize = info.group_composition;
            else groupSize += ` (${info.group_composition})`;
          }
          if (info.duration && info.duration !== "null") duration = info.duration;
          if (info.transportation && info.transportation !== "null") transportationInfo = info.transportation;
          if (info.budget && info.budget !== "null") budget = info.budget;
          if (info.special_requirements && info.special_requirements !== "null") specialConsiderations = info.special_requirements;
          if (info.meals && info.meals !== "null") mealInfo = info.meals;
        }
      }
    }
    
    // Check if we have a plan object in any of the responses
    let fullPlan = null;
    for (let i = 0; i < conversationHistory.length; i++) {
      const msg = conversationHistory[i];
      if (msg.role === 'assistant' && msg.plan) {
        fullPlan = msg.plan;
        break;
      }
    }
    
    // Add a title based on the activity type
    if (activityType) {
      activityItinerary += `# ${activityType} Itinerary\n\n`;
    } else {
      activityItinerary += '# Activity Itinerary\n\n';
    }
    
    // If we have a full itinerary from Claude, use that directly
    if (fullItinerary) {
      // Parse the itinerary into a structured format
      activityItinerary += "## Detailed Schedule\n\n";
      
      // Try to split the itinerary into individual steps
      const lines = fullItinerary.split("\n");
      let formattedItinerary = "";
      
      for (const line of lines) {
        // Look for time patterns like "9:00 AM -" or "9:00 AM to"
        if (line.match(/\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\s*[-–—]\s*/) || 
            line.match(/\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)\s*to\s*/)) {
          formattedItinerary += `${line.trim()}\n\n`;
        } else if (line.trim().length > 0) {
          // For other non-empty lines, just add them
          formattedItinerary += `${line.trim()}\n\n`;
        }
      }
      
      // If we couldn't properly format it, just use the original text
      if (formattedItinerary.trim().length === 0) {
        formattedItinerary = fullItinerary;
      }
      
      activityItinerary += formattedItinerary + "\n";
    } else {
      // Build the structured itinerary from individual pieces
      if (groupSize) {
        activityItinerary += `**Group Size:** ${groupSize}\n\n`;
      }
      
      if (location) {
        activityItinerary += `**Location:** ${location}\n\n`;
      }
      
      if (dateTime) {
        activityItinerary += `**Date/Time:** ${dateTime}\n\n`;
      }
      
      if (duration) {
        activityItinerary += `**Duration:** ${duration}\n\n`;
      }
      
      if (transportationInfo) {
        activityItinerary += `**Transportation:** ${transportationInfo}\n\n`;
      }
      
      if (budget) {
        activityItinerary += `**Budget:** ${budget}\n\n`;
      }
      
      // Add any special considerations
      if (specialConsiderations) {
        activityItinerary += `**Special Considerations:**\n${specialConsiderations}\n\n`;
      }
      
      // Add meal information if available
      if (mealInfo) {
        activityItinerary += `**Meals:** ${mealInfo}\n\n`;
      }
      
      // If we don't have a full itinerary, add a note that this is a draft
      if (!fullPlan) {
        activityItinerary += "This itinerary will be updated as you continue planning with the AI assistant.\n";
      }
    }
    
    // If we have a full plan, add that at the end
    if (fullPlan) {
      activityItinerary += "\n## AI-Generated Plan\n\n";
      
      if (fullPlan.description) {
        activityItinerary += `${fullPlan.description}\n\n`;
      }
      
      if (fullPlan.schedule && Array.isArray(fullPlan.schedule)) {
        activityItinerary += "### Schedule\n\n";
        fullPlan.schedule.forEach(item => {
          activityItinerary += `**${item.time}** - ${item.activity}\n\n`;
        });
      }
      
      if (fullPlan.considerations) {
        activityItinerary += "### Special Considerations\n\n";
        activityItinerary += `${fullPlan.considerations}\n\n`;
      }
      
      if (fullPlan.alternatives && Array.isArray(fullPlan.alternatives)) {
        activityItinerary += "### Alternative Options\n\n";
        fullPlan.alternatives.forEach((alt, index) => {
          activityItinerary += `${index + 1}. ${alt}\n`;
        });
        activityItinerary += "\n";
      }
    }
    
    // Update the activity description field directly
    const descriptionField = document.getElementById('activity_description');
    if (descriptionField) {
      descriptionField.value = activityItinerary;
    }
    
    // Update the summary field for callbacks
    conversationSummary = activityType || "Activity Plan";
    if (callbacks && callbacks.onUpdateSummary) {
      callbacks.onUpdateSummary(conversationSummary);
    }
    
    console.log("Updated activity description:", activityItinerary);
  }
  
  // Fallback local processing function for when API is unavailable
  function processMessageLocally(message) {
    const lowerMessage = message.toLowerCase();
    let response = {
      message: '',
      extracted_info: {}
    };
    
    // Simple pattern matching for fallback behavior
    if (lowerMessage.includes('outdoor') || lowerMessage.includes('hike') || lowerMessage.includes('park')) {
      response.message = "A hiking trip sounds wonderful! Would you prefer a challenging trail or something more relaxed? I can help plan activities that accommodate different fitness levels in your group.";
      response.extracted_info.activity_type = "outdoor hiking";
      
      if (lowerMessage.includes('kids') || lowerMessage.includes('children')) {
        response.extracted_info.special_requirements = "Family-friendly, suitable for children";
      } else if (lowerMessage.includes('senior') || lowerMessage.includes('older')) {
        response.extracted_info.special_requirements = "Accessible paths, moderate pace";
      }
      
    } else if (lowerMessage.includes('dinner') || lowerMessage.includes('restaurant') || lowerMessage.includes('food')) {
      response.message = "I'd be happy to plan a group dinner! What kind of cuisine does your group enjoy? I can also suggest restaurants that accommodate various dietary restrictions.";
      response.extracted_info.activity_type = "group dinner";
      
      if (lowerMessage.includes('vegan') || lowerMessage.includes('vegetarian')) {
        response.extracted_info.special_requirements = "Plant-based food options required";
      } else if (lowerMessage.includes('allerg')) {
        response.extracted_info.special_requirements = "Food allergies to consider";
      }
      
    } else if (lowerMessage.includes('movie') || lowerMessage.includes('theater') || lowerMessage.includes('film')) {
      response.message = "A movie night is a great choice! Would you like to go to a theater or plan something at home? I can help coordinate showtimes or suggest films based on your group's interests.";
      response.extracted_info.activity_type = "movie night";
      
      if (lowerMessage.includes('kids') || lowerMessage.includes('children')) {
        response.extracted_info.special_requirements = "Family-friendly movie selection";
      }
      
    } else if (lowerMessage.includes('game') || lowerMessage.includes('board game') || lowerMessage.includes('play')) {
      response.message = "Game night is always fun! Do you have specific games in mind, or would you like me to suggest some based on your group size and preferences?";
      response.extracted_info.activity_type = "game night";
      
      if (lowerMessage.includes('competitive')) {
        response.extracted_info.special_requirements = "Competitive games preferred";
      } else if (lowerMessage.includes('cooperative') || lowerMessage.includes('co-op')) {
        response.extracted_info.special_requirements = "Cooperative games preferred";
      }
      
    } else if (lowerMessage.includes('suggest') || lowerMessage.includes('idea') || lowerMessage.includes('recommend') || lowerMessage.includes('surprise')) {
      response.message = "I'd be happy to suggest some activities! Some popular group activities include hiking in a scenic park, having a picnic, visiting a museum, cooking class, escape room, board game night, or attending a local sports event. Is there a particular category that interests your group?";
      response.extracted_info.activity_type = "variety of options";
      
    } else if (lowerMessage.includes('hello') || lowerMessage.includes('hi') || lowerMessage.includes('hey')) {
      response.message = "Hello! I'm here to help plan your group activity. What type of activity are you interested in? Or would you like me to suggest some ideas?";
    } else {
      // Generic response for any other input
      response.message = "Thanks for sharing those details! To help create the perfect plan, could you tell me a bit more about your group size and whether you have any specific preferences for location or budget?";
      
      // Set a basic activity type if we can detect any keywords
      if (lowerMessage.includes('budget')) {
        response.extracted_info.special_requirements = "Budget is a priority";
      }
      if (lowerMessage.includes('people') || lowerMessage.includes('group')) {
        const match = lowerMessage.match(/(\d+)\s+people/);
        if (match) {
          response.extracted_info.group_size = match[1];
        }
      }
    }
    
    return response;
  }
  
  // Event listeners
  sendButton.addEventListener('click', handleSendMessage);
  
  textInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  });
}

function addMessage(container, role, content, className = '', id = '') {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role} mb-3 ${role === 'user' ? 'text-end' : ''}`;
  if (id) {
    messageDiv.id = id;
  }
  
  const bubble = document.createElement('div');
  bubble.className = `message-bubble d-inline-block px-3 py-2 rounded ${role === 'user' ? 'bg-primary text-white' : 'bg-light'}`;
  bubble.textContent = content;
  
  messageDiv.appendChild(bubble);
  container.appendChild(messageDiv);
  
  // Scroll to bottom
  container.scrollTop = container.scrollHeight;
  
  // If it's an assistant message, add text-to-speech functionality
  if (role === 'assistant' && 'speechSynthesis' in window && className !== 'thinking') {
    const speakButton = document.createElement('button');
    speakButton.className = 'btn btn-sm btn-link p-0 ms-2';
    speakButton.innerHTML = '🔊';
    speakButton.title = 'Listen';
    speakButton.type = 'button';
    
    speakButton.addEventListener('click', function() {
      const utterance = new SpeechSynthesisUtterance(content);
      window.speechSynthesis.speak(utterance);
    });
    
    bubble.appendChild(document.createElement('br'));
    bubble.appendChild(speakButton);
  }
}