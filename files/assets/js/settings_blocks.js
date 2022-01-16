function block_user() {

    var usernameField = document.getElementById("exile-username");

    var isValidUsername = usernameField.checkValidity();

    username = usernameField.value;

    if (isValidUsername) {

        const xhr = new XMLHttpRequest();
        xhr.setRequestHeader('Authorization', 'xhr');
        xhr.open("post", "/settings/block");
        xhr.withCredentials=true;
        f=new FormData();
        f.append("username", username);
        f.append("formkey", formkey());
        xhr.onload=function(){
            if (xhr.status<300) {
                location.reload(true);
            }
            else {
                var myToast = new bootstrap.Toast(document.getElementById('toast-post-success'));
                myToast.hide();
                var myToast = new bootstrap.Toast(document.getElementById('toast-post-error'));
                myToast.show();
                document.getElementById("toast-error-message").textContent = "Error. Please try again later.";
            }
        }
        xhr.send(f)
    }
}