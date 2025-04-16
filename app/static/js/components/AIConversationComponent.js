import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Send, Loader } from 'lucide-react';

const AIConversationComponent = () => {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi there! I\'m your AI Activity Planner. Tell me what kind of activity you have in mind, or I can suggest something based on your group\'s interests and preferences.' }
  ]);
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef(null);
  const [recognitionInstance, setRecognitionInstance] = useState(null);
  
  // Speech recognition setup
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      
      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0])
          .map(result => result.transcript)
          .join('');
          
        setInput(transcript);
      };
      
      recognition.onerror = (event) => {
        console.error('Speech recognition error', event.error);
        setIsRecording(false);
      };
      
      setRecognitionInstance(recognition);
    }
  }, []);
  
  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const toggleRecording = () => {
    if (!recognitionInstance) {
      alert('Speech recognition is not supported in your browser.');
      return;
    }
    
    if (isRecording) {
      recognitionInstance.stop();
    } else {
      recognitionInstance.start();
    }
    
    setIsRecording(!isRecording);
  };
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    // Add user message to chat
    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsProcessing(true);
    
    try {
      // In a real implementation, this would call your backend API
      // that integrates with an LLM for natural language understanding
      // For demonstration, we'll simulate a response
      setTimeout(() => {
        const mockResponse = getMockResponse(input);
        setMessages(prev => [...prev, { role: 'assistant', content: mockResponse }]);
        setIsProcessing(false);
      }, 1000);
      
    } catch (error) {
      console.error('Error processing message:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error processing your request. Please try again.' 
      }]);
      setIsProcessing(false);
    }
  };
  
  // Function to speak text using speech synthesis
  const speakText = (text) => {
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(text);
      window.speechSynthesis.speak(utterance);
    }
  };
  
  // Mock response function (to be replaced with actual backend call)
  const getMockResponse = (userInput) => {
    const input = userInput.toLowerCase();
    
    if (input.includes('outdoor') || input.includes('hike') || input.includes('park')) {
      return "A hiking trip sounds wonderful! Would you prefer a challenging trail or something more relaxed? I can help plan activities that accommodate different fitness levels in your group.";
    } else if (input.includes('dinner') || input.includes('restaurant') || input.includes('food')) {
      return "I'd be happy to plan a group dinner! What kind of cuisine does your group enjoy? I can also suggest restaurants that accommodate various dietary restrictions.";
    } else if (input.includes('movie') || input.includes('theater') || input.includes('film')) {
      return "A movie night is a great choice! Would you like to go to a theater or plan something at home? I can help coordinate showtimes or suggest films based on your group's interests.";
    } else if (input.includes('game') || input.includes('board game') || input.includes('play')) {
      return "Game night is always fun! Do you have specific games in mind, or would you like me to suggest some based on your group size and preferences?";
    } else if (input.includes('suggest') || input.includes('idea') || input.includes('recommend')) {
      return "I'd be happy to suggest some activities! To help me make better recommendations, could you tell me a bit about your group? How many people, age range, and any particular interests or constraints I should consider?";
    } else if (input.includes('hello') || input.includes('hi') || input.includes('hey')) {
      return "Hello! I'm here to help plan your group activity. What type of activity are you interested in? Or would you like me to suggest some ideas?";
    } else {
      // More personalized fallback response
      return "I'm analyzing your input to create a personalized activity plan. Could you tell me more about your preferences for location, budget, or type of activity?";
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-md">
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
                  className="ml-2 text-xs underline"
                >
                  🔊 Listen
                </button>
              )}
            </div>
          </div>
        ))}
        {isProcessing && (
          <div className="flex justify-start">
            <div className="px-4 py-2 rounded-lg max-w-md bg-gray-100 text-gray-800 rounded-bl-none flex items-center">
              <Loader className="w-4 h-4 animate-spin mr-2" />
              Thinking...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <form onSubmit={handleSubmit} className="border-t p-4 flex items-center space-x-2">
        <button 
          type="button" 
          onClick={toggleRecording} 
          className={`p-2 rounded-full ${isRecording ? 'bg-red-500 text-white' : 'bg-gray-200'}`}
        >
          {isRecording ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
        </button>
        
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message or speak..."
          className="flex-1 border rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        
        <button 
          type="submit" 
          className="p-2 bg-blue-500 text-white rounded-full disabled:opacity-50"
          disabled={!input.trim() || isProcessing}
        >
          <Send className="w-5 h-5" />
        </button>
      </form>
    </div>
  );
};

export default AIConversationComponent;
