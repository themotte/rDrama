function sort_table(n) {
	var table, rows, switching, i, x, y, shouldSwitch, switchcount = 0;
	table = document.getElementById("sortable_table");
	switching = true;
	while (switching) {
		switching = false;
		rows = table.rows;
		for (i = 1; i < (rows.length - 1); i++) {
			shouldSwitch = false;
			x = rows[i].getElementsByTagName("TD")[n];
			y = rows[i + 1].getElementsByTagName("TD")[n];
			const x_child = x.getElementsByTagName('a')
			if (x_child) {
				x = x_child[0]
			}
			const y_child = y.getElementsByTagName('a')
			if (y_child) {
				y = y_child[0]
			}
			if (parseInt(x.innerHTML) < parseInt(y.innerHTML)) {
				shouldSwitch = true;
				break;
			}
		}
		if (shouldSwitch) {
			rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
			switching = true;
			switchcount ++;
		}
	}
}