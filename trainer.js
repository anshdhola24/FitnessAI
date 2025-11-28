// static/js/trainer.js

(function () {
  function escapeHtml(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatMessage(text) {
    return escapeHtml(text).replace(/\n/g, "<br>");
  }

  function appendMessage(role, text) {
    const chat = document.getElementById("trainerChat");
    if (!chat) return;

    const msg = document.createElement("div");
    msg.className = "trainer-msg " + (role === "user" ? "trainer-msg-user" : "trainer-msg-bot");

    const avatar = document.createElement("div");
    avatar.className = "trainer-avatar";
    avatar.textContent = role === "user" ? "You" : "🤖";

    const bubble = document.createElement("div");
    bubble.className = "trainer-bubble";
    bubble.innerHTML = formatMessage(text);

    msg.appendChild(avatar);
    msg.appendChild(bubble);
    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
  }

  function setLoading(isLoading) {
    const input = document.getElementById("trainerInput");
    const btn = document.getElementById("trainerSendBtn");
    if (!input || !btn) return;
    input.disabled = isLoading;
    btn.disabled = isLoading;
    btn.textContent = isLoading ? "Sending…" : "Send";
  }

  async function sendMessage(message) {
    const trimmed = (message || "").trim();
    if (!trimmed) return;

    appendMessage("user", trimmed);
    setLoading(true);

    try {
      const res = await fetch("/trainer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed })
      });

      if (!res.ok) {
        throw new Error("Server error " + res.status);
      }

      const data = await res.json();
      appendMessage("bot", data.reply || "Sorry, I couldn't understand that.");
    } catch (err) {
      console.error(err);
      appendMessage(
        "bot",
        "😔 I couldn't reach the server. Please check your internet and try again."
      );
    } finally {
      setLoading(false);
    }
  }

  // ---- Voice input (simple + safe) ----
  let recognition = null;
  let listening = false;

  function setupVoice() {
    const Mic = window.SpeechRecognition || window.webkitSpeechRecognition;
    const micBtn = document.getElementById("trainerMicBtn");
    const input = document.getElementById("trainerInput");

    if (!micBtn || !input) return;

    if (!Mic) {
      micBtn.classList.add("trainer-mic-disabled");
      micBtn.title = "Voice input not supported in this browser.";
      return;
    }

    recognition = new Mic();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = function () {
      listening = true;
      micBtn.classList.add("is-listening");
      micBtn.title = "Listening… click again to cancel";
    };

    recognition.onend = function () {
      listening = false;
      micBtn.classList.remove("is-listening");
      micBtn.title = "Voice input";
    };

    recognition.onerror = function (event) {
      console.error("Speech error", event);
      listening = false;
      micBtn.classList.remove("is-listening");
      micBtn.title = "Voice error – try again.";
    };

    recognition.onresult = function (event) {
      const transcript = event.results[0][0].transcript;
      if (transcript) {
        input.value = transcript;
        input.focus();
      }
    };

    micBtn.addEventListener("click", function () {
      if (!recognition) return;
      if (listening) {
        recognition.stop();
      } else {
        try {
          recognition.start();
        } catch (err) {
          console.error(err);
        }
      }
    });
  }

  // ---- Init when on trainer page ----
  document.addEventListener("DOMContentLoaded", function () {
    const chat = document.getElementById("trainerChat");
    const form = document.getElementById("trainerForm");
    const input = document.getElementById("trainerInput");
    const chips = document.querySelectorAll(".trainer-chip");

    if (chat && form && input) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        const text = input.value;
        input.value = "";
        sendMessage(text);
      });

      input.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && !e.shiftKey) {
          e.preventDefault();
          form.dispatchEvent(new Event("submit"));
        }
      });

      chips.forEach(function (chip) {
        chip.addEventListener("click", function () {
          const msg = chip.getAttribute("data-message") || chip.textContent;
          sendMessage(msg);
        });
      });

      setupVoice();
    }
  });
})();
