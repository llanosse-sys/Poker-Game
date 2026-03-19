// -------------------------------------------------------
// STATE
// Tracks everything about the current game session.
// -------------------------------------------------------
let socket = null;
let myName = null;
let playerOrder = [];
let myIndex = -1;


// -------------------------------------------------------
// UTILITY: Get card color class (red for hearts/diamonds)
// -------------------------------------------------------
function cardColor(cardStr) {
    return (cardStr.includes("♥") || cardStr.includes("♦")) ? "red" : "black";
}


// -------------------------------------------------------
// UTILITY: Add a message to the game log
// -------------------------------------------------------
function log(message, highlight = false) {
    const entries = document.getElementById("log-entries");
    if (!entries) return;
    const entry = document.createElement("div");
    entry.className = "log-entry" + (highlight ? " highlight" : "");
    entry.textContent = message;
    entries.prepend(entry);
}


// -------------------------------------------------------
// RENDER: Update a community card slot
// -------------------------------------------------------
function renderCommunityCard(index, cardStr) {
    const slot = document.getElementById(`cc-${index}`);
    if (!slot) return;
    slot.textContent = cardStr;
    slot.classList.add("filled", cardColor(cardStr));
}


// -------------------------------------------------------
// RENDER: Update a player's seat on the table
// -------------------------------------------------------
function renderSeat(seatIndex, name, chips, status = "", folded = false) {
    document.getElementById(`name-${seatIndex}`).textContent = name;
    document.getElementById(`chips-${seatIndex}`).textContent = `$${chips}`;
    document.getElementById(`status-${seatIndex}`).textContent = status;

    const seat = document.getElementById(`seat-${seatIndex}`);
    seat.classList.toggle("folded", folded);

    // Show card backs for other players (they have cards but we can't see them)
    const cardsDiv = document.getElementById(`cards-${seatIndex}`);
    cardsDiv.innerHTML = `
        <div class="mini-card back"></div>
        <div class="mini-card back"></div>
    `;
}


// -------------------------------------------------------
// RENDER: Show/hide action buttons based on available actions
// -------------------------------------------------------
function showActionPanel(actions, toCall) {
    const panel = document.getElementById("action-panel");
    panel.classList.add("visible");

    document.getElementById("btn-fold").style.display  = actions.includes("fold")  ? "block" : "none";
    document.getElementById("btn-call").style.display  = actions.includes("call")  ? "block" : "none";
    document.getElementById("btn-check").style.display = actions.includes("check") ? "block" : "none";
    document.getElementById("btn-raise").style.display = actions.includes("raise") ? "block" : "none";
    document.getElementById("raise-input").style.display = actions.includes("raise") ? "block" : "none";

    document.getElementById("call-amount").textContent = toCall > 0 ? `$${toCall}` : "";

    if (myIndex >= 0) {
        document.getElementById(`seat-${myIndex}`).classList.add("active");
    }
}


// -------------------------------------------------------
// RENDER: Hide action buttons after player acts
// -------------------------------------------------------
function hideActionPanel() {
    document.getElementById("action-panel").classList.remove("visible");
    document.querySelectorAll(".seat").forEach(s => s.classList.remove("active"));
}


// -------------------------------------------------------
// SEND ACTION: Called when player clicks a button
// -------------------------------------------------------
function sendAction(action, raiseAmount = 0) {
    if (!socket) return;
    socket.send(JSON.stringify({ action, raise_amount: raiseAmount }));
    hideActionPanel();
    log(`You: ${action}${raiseAmount ? ` $${raiseAmount}` : ""}`);
}


