// ai-conversation.js - React component for AI conversation
function initializeAIConversation(containerId, callbacks) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // This function would render the React component
  // The actual implementation would use ReactDOM.render with the React component
  // For demonstration purposes, we'll create a mock implementation
  
  // Create our conversation interface
  createConversationInterface(container, callbacks);
}

function createConversationInterface(container, callbacks) {
  // In a full implementation, this would use React
  // For demonstration, we'll create a simple DOM-based interface
  
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
  
  // Handle sending messages
  function handleSendMessage() {
    const message = textInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessage(messagesContainer, 'user', message);
    textInput.value = '';
    
    // Stop recording if active
    if (isRecording && recognition) {
      recognition.stop();
      voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
      voiceButton.classList.remove('btn-danger');
      voiceButton.classList.add('btn-outline-secondary');
      isRecording = false;
    }
    
    // Process message and get AI response
    setTimeout(() => {
      const response = processMessage(message);
      addMessage(messagesContainer, 'assistant', response.message);
      
      // Update hidden form fields via callbacks
      if (response.activityType) {
        activityType = response.activityType;
        if (callbacks && callbacks.onUpdateActivityType) {
          callbacks.onUpdateActivityType(activityType);
        }
      }
      
      if (response.considerations) {
        specialConsiderations = response.considerations;
        if (callbacks && callbacks.onUpdateConsiderations) {
          callbacks.onUpdateConsiderations(specialConsiderations);
        }
      }
      
      // Update conversation summary
      conversationSummary = `Activity Type: ${activityType || 'Not specified'}. Special Considerations: ${specialConsiderations || 'None'}.`;
      if (callbacks && callbacks.onUpdateSummary) {
        callbacks.onUpdateSummary(conversationSummary);
      }
    }, 1000);
  }
  
  // Event listeners
  sendButton.addEventListener('click', handleSendMessage);
  
  textInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      handleSendMessage();
    }
  });
}

function addMessage(container, role, content) {
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${role} mb-3 ${role === 'user' ? 'text-end' : ''}`;
  
  const bubble = document.createElement('div');
  bubble.className = `message-bubble d-inline-block px-3 py-2 rounded ${role === 'user' ? 'bg-primary text-white' : 'bg-light'}`;
  bubble.textContent = content;
  
  messageDiv.appendChild(bubble);
  container.appendChild(messageDiv);
  
  // Scroll to bottom
  container.scrollTop = container.scrollHeight;
  
  // If it's an assistant message, add text-to-speech functionality
  if (role === 'assistant' && 'speechSynthesis' in window) {
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

function processMessage(message) {
  // This is a mock implementation of natural language processing
  // In a real implementation, this would call an API endpoint
  // that interfaces with a language model
  
  const lowerMessage = message.toLowerCase();
  let response = {
    message: '',
    activityType: '',
    considerations: ''
  };
  
  // Simple rule-based responses
  if (lowerMessage.includes('outdoor') || lowerMessage.includes('hike') || lowerMessage.includes('park')) {
    response.message = "A hiking trip sounds wonderful! Would you prefer a challenging trail or something more relaxed? I can help plan activities that accommodate different fitness levels in your group.";
    response.activityType = "outdoor hiking";
    
    if (lowerMessage.includes('kids') || lowerMessage.includes('children')) {
      response.considerations = "Family-friendly, suitable for children";
    } else if (lowerMessage.includes('senior') || lowerMessage.includes('older')) {
      response.considerations = "Accessible paths, moderate pace";
    }
    
  } else if (lowerMessage.includes('dinner') || lowerMessage.includes('restaurant') || lowerMessage.includes('food')) {
    response.message = "I'd be happy to plan a group dinner! What kind of cuisine does your group enjoy? I can also suggest restaurants that accommodate various dietary restrictions.";
    response.activityType = "group dinner";
    
    if (lowerMessage.includes('vegan') || lowerMessage.includes('vegetarian')) {
      response.considerations = "Plant-based food options required";
    } else if (lowerMessage.includes('allerg')) {
      response.considerations = "Food allergies to consider";
    }
    
  } else if (lowerMessage.includes('movie') || lowerMessage.includes('theater') || lowerMessage.includes('film')) {
    response.message = "A movie night is a great choice! Would you like to go to a theater or plan something at home? I can help coordinate showtimes or suggest films based on your group's interests.";
    response.activityType = "movie night";
    
    if (lowerMessage.includes('kids') || lowerMessage.includes('children')) {
      response.considerations = "Family-friendly movie selection";
    }
    
  } else if (lowerMessage.includes('game') || lowerMessage.includes('board game') || lowerMessage.includes('play')) {
    response.message = "Game night is always fun! Do you have specific games in mind, or would you like me to suggest some based on your group size and preferences?";
    response.activityType = "game night";
    
    if (lowerMessage.includes('competitive')) {
      response.considerations = "Competitive games preferred";
    } else if (lowerMessage.includes('cooperative') || lowerMessage.includes('co-op')) {
      response.considerations = "Cooperative games preferred";
    }
    
  } else if (lowerMessage.includes('suggest') || lowerMessage.includes('idea') || lowerMessage.includes('recommend')) {
    response.message = "I'd be happy to suggest some activities! To help me make better recommendations, could you tell me a bit about your group? How many people, age range, and any particular interests or constraints I should consider?";
    
  } else {
    response.message = "Thanks for sharing your thoughts! To help plan the perfect activity, could you tell me more about your group? How many people will be participating, and are there any specific preferences or constraints I should know about?";
  }
  
  return response;
}
