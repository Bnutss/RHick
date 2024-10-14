// Автоматическое плавное скрытие сообщений через 5 секунд
setTimeout(function () {
    const messages = document.querySelectorAll('.message-container li');
    messages.forEach(function (message) {
        message.style.opacity = '0';
    });
}, 3000);
setTimeout(function () {
    const messages = document.querySelector('.message-container');
    if (messages) {
        messages.innerHTML = '';
    }
}, 3500);