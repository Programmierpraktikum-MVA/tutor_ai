
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
    console.log("New Sending")
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
        console.log(JSON.stringify(response));
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
        <p class="text-small mb-1 text-muted"><span class="mr-1">👨‍🎓</span>John Doe <span class="small text-muted">${getCurrentDateTimeString()}</span></p>
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
    <p class="text-small mb-1 text-muted"><span class="mr-1">🤖</span></i>Chatbot <span class="small text-muted">${getCurrentDateTimeString()}</span></p>
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
    stars.forEach(function(star, index) {
        star.addEventListener('click', function() {
            stars.forEach(function(star, i) {
                star.style.color = i <= index ? 'gold' : 'gray';
            });
        });
    });
}

function delete_rating_stars() {
    try {
        var stars = document.getElementById("rating");
        if (stars) stars.remove();
    } catch {

    }
}

function rateMessage() {
    var stars = document.getElementById("rating");
    var rating = Array.from(stars).reduce(function(acc, star, index) {
        return star.style.color === 'gold' ? index + 1 : acc;
    }, 0);

    fetch("/rate", {
        method: 'POST',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ "message": "Some message" , "rating": rating})
    }).then(response => response.json()).then(response => {
        console.log(JSON.stringify(response));
        delete_rating_stars();
    });
}

function addTypingAnimation() {
    var wrapper = document.createElement('div');
    wrapper.className = 'media w-50 mb-3';
    wrapper.id = 'bubbles';
    wrapper.innerHTML = `
    <div class="media-body ml-3">
        <div class="bg-light rounded py-2 px-3 mb-2">
            <div class="msg-bubble">
                <div class="typing">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
            </div>
        </div>
    </div>
    `;
    chatBox.appendChild(wrapper);
  }

  function deleteTypingAnimation() {
    const bubble_element = document.getElementById("bubbles");
    bubble_element.remove();
  }

function getCurrentDateTimeString() {
    var options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric',
        hour12: false
    };
    return new Date().toLocaleString(undefined, options);
}