// -------------------------------------------------------
// HANDLE SERVER MESSAGES
// -------------------------------------------------------
function handleServerMessage(data) {
    switch (data.event) {

        // -------------------------------------------------------
        // room_created: Server confirmed the room was created.
        // Show the room code in the ready overlay so the creator
        // can share it with friends. No redirect needed anymore.
        // -------------------------------------------------------
        case "room_created":
            document.getElementById("room-code-display").textContent = data.code;
            document.getElementById("code-section").style.display = "flex";
            document.getElementById("copy-code-btn").addEventListener("click", function () {
                navigator.clipboard.writeText(data.code).then(() => {
                    this.textContent = "Copied!";
                    setTimeout(() => { this.textContent = "Copy"; }, 2000);
                });
            });
            break;

        case "error":
            alert(data.message);
            window.location.href = "/";
            break;

        case "player_joined":
            playerOrder = data.all_players;
            myIndex = playerOrder.indexOf(myName);
            log(`${data.player} joined the table.`);
            document.getElementById("ready-status").textContent =
                `${data.all_players.length} / 4 players connected — 0 ready`;

            playerOrder.forEach((name, i) => {
                renderSeat(i, name, 1000);
            });
            break;

        case "player_ready":
            document.getElementById("ready-status").textContent =
                `${data.total_players} / 4 players connected — ${data.ready_count} ready`;
            const readyEntry = document.createElement("div");
            readyEntry.textContent = `✓ ${data.player}`;
            readyEntry.style.color = "#7ec87e";
            document.getElementById("ready-list").appendChild(readyEntry);
            break;

        case "game_starting":
            playerOrder = data.players;
            myIndex = playerOrder.indexOf(myName);
            log("Game is starting!", true);
            document.getElementById("ready-overlay").classList.add("hidden");

            playerOrder.forEach((name, i) => {
                renderSeat(i, name, 1000);
            });
            break;

        case "hole_cards": {
            const [c1, c2] = data.cards;
            const hc0 = document.getElementById("hole-card-0");
            const hc1 = document.getElementById("hole-card-1");
            hc0.textContent = c1;
            hc0.className = `hole-card ${cardColor(c1)}`;
            hc1.textContent = c2;
            hc1.className = `hole-card ${cardColor(c2)}`;
            log(`Your hole cards: ${c1} ${c2}`, true);
            break;
        }

        case "community_cards": {
            const stage = data.stage;
            document.getElementById("stage-label").textContent = stage;
            log(`[${stage.toUpperCase()}] ${data.cards.join("  ")}`, true);

            if (stage === "flop") {
                renderCommunityCard(0, data.cards[0]);
                renderCommunityCard(1, data.cards[1]);
                renderCommunityCard(2, data.cards[2]);
            } else if (stage === "turn") {
                renderCommunityCard(3, data.cards[3]);
            } else if (stage === "river") {
                renderCommunityCard(4, data.cards[4]);
            }
            break;
        }

        case "your_turn":
            log("It's your turn!", true);
            showActionPanel(data.actions, data.to_call);
            document.getElementById("pot-amount").textContent = `$${data.pot}`;
            break;

        case "player_action": {
            document.getElementById("pot-amount").textContent = `$${data.pot}`;

            const seatIdx = playerOrder.indexOf(data.player);
            if (seatIdx >= 0) {
                document.getElementById(`status-${seatIdx}`).textContent = data.action;
                document.getElementById(`chips-${seatIdx}`).textContent = `$${data.chips}`;

                if (data.action === "fold") {
                    document.getElementById(`seat-${seatIdx}`).classList.add("folded");
                }

                document.getElementById(`seat-${seatIdx}`).classList.remove("active");
            }

            log(`${data.player}: ${data.action}${data.raise_amount ? ` $${data.raise_amount}` : ""} | Pot: $${data.pot}`);
            break;
        }

        case "showdown":
            log(`Winner: ${data.winners.join(", ")} with ${data.hand_name} (+$${data.split_amount})`, true);
            break;

        case "reveal_cards":
            Object.entries(data.hands).forEach(([name, cards]) => {
                const seatIdx = playerOrder.indexOf(name);
                if (seatIdx < 0) return;
                const cardsDiv = document.getElementById(`cards-${seatIdx}`);
                cardsDiv.innerHTML = cards.map(card => {
                    const color = cardColor(card);
                    return `<div class="mini-card ${color}">${card}</div>`;
                }).join("");
            });
            log(`Showdown — cards revealed!`, true);
            break;

        case "chips_update":
            playerOrder.forEach((name, i) => {
                document.getElementById(`chips-${i}`).textContent = `$${data.chips[name]}`;
            });
            break;

        case "round_over":
            document.getElementById("new-round-panel").classList.add("visible");
            document.getElementById("new-round-status").textContent = `0 / ${data.total_players} ready`;
            document.getElementById("btn-new-round").disabled = false;
            document.getElementById("btn-new-round").textContent = "New Round";
            break;

        case "new_round_player_ready":
            document.getElementById("new-round-status").textContent = `${data.ready_count} / ${data.total_players} ready`;
            log(`${data.player} is ready for the next round.`);
            break;

        case "new_round_starting":
            document.getElementById("new-round-panel").classList.remove("visible");
            for (let i = 0; i < 5; i++) {
                const slot = document.getElementById(`cc-${i}`);
                slot.textContent = "";
                slot.className = "card-slot";
            }
            document.getElementById("stage-label").textContent = "";
            document.getElementById("pot-amount").textContent = "$0";
            document.getElementById("hole-card-0").textContent = "?";
            document.getElementById("hole-card-1").textContent = "?";
            playerOrder.forEach((_, i) => {
                if (i !== myIndex) {
                    const cardsDiv = document.getElementById(`cards-${i}`);
                    cardsDiv.innerHTML = `
                        <div class="mini-card back"></div>
                        <div class="mini-card back"></div>
                    `;
                }
            });

            log("New round starting!", true);
            break;

        case "positions_update":
            playerOrder.forEach((name, i) => {
                const el = document.getElementById(`position-${i}`);
                if (el) el.textContent = data.positions[name] || "";
            });
            break;

        case "player_left":
            log(`${data.player} left the game.`);
            break;

        case "game_over":
            log(`Game over: ${data.reason}`, true);
            alert(`Game ended: ${data.reason}`);
            window.location.href = "/";
            break;

        default:
            console.log("Unknown event:", data);
    }
}


