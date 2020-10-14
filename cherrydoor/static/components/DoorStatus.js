const DoorStatus = {
	data() {
		return {
			doorOpen: false,
			isBreak: false,
		};
	},
	inject: ["user", "socket"],
	mounted() {
		this.socket.emit("enter_room", { room: "door" });
		this.socket.on("door", (data) => {
			if (data != null) {
				this.$data.doorOpen = !!data.open;
				this.$data.doorOpen = !!data.break;
			}
		});
	},
	methods: {
		toggleDoor() {
			if (
				this.user != null &&
				this.user.permissions != null &&
				this.user.permissions.enter
			) {
				this.socket.emit("door", { open: !this.$data.doorOpen });
			}
		},
	},
	template: `
<div class="door-status">
		<h1>Status drzwi</h1>
		<p :class="{ trueIndicator: doorOpen }" class="door-status-text indicator">{{ doorOpen ? "Otwarte" : "Zamknięte" }}</p>
		<p :class="{ trueIndicator: isBreak }" class="door-status-text indicator">{{ isBreak ? "Przerwa" : "Lekcja/Po Szkole" }}</p>
		<button @click="toggleDoor()" :class="{ open: doorOpen }" class="door-button">{{ doorOpen ? "Zamknij" : "Otwórz" }}</button>
</div>
`,
};

export default DoorStatus;
