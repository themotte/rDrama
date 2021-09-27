function removeComment(post_id,button1,button2) {
    url="/ban_comment/"+post_id

    callback=function(){

        try {
            document.getElementById("comment-"+post_id+"-only").classList.add("banned");
        } catch(e) {
            document.getElementById("context").classList.add("banned");
        }

        button=document.getElementById("remove-"+post_id);
        button.onclick=function(){approveComment(post_id)};
        button.innerHTML='<i class="fas fa-clipboard-check"></i>Approve'
    }
    post(url, callback, "Comment has been removed.")

    if (typeof button1 !== 'undefined') {
        document.getElementById(button1).classList.toggle("d-md-inline-block");
        document.getElementById(button2).classList.toggle("d-md-inline-block");
    }
};

function approveComment(post_id,button1,button2) {
    url="/unban_comment/"+post_id

    callback=function(){
        try {
            document.getElementById("comment-"+post_id+"-only").classList.remove("banned");
        } catch(e) {
            document.getElementById("context").classList.remove("banned");
        }

        button=document.getElementById("remove-"+post_id);
        button.onclick=function(){removeComment(post_id)};
        button.innerHTML='<i class="fas fa-trash-alt"></i>Remove'
    }

    post(url, callback, "Comment has been approved.")

    if (typeof button1 !== 'undefined') {
        document.getElementById(button1).classList.toggle("d-md-inline-block");
        document.getElementById(button2).classList.toggle("d-md-inline-block");
    }
}


function removeComment2(post_id,button1,button2) {
    url="/ban_comment/"+post_id

    callback=function(){
        document.getElementById("comment-"+post_id+"-only").classList.add("banned");

        button=document.getElementById("remove-"+post_id);
        button.onclick=function(){approveComment(post_id)};
        button.innerHTML='<i class="fas fa-clipboard-check"></i>Approve'
    }
    post(url, callback, "Comment has been removed.")

    if (typeof button1 !== 'undefined') {
        document.getElementById(button1).classList.toggle("d-none");
        document.getElementById(button2).classList.toggle("d-none");
    }
};

function approveComment2(post_id,button1,button2) {
    url="/unban_comment/"+post_id

    callback=function(){
        document.getElementById("comment-"+post_id+"-only").classList.remove("banned");

        button=document.getElementById("remove-"+post_id);
        button.onclick=function(){removeComment(post_id)};
        button.innerHTML='<i class="fas fa-trash-alt"></i>Remove'
    }

    post(url, callback, "Comment has been approved.")

    if (typeof button1 !== 'undefined') {
        document.getElementById(button1).classList.toggle("d-none");
        document.getElementById(button2).classList.toggle("d-none");
    }
}