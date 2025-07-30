document.addEventListener('DOMContentLoaded', function() {
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const voiceButton = document.getElementById('voiceButton');
    const waveAnimation = document.getElementById('waveAnimation');
    const chatHistory = document.getElementById('chatHistory');
    const quickButtons = document.querySelectorAll('.quick-btn');
    
    // Speech recognition setup
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;
    
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-UK';
        
        recognition.onstart = function() {
            voiceButton.classList.add('listening');
            waveAnimation.classList.remove('hidden');
        };
        
        recognition.onend = function() {
            voiceButton.classList.remove('listening');
            waveAnimation.classList.add('hidden');
        };
        
        recognition.onresult = function(event) {
            const transcript = event.results[0][0].transcript;
            userInput.value = transcript;
            sendCommand(transcript);
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error', event.error);
            addMessage('ALEX', "Sorry, I didn't catch that. Could you try again?");
        };
    } else {
        voiceButton.style.display = 'none';
        console.warn('Speech recognition not supported in this browser');


        addMessageaddMessage('ALEX', "Voice input is not supported in this browser. Please use Chrome.");
        // voiceButton.disabled = true;
        // voiceButton.title = "Voice input not supported in this browser";
        // voiceButton.style.opacity = 0.5;
    }
    
    // Event listeners
    sendButton.addEventListener('click', () => {
        if (userInput.value.trim()) {
            sendCommand(userInput.value);
            userInput.value = '';
        }
    });
    
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && userInput.value.trim()) {
            sendCommand(userInput.value);
            userInput.value = '';
        }
    });
    
    if (recognition) {
        voiceButton.addEventListener('click', () => {
            if (voiceButton.classList.contains('listening')) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
    }
    
    quickButtons.forEach(button => {
        button.addEventListener('click', () => {
            const command = button.getAttribute('data-command');
            sendCommand(command);
        });
    });
    
    // Function to send command to backend
    function sendCommand(command) {
        addMessage('You', command);
        
        fetch('/command', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ command: command })
        })
        .then(response => response.json())
        .then(data => {
            if (data.response) {
                addMessage('ALEX', data.response);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            addMessage('ALEX', "Sorry, I'm having trouble connecting to the server.");
        });
    }
    
    // Function to add message to chat
    function addMessage(sender, text) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add(sender === 'You' ? 'user-message' : 'assistant-message');
        
        if (sender === 'You') {
            messageDiv.innerHTML = `
                <div class="message-content">
                    <p>${text}</p>
                </div>
                <div class="avatar">
                    <i class="fas fa-user"></i>
                </div>
            `;
        } else {
            messageDiv.innerHTML = `
                <div class="avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <p>${text}</p>
                </div>
            `;
        }
        
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
});