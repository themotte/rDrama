function removeFollowing(event, username) {
	postToastSimple(event.target,'/unfollow/' + username); 
	let table = document.getElementById("followers-table");
	table.removeChild(event.target.parentElement.parentElement);
}