// -------------------------------------------------------
// LOBBY BUTTON LISTENERS (only exist on index.html)
// Pass name, action, and code directly in the URL so
// it works on all devices including iPhone Safari.
// -------------------------------------------------------
const createBtn = document.getElementById("create-btn");
const joinBtn   = document.getElementById("join-btn");

if (createBtn) {
    createBtn.addEventListener("click", function () {
        const name = document.getElementById("create-name").value.trim();
        if (!name) { alert("Enter your name first."); return; }

        const chips = parseInt(document.getElementById("starting-chips").value) || 1000;
        const sb    = parseInt(document.getElementById("small-blind").value)    || 5;
        const bb    = parseInt(document.getElementById("big-blind").value)      || 10;

        if (bb <= sb) { alert("Big blind must be greater than small blind."); return; }

        window.location.href = `game.html?name=${encodeURIComponent(name)}&action=create&chips=${chips}&sb=${sb}&bb=${bb}`;
    });
}

if (joinBtn) {
    joinBtn.addEventListener("click", function () {
        const name = document.getElementById("join-name").value.trim();
        const code = document.getElementById("join-code").value.trim();
        if (!name) { alert("Enter your name first."); return; }
        if (!code || code.length !== 4) { alert("Enter the 4-digit room code."); return; }
        window.location.href = `game.html?name=${encodeURIComponent(name)}&action=join&code=${code}`;
    });
}


// -------------------------------------------------------
// GAME TABLE BUTTON LISTENERS (only exist on game.html)
// -------------------------------------------------------
const btnFold  = document.getElementById("btn-fold");
const btnCall  = document.getElementById("btn-call");
const btnCheck = document.getElementById("btn-check");
const btnRaise = document.getElementById("btn-raise");

const btnNewRound = document.getElementById("btn-new-round");
if (btnNewRound) {
    btnNewRound.addEventListener("click", () => {
        if (!socket) return;
        socket.send(JSON.stringify({ action: "new_round_ready" }));
        btnNewRound.disabled = true;
        btnNewRound.textContent = "Waiting...";
    });
}

const btnReady = document.getElementById("btn-ready");
if (btnReady) {
    btnReady.addEventListener("click", () => {
        if (!socket) return;
        socket.send(JSON.stringify({ action: "ready" }));
        btnReady.disabled = true;
        btnReady.textContent = "Waiting...";
    });
}

if (btnFold)  btnFold.addEventListener("click", () => sendAction("fold"));
if (btnCall)  btnCall.addEventListener("click", () => sendAction("call"));
if (btnCheck) btnCheck.addEventListener("click", () => sendAction("check"));
if (btnRaise) {
    btnRaise.addEventListener("click", () => {
        const amount = parseInt(document.getElementById("raise-input").value);
        if (!amount || amount <= 0) {
            alert("Enter a valid raise amount.");
            return;
        }
        sendAction("raise", amount);
        document.getElementById("raise-input").value = "";
    });
}


// -------------------------------------------------------
// GAME PAGE INIT (only runs on game.html)
// Reads name/action/code from URL params — works on all
// devices including iPhone Safari which can block localStorage.
// -------------------------------------------------------
if (document.getElementById("btn-fold")) {
    const params = new URLSearchParams(window.location.search);
    myName = params.get("name");
    const myAction = params.get("action") || "join";
    const myCode   = params.get("code") || "";

    if (!myName) {
        window.location.href = "/";
    } else {
        const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        const wsHost     = window.location.hostname || "localhost";
        const wsPort     = window.location.protocol === "https:" ? "" : ":8765";
        socket = new WebSocket(`${wsProtocol}//${wsHost}${wsPort}`);

        socket.onopen = function () {
            const msg = { name: myName, action: myAction };
            if (myAction === "join") msg.code = myCode;
            if (myAction === "create") {
                msg.chips = parseInt(params.get("chips")) || 1000;
                msg.sb    = parseInt(params.get("sb"))    || 5;
                msg.bb    = parseInt(params.get("bb"))    || 10;
            }
            socket.send(JSON.stringify(msg));
        };

        socket.onmessage = function (event) {
            const data = JSON.parse(event.data);
            handleServerMessage(data);
        };

        socket.onclose = function () {
            log("Disconnected from server.");
        };
    }
}
