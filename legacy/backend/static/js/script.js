var username = "{{ username }}";
var botLogoURL = "../static/images/Logo.png";

autosize(document.getElementById('message-input'));

var chatBox = document.getElementById('chat-box');

document.getElementById('button-addon2').addEventListener('click', function(event) {
    sendMessage();
});

document.getElementById('message-input').addEventListener('keydown', function(event) {
    if (event.key === 'Enter') {
        event.preventDefault();  // Prevent newline
        sendMessage();
    }
});

function sendMessage() {
    var messageText = document.getElementById('message-input').value.trim();
    if (!messageText) return;
    generateUserMessage(messageText);

    document.getElementById('message-input').value = '';

    // Show typing indicator and delay the bot response
    addTypingAnimation();
    // Scroll to the bottom of the chat box
    chatBox.scrollTop = chatBox.scrollHeight;

    fetch("/send", {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ "message": messageText })
    }).then(response => response.json()).then(response => {
        deleteTypingAnimation();
        generateBotMessage(response.message);
        chatBox.scrollTop = chatBox.scrollHeight;
    });
}

function generateUserMessage(text) {
    var wrapper = document.createElement('div');
    wrapper.className = 'media w-50 ml-auto mb-3';
    wrapper.innerHTML = `
    <div class="media-body">
        <p class="text-small mb-1 text-muted"><span class="mr-1">👨‍🎓</span>${username} <span class="small text-muted">${getCurrentDateTimeString()}</span></p>
        <div class="bg-primary rounded py-2 px-3 mb-2">
            <p class="text-small mb-0 text-white">${text}</p>
        </div>
    </div>
    `;
    chatBox.appendChild(wrapper);
}

function generateBotMessage(text) {
    delete_rating_stars();

    var wrapper = document.createElement('div');
    wrapper.className = 'media w-50 mb-3';
    wrapper.innerHTML = `
    <div class="media-body ml-3">
    <p class="text-small mb-1 text-muted"><span class="mr-1"><img src="${botLogoURL}" width="32" height="32"></span>Tutor AI <span class="small text-muted">${getCurrentDateTimeString()}</span></p>
    <div class="bg-light rounded py-2 px-3 mb-2">
        <p class="text-small mb-0 text-muted">${text}</p>
    </div>
    <div id="rating">
        <i class="fa fa-star" style="color: grey;"></i>
        <i class="fa fa-star" style="color: grey;"></i>
        <i class="fa fa-star" style="color: grey;"></i>
        <i class="fa fa-star" style="color: grey;"></i>
        <i class="fa fa-star" style="color: grey;"></i>
        <button id="rate_btn" onclick=rateMessage()>Rate</button>
    </div>
    </div>
    `;
    chatBox.appendChild(wrapper);
    var stars = document.getElementById('rating').querySelectorAll('.fa');
    stars.forEach(star => {
        star.addEventListener('click', function() {
            stars.forEach(s => s.style.color = 'grey');
            this.style.color = 'gold';
        });
    });
}

function addTypingAnimation() {
    var wrapper = document.createElement('div');
    wrapper.className = 'media w-50 mb-3';
    wrapper.id = 'typing-indicator';
    wrapper.innerHTML = `
    <div class="media-body ml-3">
        <div class="bg-light rounded py-2 px-3 mb-2">
            <p class="text-small mb-0 text-muted">Tutor AI is typing...</p>
        </div>
    </div>
    `;
    chatBox.appendChild(wrapper);
}

function deleteTypingAnimation() {
    var typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

function getCurrentDateTimeString() {
    var now = new Date();
    return now.toLocaleString();
}

function delete_rating_stars() {
    var rateButton = document.getElementById('rate_btn');
    if (rateButton) {
        rateButton.remove();
    }
}

function rateMessage() {
    alert("Rating functionality is not implemented yet.");
}
// JavaScript für Dark-Mode und Einstellungen
var body = document.body;
var chatBox = document.getElementById('chat-box');
var settingsPanel = document.getElementById('settings-panel');
var settingsToggle = document.getElementById('settings-toggle');
var settingsToggle2 = document.getElementById('settings-toggle2');
var darkModeSwitch = document.getElementById('dark-mode-switch');





// Dark Mode Toggle
darkModeSwitch.addEventListener('change', function() {
    body.classList.toggle('dark-mode');
    chatBox.classList.toggle('dark-mode');
    settings.classList.toggle('dark-mode');
    var isDarkMode = body.classList.contains('dark-mode');
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
});




// Eventlistener für den ersten Settings Toggle Button
settingsToggle.addEventListener('click', function() {
    settingsPanel.classList.toggle('open'); // Toggle-Klasse für Öffnen/Schließen des Panels
    document.getElementById('settings-overlay').classList.toggle('active'); // Toggle für das Overlay
});

// Eventlistener für den zweiten Settings Toggle Button
settingsToggle2.addEventListener('click', function() {
    settingsPanel.classList.toggle('open'); // Toggle-Klasse für Öffnen/Schließen des Panels
    document.getElementById('settings-overlay').classList.toggle('active'); // Toggle für das Overlay
});

// Eventlistener für das Schließen des Panels bei Klick außerhalb
document.getElementById('settings-overlay').addEventListener('click', function() {
    settingsPanel.classList.remove('open');
    this.classList.remove('active');
});




// Überprüfen und Anwenden des Themes beim Laden
var savedTheme = localStorage.getItem('theme');
if (savedTheme === 'dark') {
    body.classList.add('dark-mode');
    chatBox.classList.add('dark-mode');
    settings.classList.add('dark-mode');
    darkModeSwitch.checked = true;
}

// Einstellungsfeld anzeigen/verstecken
settingsToggle.addEventListener('click', function() {
    settingsPanel.classList.toggle('open');
    document.getElementById('settings-overlay').classList.toggle('active');
});

// Schließen des Einstellungsfensters bei Klick außerhalb
document.getElementById('settings-overlay').addEventListener('click', function() {
    settingsPanel.classList.remove('open');
    this.classList.remove('active');
});
darkModeSwitch.addEventListener('change', function() {
    body.classList.toggle('dark-mode');
    chatBox.classList.toggle('dark-mode');
    settingsPanel.classList.toggle('dark-mode'); // Hinzugefügt
    var isDarkMode = body.classList.contains('dark-mode');
    localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
});

// Überprüfen und Anwenden des Themes beim Laden
var savedTheme = localStorage.getItem('theme');
if (savedTheme === 'dark') {
    body.classList.add('dark-mode');
    chatBox.classList.add('dark-mode');
    settingsPanel.classList.add('dark-mode'); // Hinzugefügt
    darkModeSwitch.checked = true;
}





