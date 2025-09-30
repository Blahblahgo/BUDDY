const chatbox = document.getElementById("chatbox");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const voiceBtn = document.getElementById("voice-btn");

let voices = [];
function loadVoices() {
  voices = window.speechSynthesis.getVoices();
}
window.speechSynthesis.onvoiceschanged = loadVoices;
loadVoices();

function appendMessage(msg, type) {
  const msgDiv = document.createElement("div");
  msgDiv.className = type === "user" ? "user-msg" : "bot-msg";

  const prefix = type === "user" ? "🧑 You: " : "🤖 Buddy: ";
  msgDiv.textContent = prefix + msg;
  chatbox.appendChild(msgDiv);
  chatbox.scrollTop = chatbox.scrollHeight;

  if (type === "bot") speakMessage(msg);
}

function speakMessage(message) {
  if (!message) return;

  message = message.replace(/https?:\/\/\S+/g, '');
  message = message.replace(
    /([\u2700-\u27BF]|[\uE000-\uF8FF]|[\uD800-\uDBFF][\uDC00-\uDFFF]|[\u2011-\u26FF]|[\u2B05-\u2B07]|[\u2934-\u2935]|[\u2190-\u21FF])/g,
    ''
  ).trim();
  if (!message) return;

  const utter = new SpeechSynthesisUtterance(message);
  const femaleNames = ["zira", "samantha", "tessa"];
  const selectedVoice = voices.find(v =>
    femaleNames.some(n => v.name.toLowerCase().includes(n))
  ) || voices[0] || null;

  if (selectedVoice) utter.voice = selectedVoice;
  utter.lang = selectedVoice?.lang || "en-IN";
  utter.pitch = 1.3;
  utter.rate = 1.05;
  utter.volume = 1;

  // Slight pauses for natural speech
  utter.text = message.replace(/([,.!?])/g, '$1 ...');

  window.speechSynthesis.speak(utter);
}

function showWidget(id, message, duration = 7000) {
  const widget = document.getElementById(id);
  if (!widget) return;
  widget.textContent = message;
  widget.classList.add("show");
  if (duration > 0) setTimeout(() => widget.classList.remove("show"), duration);
}

function hideWidget(id) {
  const widget = document.getElementById(id);
  if (!widget) return;
  widget.classList.remove("show");
}

function sendMessage(message) {
  appendMessage(message, "user");

  fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  })
    .then(res => res.json())
    .then(data => {
      let botReply = data.reply || "";

      // Only add casual greeting if backend reply is empty or generic fallback
      const lowerMsg = message.toLowerCase();
      if ((!botReply || botReply === "" || botReply.includes("Ready! Cheppu em kavali?")) &&
          ["hi", "hey", "hello", "wassup", "what's up"].some(g => lowerMsg.includes(g))) {
        const greetings = [
          "Heeey! 😄 How's your day going?",
          "Yo buddy! 🌟 What's poppin'?",
          "Hey hey! 😎 Feeling good today?",
        ];
        botReply = greetings[Math.floor(Math.random() * greetings.length)];
      }

      appendMessage(botReply, "bot");

      if (data.redirect) {
        setTimeout(() => {
          window.open(data.redirect, "_blank");
        }, 2000);
      }

      const replyLower = botReply.toLowerCase();
      if (replyLower.includes("temperature") || replyLower.includes("weather")) {
        showWidget("weather-widget", botReply);
      } else if (replyLower.includes("time")) {
        showWidget("time-widget", botReply);
      } else if (replyLower.includes("reminder")) {
        showWidget("reminder-widget", botReply);
      } else {
        hideWidget("weather-widget");
        hideWidget("time-widget");
        hideWidget("reminder-widget");
      }
    })
    .catch(() => {
      appendMessage("Server unreachable buddy! 😢", "bot");
    });
}

// UI events
sendBtn.onclick = () => {
  const msg = input.value.trim();
  if (!msg) return;
  sendMessage(msg);
  input.value = "";
};

input.addEventListener("keypress", (e) => {
  if (e.key === "Enter") sendBtn.click();
});

// Voice input
voiceBtn.onclick = () => {
  const recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
  recognition.lang = "en-IN";
  recognition.start();

  recognition.onresult = (event) => {
    const spokenText = event.results[0][0].transcript;
    input.value = spokenText;
    sendBtn.click();
  };

  recognition.onerror = (event) => {
    appendMessage("Mic error buddy: " + event.error, "bot");
  };
};