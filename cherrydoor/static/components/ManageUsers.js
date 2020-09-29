const ManageUsers = {
	data() {
		return {
			users: [
				{
					username: "test",
					permissions: ["enter"],
					cards: ["test"],
					edit: { parmissions: false, cards: [false], username: false },
				},
			],
			available_permissions: this.user.permissions,
			new_user: { username: "", permissions: [] },
		};
	},
	inject: ["user", "socket"],
	mounted() {
		this.socket.on("door", (data) => {
			if (data != null) {
				this.$data.doorOpen = data.open;
			}
		});
	},
	methods: {
		addUser() {
			return true;
		},
		submitUser() {
			return true;
		},
		getCard(userIndex, cardIndex) {},
	},
	template: `
<ul class="manage-users">
	<li class="user" v-for="(usr, i) in users" :key="usr.username">
			<div class="input-editable">
				<input class="username existing-user" v-model="usr.username" :disabled="!usr.edit.username">
				<button @click="usr.edit.username = true" class="edit-button edit-username btn waves-effect waves-light right">Edit</button>
			</div>
			<div class="user-permissions existing-user">
				<div class="page__checkbox input-field" v-for="permission in Object.keys(available_permissions)" >
					<label class="checkbox">
						<input
							type="checkbox"
							:name="permission"
							:id="permission+i"
							:aria-label="permission"
							class="checkbox-input"
							v-model="usr.permissions"
							:value="permission"
							:disabled="!available_permissions[permission] || !usr.edit.permissions"
							:checked="available_permissions[permission]"
						/>
						<span class="checkbox-label">
							<span class="checkbox-text">{{permission}}</span>
						</span>
					</label>
				</div>
			</div>
			<button class="edit-button edit-permissions btn waves-effect waves-light right" @click="usr.edit.permissions = true">Edit permissions</button>
			<ul class="user-cards existing-user">
				<li v-for="(card, index) in usr.cards">
					<div class="input-editable">
						<input class="card-uid existing-user" v-model="usr.cards[index]" :disabled="!usr.edit.cards[index]">
						<button class="edit-button edit-card btn waves-effect waves-light right" @click="usr.edit.cards[index]=true">Edit</button><button class="edit-button reader-input btn waves-effect waves-light" @click="getCard(i, index)">Get from reader</button>
					</div>
				</li>
			</ul>
	</li>
	<li class="user new-user">
			<h3>Nowy użytkownik</h3>
			<input class="username new-user" v-model="new_user.username">
			<div class="user-permissions new-user">
					<div class="page__checkbox input-field" v-for="permission in Object.keys(available_permissions)" >
						<label class="checkbox">
							<input
								type="checkbox"
								:name="permission"
								:aria-label="permission"
								class="checkbox-input"
								v-model="new_user.permissions"
								:value="permission"
								:disabled="!available_permissions[permission]"
							/>
							<span class="checkbox-label">
								<span class="checkbox-text">{{permission}}</span>
							</span>
						</label>
					</div>
			</div>
			<ul class="user-cards new-user">
				<li v-for="card in new_user.cards"><input class="card-uid new-user" v-model="card" disabled></li>
			</ul>
			<button class="new-user plus-button" @click="addUser()">Add user</button>
		</li>
</ul>
`,
};

export default ManageUsers;
