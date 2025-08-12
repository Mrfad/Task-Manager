//1) Script to get the time running at realtime
setInterval(function() {
    var date = new Date();
    $('#clock').html(
        (date.getHours() < 10 ? '0': '') + date.getHours() + ":" +
        (date.getMinutes() < 10 ? '0': '') + date.getMinutes() + ":" +
        (date.getSeconds() < 10 ? '0': '') + date.getSeconds()
    );
}, 500);