const Settings = {
	data() {
		return { breaks: [{ from: "10:00", to: "11:00" }] };
	},
	mounted() {
		this.socket.on("settings", (data) => {
			if (data != null) {
				//this.$data.breaks = data.breaks;
			}
		});
		this.socket.emit("enter_room", { room: "settings" });
	},
	inject: ["socket"],
	template: `
<ul>
	<!--<li v-for="(breakTimes, i) in breaks" :key="i">
		<label :for="'break-'+i+'-from'">Od:</label>
		<vue-timepicker v-model="breakTimes.from" format="HH:mm" manual-input :id="'break-'+i+'-from'" autocomplete="on" auto-scroll></vue-timepicker>
		<label :for="'break-'+i+'-to'">Do:</label>
		<vue-timepicker v-model="breakTimes.to" format="HH:mm" manual-input :id="'break-'+i+'-to'" autocomplete="on" auto-scroll></vue-timepicker>
	</li>-->
	<vue-timepicker></vue-timepicker>
</ul>
`,
};

export default Settings;
