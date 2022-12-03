// a tiny script to yell at the user if they try to leave the Volunteer page any way besides the Submit button

var submitting = false;

var onFormSubmit = function() { submitting = true; };

window.onload = function() {
    window.addEventListener("beforeunload", function (e) {
        if (submitting) {
            return undefined;
        }

        (e || window.event).returnValue = true;
        return true;
    })
}
