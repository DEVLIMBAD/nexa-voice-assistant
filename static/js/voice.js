// Text-to-Speech functionality
function speakText(text) {
    if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        
        // Try to find a female voice
        const voices = window.speechSynthesis.getVoices();
        const femaleVoice = voices.find(voice => 
            voice.lang.includes('en') && voice.name.toLowerCase().includes('female')
        );
        
        if (femaleVoice) {
            utterance.voice = femaleVoice;
        }
        
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        
        window.speechSynthesis.speak(utterance);
    }
}

// Listen for responses from ALEX to speak them
document.addEventListener('DOMContentLoaded', function() {
    // This would be integrated with the message receiving system
    // For example, when receiving a response from the server:
    /*
    fetch('/command', {...})
        .then(...)
        .then(data => {
            if (data.response) {
                speakText(data.response);
            }
        });
    */
});

// Ensure voices are loaded
window.speechSynthesis.onvoiceschanged = function() {
    // Voices are now loaded
};