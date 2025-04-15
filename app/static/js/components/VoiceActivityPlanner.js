import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Send, Volume2, Loader, MessageSquare } from 'lucide-react';

const VoiceActivityPlanner = ({ activityId, participantId, isOrganizer = false }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [preferences, setPreferences] = useState({});
  const messagesEndRef = useRef(null);
  const audioRef = useRef(null);
  
  // Set up speech recognition
  const recognitionRef = useRef(null);
  
  useEffect(() => {
    // Initialize recognition
    if (window.webkitSpeechRecognition || window.SpeechRecognition) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      
      recognitionRef.current.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0])
          .map(result => result.transcript)
          .join('');
          
        setInput(transcript);
      };
      
      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error', event.error);
        setIsRecording(false);
      };
    }
    
    // Add initial welcome message
    const initialMessage = isOrganizer 
      ? "Hi there! I'm your AI Activity Planner. Tell me about the activity you're planning and your group. What kind of experience are you looking to create?"
      : "Hello! I'm your AI Activity Planner. I'd love to hear about your preferences for this group activity. What kinds of activities do you enjoy?";
      
    setMessages([{
      role: 'assistant',
      content: initialMessage
    }]);
    
    // Set up speech synthesis
    if ('speechSynthesis' in window) {
      // Speech synthesis setup
      window.speechSynthesis.onvoiceschanged = () => {
        // This is needed for some browsers
      };
    }
    
    // Load existing preferences if any
    if (activityId && participantId) {
      fetchPreferences();
    }
    
    return () => {
      // Cleanup
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch (e) {
          // Ignore errors on cleanup
        }
      }
      
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, [activityId, participantId, isOrganizer]);
  
  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const fetchPreferences = async () => {
    try {
      // In a real implementation, fetch from your API
      // For demo purposes, we'll use mock data
      const mockPreferences = {
        activity: {
          activity_type: 'Outdoor',
          physical_exertion: 'Medium'
        },
        timing: {
          preferred_day: 'Weekend',
          preferred_time: 'Morning'
        }
      };
      
      setPreferences(mockPreferences);
    } catch (error) {
      console.error('Error fetching preferences:', error);
    }
  };
  
  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert('Speech recognition is not supported in your browser.');
      return;
    }
    
    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      recognitionRef.current.start();
      setIsRecording(true);
    }
  };
  
  const speakText = (text) => {
    if (!('speechSynthesis' in window)) return;
    
    // Cancel any ongoing speech
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    // Get available voices
    const voices = window.speechSynthesis.getVoices();
    
    // Try to find a natural sounding voice
    const preferredVoice = voices.find(voice => 
      voice.name.includes('Google') || voice.name.includes('Natural')
    ) || voices[0];
    
    if (preferredVoice) {
      utterance.voice = preferredVoice;
    }
    
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    
    window.speechSynthesis.speak(utterance);
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    // Stop recording if active
    if (isRecording && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsRecording(false);
    }
    
    // Add user message to chat
    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsProcessing(true);
    
    try {
      // In a real implementation, call your backend API
      // Simulating API call
      setTimeout(() => {
        const response = processMessage(input);
        
        const assistantMessage = { role: 'assistant', content: response.message };
        setMessages(prev => [...prev, assistantMessage]);
        
        // Update preferences if any were extracted
        if (response.preferences) {
          setPreferences(prev => {
            const newPreferences = { ...prev };
            
            // Merge new preferences
            Object.keys(response.preferences).forEach(category => {
              if (!newPreferences[category]) {
                newPreferences[category] = {};
              }
              
              Object.assign(newPreferences[category], response.preferences[category]);
            });
            
            return newPreferences;
          });
        }
        
        setIsProcessing(false);
        
        // Automatically speak the response
        speakText(response.message);
      }, 1500);
      
    } catch (error) {
      console.error('Error processing message:', error);
      const errorMessage = { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error processing your request. Please try again.' 
      };
      setMessages(prev => [...prev, errorMessage]);
      setIsProcessing(false);
    }
  };
  
  // Mock processing function - in a real app this would call your backend
  const processMessage = (message) => {
    const lowerMessage = message.toLowerCase();
    const result = {
      message: '',
      preferences: {
        activity: {},
        timing: {},
        meals: {},
        requirements: {}
      }
    };
    
    // Simple rule-based processing
    if (lowerMessage.includes('outdoor') || lowerMessage.includes('hike') || lowerMessage.includes('park')) {
      result.preferences.activity.activity_type = 'Outdoor';
      result.message = "I see you enjoy outdoor activities! Would you prefer something challenging like hiking or more relaxed like a park visit?";
    } 
    else if (lowerMessage.includes('dinner') || lowerMessage.includes('restaurant') || lowerMessage.includes('food')) {
      result.preferences.activity.activity_type = 'Food';
      result.preferences.meals.meals_included = 'Yes';
      result.message = "A food-focused activity sounds great! Do you have any dietary preferences or restrictions I should know about?";
    }
    else if (lowerMessage.includes('movie') || lowerMessage.includes('theater') || lowerMessage.includes('film')) {
      result.preferences.activity.activity_type = 'Entertainment';
      result.message = "Movies or theater sounds fun! Do you prefer blockbusters or more independent films?";
    }
    else if (lowerMessage.includes('game') || lowerMessage.includes('board game') || lowerMessage.includes('play')) {
      result.preferences.activity.activity_type = 'Games';
      result.message = "Game night is always enjoyable! Do you prefer competitive games, cooperative ones, or party games?";
    }
    else if (lowerMessage.includes('weekend')) {
      result.preferences.timing.preferred_day = 'Weekend';
      result.message = "I've noted your preference for weekend activities. Do you prefer mornings, afternoons, or evenings?";
    }
    else if (lowerMessage.includes('morning') || lowerMessage.includes('afternoon') || lowerMessage.includes('evening')) {
      if (lowerMessage.includes('morning')) {
        result.preferences.timing.preferred_time = 'Morning';
      } else if (lowerMessage.includes('afternoon')) {
        result.preferences.timing.preferred_time = 'Afternoon';
      } else {
        result.preferences.timing.preferred_time = 'Evening';
      }
      result.message = "Great! I've noted your time preference. Any particular activities you enjoy during this time?";
    }
    else if (lowerMessage.includes('anything') || lowerMessage.includes('whatever') || lowerMessage.includes('flexible')) {
      result.preferences.requirements.additional_info = 'Flexible on most aspects';
      result.message = "I appreciate your flexibility! Is there anything specific you'd rather avoid, or any constraints I should keep in mind?";
    }
    else {
      result.message = "Thanks for sharing! Could you tell me more about what kinds of activities you enjoy, or when you'd prefer to do them?";
    }
    
    return result;
  };
  
  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-md overflow-hidden">
      {/* Header */}
      <div className="bg-blue-600 text-white p-4">
        <h3 className="font-bold text-lg">AI Activity Planner</h3>
        <p className="text-sm opacity-80">
          {isOrganizer ? "Plan your perfect group activity" : "Share your activity preferences"}
        </p>
      </div>
      
      {/* Message area */}
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div 
            key={index} 
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div 
              className={`px-4 py-2 rounded-lg max-w-md ${
                message.role === 'user' 
                  ? 'bg-blue-500 text-white rounded-br-none' 
                  : 'bg-gray-100 text-gray-800 rounded-bl-none'
              }`}
            >
              {message.content}
              {message.role === 'assistant' && (
                <button 
                  onClick={() => speakText(message.content)} 
                  className="ml-2 text-xs opacity-70 hover:opacity-100"
                  disabled={isSpeaking}
                >
                  🔊
                </button>
              )}
            </div>
          </div>
        ))}
        
        {/* Typing indicator */}
        {isProcessing && (
          <div className="flex justify-start">
            <div className="px-4 py-2 rounded-lg bg-gray-100 text-gray-800 rounded-bl-none">
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input area */}
      <form onSubmit={handleSubmit} className="border-t p-4 flex items-center space-x-2">
        <button 
          type="button" 
          onClick={toggleRecording} 
          className={`p-2 rounded-full ${isRecording ? 'bg-red-500 text-white' : 'bg-gray-200'}`}
          title={isRecording ? "Stop recording" : "Start voice recording"}
        >
          {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>
        
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type or speak your message..."
          className="flex-1 border rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        
        <button 
          type="submit" 
          className="p-2 bg-blue-500 text-white rounded-full disabled:opacity-50"
          disabled={!input.trim() || isProcessing}
          title="Send message"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>
      
      {/* Right panel for preference summary */}
      {Object.keys(preferences).length > 0 && (
        <div className="border-t p-4">
          <div className="mb-2 flex justify-between items-center">
            <h4 className="font-semibold text-sm text-gray-700">Preferences Summary</h4>
            <button 
              className="text-xs text-blue-500 hover:underline"
              onClick={() => alert('Preferences saved!')}
            >
              Save All
            </button>
          </div>
          <div className="space-y-2 text-sm">
            {Object.entries(preferences).map(([category, prefs]) => (
              <div key={category} className="bg-gray-50 p-2 rounded">
                <div className="font-medium text-gray-700 capitalize">{category}</div>
                <ul className="mt-1 space-y-1">
                  {Object.entries(prefs).map(([key, value]) => (
                    <li key={key} className="flex justify-between">
                      <span className="text-gray-600">
                        {key.replace(/_/g, ' ')}:
                      </span> 
                      <span className="font-medium">{value}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* Hidden audio element for potential audio playback */}
      <audio ref={audioRef} className="hidden" />
    </div>
  );
};

export default VoiceActivityPlanner;
