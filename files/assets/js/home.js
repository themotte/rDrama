if (!("standalone" in window.navigator) && window.navigator.standalone) {
    if (window.innerWidth <= 737) {
        document.getElementById('mobile-prompt').show()
        document.getElementsByClassName('tooltip')[0].onclick = function(event){
            document.getElementById('mobile-prompt').hide()
            var xhr = new XMLHttpRequest();
            xhr.withCredentials=true;
            xhr.open("POST", '/dismiss_mobile_tip', true);
            xhr.send();
        }
    }
}