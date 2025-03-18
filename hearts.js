// hearts.js
function createHeart() {
    const heart = document.createElement("div");
    heart.className = "heart";
    heart.innerHTML = "&#10084;";
    heart.style.left = Math.random() * 100 + "vw";
    heart.style.animationDuration = (3 + Math.random() * 3) + "s";
    heart.style.fontSize = (20 + Math.random() * 30) + "px";
    document.body.appendChild(heart);
    heart.addEventListener('animationend', () => {
        heart.remove();
    });
}
setInterval(createHeart, 500);