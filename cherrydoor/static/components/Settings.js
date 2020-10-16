const Settings = {
	data() {
		return { breaks: "" };
	},
	mounted() {
		this.socket.on("settings", (data) => {
			if (data != null) {
				this.$data.breaks = JSON.stringify(data.breaks, null, 2);
			}
		});
		this.socket.emit("enter_room", { room: "settings" });
	},
	methods: {
		save() {
			try {
				this.socket.emit("settings", {
					breaks: JSON.parse(this.$data.breaks),
				});
			} catch (e) {}
		},
		reset() {
			try {
				this.socket.emit("reset");
			} catch (e) {}
		},
	},
	inject: ["socket"],
	template: `
<div class="card row-4 col-4">
	<label for="breaks">Przerwy <small>json, lista obiektów z właściwościami "from" i "to", format "HH:MM"</small></label>
	<textarea class="break-input" v-model="breaks" placeholder="[]"></textarea>
	<button @click="save()" class="save-button">Zapisz</button>
</div>
<div class="card">
	<button @click="reset()" class="reset-button">Zresetuj Arduino</button>
</div>
`,
};

export default Settings;
